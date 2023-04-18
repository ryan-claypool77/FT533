from datetime import datetime, timedelta, date
import math
import pandas as pd
import numpy as np
from pandas.tseries.offsets import BDay

# blotter_cols = ['trade_id', 'date', 'asset', 'trip', 'action', 'type', 'price', 'status']
# ledger_cols = ['trade_id', 'asset', 'dt_enter', 'dt_exit', 'success', 'n', 'rtn']

blotter = pd.read_csv('blotter.csv').sort_values(['trade_id', 'date'], ascending=[1, 1])


def create_ledger(blotter):
    # 1. Create a ledger to hold the static elements (trade_id, asset); set trade_id as index
    ledger = pd.DataFrame({
        'trade_id': blotter['trade_id'],
        'asset': blotter['asset'],
    }).drop_duplicates().set_index('trade_id')

    # 2. Find minimum date for each trade_id in blotter and add 'dt_enter' column
    date_entry = blotter.loc[(blotter['trip'] == 'ENTER') & (blotter['status'] == 'SUBMITTED')]
    date_entry = date_entry.set_index('trade_id')
    ledger['dt_enter'] = date_entry['date']
    ledger = ledger.dropna()  # BUG!!!!!!!; 811 trade_ids exist; 810 entry orders were submitted; #811 only has a live, no submit

    # TESTING - PENDING REVIEW OF BUG (line 26); ALL ELSE PASSED
    # print(date_entry)  # pass
    # print(ledger)  # see ledger.dropna() 3 lines above

    # 3. Find out if blotter contains an exit order for the trade id that was also filled; if so, assign date
    date_exit = blotter.loc[(blotter['trip'] == 'EXIT') & (blotter['status'] == 'FILLED')]
    date_exit = date_exit.set_index('trade_id')
    ledger['dt_exit'] = date_exit['date']

    # 4. Success Logic -
    # i. if blotter contains a 'FILLED', 'EXIT' order, 1
    passing = blotter.loc[(blotter['trip'] == 'EXIT') & (blotter['status'] == 'FILLED') & (blotter['type'] == 'LMT')]
    passing = passing.set_index('trade_id')
    passing['success'] = int(1)

    # ii. if blotter contains  a 'CANCELLED' 'ENTRY' order, 0
    failing = blotter.loc[(blotter['trip'] == 'EXIT') & (blotter['status'] == 'CANCELLED')]
    failing = failing.set_index('trade_id')
    failing['success'] = int(-1)

    # iii. if blotter contains  a 'CANCELLED' 'EXIT' order, -1
    no_entry = blotter.loc[(blotter['trip'] == 'ENTER') & (blotter['status'] == 'CANCELLED')]
    no_entry = no_entry.set_index('trade_id')
    no_entry['success'] = int(0)

    success_rate = pd.concat([
        passing,
        failing,
        no_entry
    ]).sort_values(['trade_id', 'date'])

    ledger['success'] = success_rate['success']

    # 5. 'n' column is the difference between the (dt_exit - dt_enter + 1 Day)
    # clean up ledger dates to datetime
    ledger['dt_enter'] = pd.to_datetime(ledger['dt_enter'])
    ledger['dt_exit'] = pd.to_datetime(ledger['dt_exit'])

    # print(ledger['dt_enter'].dtypes)
    # print(ledger['dt_exit'].dtypes)

    # ledger['n'] = (ledger['dt_exit'] - ledger['dt_enter']) / np.timedelta64(1, 'D') + 1  # REMOVE NON-BUSINESS DAYS
    ledger['n'] = [None if pd.isna(row['dt_enter']) or pd.isna(row['dt_exit'])
               else len(pd.date_range(start=row['dt_enter'], end=row['dt_exit'], freq=BDay()))
               for _, row in ledger.iterrows()]
    # for line in ledger.iterrows():
    #     line['n'] = np.busday_count(line['dt_enter'], line['dt_exit'])
        # print(res)

    # 6. 'rtn' column is lambda(filled_exit_price/filled_entry_price) / 'n'

    # create a df for filled entry orders
    filled_enter_table = blotter.loc[(blotter['trip'] == 'ENTER') & (blotter['status'] == 'FILLED')]
    filled_enter_table = filled_enter_table.set_index('trade_id')
    filled_enter_table['price'] = pd.to_numeric(filled_enter_table['price'], downcast="float")
    ledger['price_enter'] = filled_enter_table['price']

    # create a df for filled exit orders
    filled_exit_table = blotter.loc[(blotter['trip'] == 'EXIT') & (blotter['status'] == 'FILLED')]
    filled_exit_table = filled_exit_table.set_index('trade_id')
    filled_exit_table['price'] = pd.to_numeric(filled_exit_table['price'], downcast="float")
    ledger['price_exit'] = filled_exit_table['price']

    # add returns by index
    for index in ledger.iterrows():
        ledger['rtn'] = np.log(ledger['price_exit'] / ledger['price_enter']) / ledger['n']


    # print(ledger)
    ledger.drop(['price_enter', 'price_exit'], axis=1, inplace=True)
    return ledger

# FOR TESTING
ledger = create_ledger(blotter)
print(ledger)
