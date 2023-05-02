import eikon
from dash import Dash, html, dcc, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
from datetime import datetime, date, timedelta as dt
import plotly.express as px
import pandas as pd
# from datetime import datetime
import numpy as np
import os
import refinitiv.dataplatform.eikon as ek
import refinitiv.data as rd
import base64

# Refinitiv API Key
ek.set_app_key(os.getenv('JULSLEO'))
app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
percentage = dash_table.FormatTemplate.percentage(3)

controls = dbc.Card(
    [
        dbc.Row([
            html.H5('Asset:',
                    style={'display': 'inline-block', 'margin-right': 20}),
            dcc.Input(id='asset', type='text', value="IVV",
                      style={'display': 'inline-block',
                             'border': '1px solid black'}),
            dbc.Table(
                [
                    html.Thead(html.Tr([html.Th('\u03B1\N{SUBSCRIPT ONE}'), html.Th("n\N{SUBSCRIPT ONE}")])),
                    html.Tbody([
                        html.Tr([
                            html.Td(
                                dbc.Input(
                                    id='alpha1',
                                    type='number',
                                    value=-0.01,
                                    max=1,
                                    min=-1,
                                    step=0.01
                                )
                            ),
                            html.Td(
                                dcc.Input(
                                    id='n1',
                                    type='number',
                                    value=3,
                                    min=1,
                                    step=1
                                )
                            )
                        ])
                    ])
                ],
                bordered=True
            ),
            dbc.Table(
                [
                    html.Thead(html.Tr([html.Th('\u03B1\N{SUBSCRIPT TWO}'), html.Th("n\N{SUBSCRIPT TWO}")])),
                    html.Tbody([
                        html.Tr([
                            html.Td(
                                dbc.Input(
                                    id='alpha2',
                                    type='number',
                                    value=0.01,
                                    max=1,
                                    min=-1,
                                    step=0.01
                                )
                            ),
                            html.Td(
                                dcc.Input(
                                    id='n2',
                                    type='number',
                                    value=5,
                                    min=1,
                                    step=1
                                )
                            )
                        ])
                    ])
                ],
                bordered=True
            )
        ]),
        dbc.Row([
            dcc.DatePickerRange(
                id='refinitiv-date-range',
                min_date_allowed=date(2015, 1, 1),
                max_date_allowed=datetime.now(),
                initial_visible_month=datetime.now()
                # start_date = datetime.date(
                #     datetime.now() - timedelta(days=3*365)),
                # end_date = datetime.now().date()
            )
        ]),
        dbc.Row(html.H6('')),
        dbc.Row(html.Button('QUERY Refinitiv', id='run-query', n_clicks=0))
    ],
    body=True
)

image = 'ss_react_graph.png'
test_base64 = base64.b64encode(open(image, 'rb').read()).decode('ascii')
img_card = dbc.Card(
    [
        html.H5('Reactive Graph', style={'text-align': 'center'}),
        dbc.CardImg(src='data:image/png;base64,{}'.format(test_base64), bottom=True)
    ]
)

app.layout = dbc.Container(
    [
        html.H6('By Ryan Claypool'),
        dbc.Row(
            [
                dbc.Col(controls, md=4, width='auto'),
                dbc.Col(img_card, md=7, width='auto')
            ],
            align="center", justify='start'
        ),
        html.H2('Trade Blotter:'),
        dash_table.DataTable(id="blotter")
    ],
    fluid=True
)


@app.callback(
    Output('blotter', 'data'),
    Input('run-query', 'n_clicks'),
    [State('refinitiv-date-range', 'start_date'), State('refinitiv-date-range', 'end_date'),
     State('asset', 'value')],
    prevent_initial_call=True
)
def render_trade_blotter(n_clicks, start_date, end_date, asset):
    prices, prc_err = ek.get_data(
        instruments=asset,
        fields=[
            'TR.OPENPRICE(Adjusted=0)',
            'TR.HIGHPRICE(Adjusted=0)',
            'TR.LOWPRICE(Adjusted=0)',
            'TR.CLOSEPRICE(Adjusted=0)',
            'TR.PriceCloseDate'
        ],
        parameters={
            'SDate': start_date,
            'EDate': end_date,
            'Frq': 'D'
        }
    )

    prices.rename(
        columns={
            'Open Price': 'open',
            'High Price': 'high',
            'Low Price': 'low',
            'Close Price': 'close'
        },
        inplace=True
    )
    prices.dropna(inplace=True)
    prices['Date'] = pd.to_datetime(prices['Date']).dt.date

    rd.open_session()
    next_business_day = rd.dates_and_calendars.add_periods(
        start_date=prices['Date'].iloc[-1].strftime("%Y-%m-%d"),
        period="1D",
        calendars=["USA"],
        date_moving_convention="NextBusinessDay",
    )
    rd.close_session()

    # PARAMETERS
    alpha1 = -0.01
    alpha2 = 0.01
    n1 = 3
    n2 = 5

    # SUBMITTED ENTRY ORDERS: BUY ASSET @ PREVIOUS CLOSE PRICE * (1 + Alpha1)
    submitted_entry_orders = pd.DataFrame({
        'trade_id': range(1, prices.shape[0]),
        'date': list(pd.to_datetime(prices['Date'].iloc[1:]).dt.date),
        'asset': asset,
        'trip': 'ENTER',
        'action': 'BUY',
        'type': 'LMT',
        'price': round(prices['close'].iloc[:-1] * (1 + alpha1), 2),
        'status': 'SUBMITTED'
    })

    # CANCELLED ENTRY ORDERS: IF SUBMITTED ENTRY ORDER DOES NOT FILL WITHIN N1 DAYS
    with np.errstate(invalid='ignore'):
        cancelled_entry_orders = submitted_entry_orders[
            np.greater(
                prices['low'].iloc[1:][::-1].rolling(3).min()[::-1].to_numpy(),
                submitted_entry_orders['price'].to_numpy()
            )
        ].copy()
    cancelled_entry_orders.reset_index(drop=True, inplace=True)
    cancelled_entry_orders['status'] = 'CANCELLED'
    cancelled_entry_orders['date'] = pd.DataFrame(
        {'cancel_date': submitted_entry_orders['date'].iloc[(n1 - 1):].to_numpy()},
        index=submitted_entry_orders['date'].iloc[:(1 - n1)].to_numpy()
    ).loc[cancelled_entry_orders['date']]['cancel_date'].to_list()

    # FILLED ENTRY ORDERS
    # ISSUE EXIT LMT ORDER TO SELL
    filled_entry_orders = submitted_entry_orders[submitted_entry_orders['trade_id'].isin(
        list(set(submitted_entry_orders['trade_id']) - set(cancelled_entry_orders['trade_id'])))].copy()
    filled_entry_orders.reset_index(drop=True, inplace=True)
    filled_entry_orders['status'] = 'FILLED'

    for i in range(0, len(filled_entry_orders)):
        idx1 = np.flatnonzero(prices['Date'] == filled_entry_orders['date'].iloc[i])[0]
        asset_slice = prices.iloc[idx1:(idx1 + n1)]['low']
        fill_inds = asset_slice <= filled_entry_orders['price'].iloc[i]
        if (len(fill_inds) < n1) & (not any(fill_inds)):
            filled_entry_orders.at[i, 'status'] = 'LIVE'
        else:
            filled_entry_orders.at[i, 'date'] = prices['Date'].iloc[fill_inds.idxmax()]

    # LIVE ENTRY ORDERS
    live_entry_orders = pd.DataFrame({
        'trade_id': prices.shape[0],
        'date': pd.to_datetime(next_business_day).date(),
        'asset': asset,
        'trip': 'ENTER',
        'action': 'BUY',
        'type': 'LMT',
        'price': round(prices['close'].iloc[-1] * (1 + alpha1), 2),
        'status': 'LIVE'
    }, index=[0])

    if any(filled_entry_orders['status'] == 'LIVE'):
        live_entry_orders = pd.concat([
            filled_entry_orders[filled_entry_orders['status'] == 'LIVE'], live_entry_orders])
        live_entry_orders['date'] = pd.to_datetime(next_business_day).date()
    filled_entry_orders = filled_entry_orders[filled_entry_orders['status'] == 'FILLED']

    # SUBMITTED EXIT ORDERS
    submitted_exit_orders = filled_entry_orders.copy()
    submitted_exit_orders['trip'] = 'EXIT'
    submitted_exit_orders['action'] = 'SELL'
    submitted_exit_orders['price'] = round(filled_entry_orders['price'] * (1 + alpha2), 2)
    submitted_exit_orders['status'] = 'SUBMITTED'
    submitted_exit_orders.reset_index(drop=True)


    # PLAN OF EXECUTION
    # (1) For each submitted order, see if the price is met ( price =< high)
    prices['Date'] = pd.to_datetime(prices['Date'], format='%Y-%m-%d')
    prices.set_index('Date', inplace=True)
    prices.sort_index(ascending=True, inplace=True)


    # Initiation of lists
    cancelled_exit_orders = pd.DataFrame(columns=['trade_id', 'date', 'asset', 'trip', 'action', 'type', 'price', 'status'])
    filled_exit_orders = pd.DataFrame(columns=['trade_id', 'date', 'asset', 'trip', 'action', 'type', 'price', 'status'])
    live_exit_orders = pd.DataFrame(columns=['trade_id', 'date', 'asset', 'trip', 'action', 'type', 'price', 'status'])
    market_orders = pd.DataFrame(columns=['trade_id', 'date', 'asset', 'trip', 'action', 'type', 'price', 'status'])

    for idx1, row in submitted_exit_orders.iterrows():  # loop through submitted exit orders by row
        order_date = pd.to_datetime(row['date'], format='%Y-%m-%d')
        order_price = row['price']
        filt = prices.index >= order_date  # Filters out price observations before order date
        trade_window = prices[filt].head(n2)  # n2 is the # of days trade is open.
        days = len(trade_window)  # to check if trade is live still or not (<n2 observations)
        if days < n2:
            is_live = True
        else:
            is_live = False
        # CODE ABOVE IS TESTED AND PASSED


        # TESTING
        # filled = pd.DataFrame(
        #     columns=['trade_id', 'date', 'asset', 'trip', 'action', 'type', 'price', 'status'])
        is_filled = False
        for idx2, daily_close in trade_window.iterrows():
            if order_price <= daily_close['close'] and is_filled == False:  # LOGIC FOR FILLED EXIT ORDERS
                is_filled = True
                filled = pd.DataFrame({
                    'trade_id': row['trade_id'],
                    'date': pd.to_datetime(idx2).date(),
                    'asset': row['asset'],
                    'trip': 'EXIT',
                    'action': 'SELL',
                    'type': 'LMT',
                    'price': row['price'],
                    'status': 'FILLED'
                }, index=[0])
                filled_exit_orders = pd.concat([filled_exit_orders, filled], axis=0)

        if is_filled == False and is_live == True:
            # WRITE LOGIC FOR LIVE - live_exit_orders
            # print(row['trade_id'], order_price)  # Test - All live orders printed
            # live = pd.DataFrame(row)
            # live['status'] = 'LIVE'
            # live['date'] = max(trade_window.index) + pd.offsets.BDay()
            live_date = max(trade_window.index) + pd.offsets.BDay()
            # live_date = pd.to_datetime(live_date, format='%Y-%m-%d')
            live = pd.DataFrame({
                'trade_id': row['trade_id'],
                'date': live_date,
                'asset': row['asset'],
                'trip': 'EXIT',
                'action': 'SELL',
                'type': 'LMT',
                'price': row['price'],
                'status': 'LIVE'
            }, index=[0])
            # live['date'] = pd.to_date(live['date']).date()
            live['date'] = pd.to_datetime(live['date'], format='%d-%m-%Y')
            live['date'] = live['date'].dt.strftime('%Y-%m-%d')
            live_exit_orders = pd.concat([live_exit_orders, live], axis=0)
            # print(live)  # Test Successful; correct blotter output
            # live_exit_orders = pd.concat([live], axis=1)
            # print("Live Order: ")
            # print(live_exit_orders)
        elif is_filled == False and is_live == False:
            # WRITE LOGIC FOR CANCELLED - cancelled_exit_orders
            cancelled = pd.DataFrame({
                'trade_id': row['trade_id'],
                'date': pd.to_datetime(idx2).date(),
                'asset': row['asset'],
                'trip': 'EXIT',
                'action': 'SELL',
                'type': 'LMT',
                'price': row['price'],
                'status': 'CANCELLED'
            }, index=[0])
            cancelled_exit_orders = pd.concat([cancelled_exit_orders, cancelled], axis=0)

            # WRITE LOGIC FOR MARKET - market_orders
            market_orders = cancelled_exit_orders.copy()
            market_price = daily_close['close'].tail(1)
            # print(market_price)
            market_orders['price'] = pd.to_datetime(market_price).date()
            market_orders['type'] = 'MKT'
            market_orders['status'] = 'FILLED'



    # TESTING FOR TABLE CORRECTNESS

    # print("Table 1 - submitted_entry_orders:")
    # print(submitted_entry_orders)  # PASS

    # print("Table 2 - cancelled_entry_orders:")
    # print(cancelled_entry_orders)  # PASS

    # print("Table 3 - filled_entry_orders:")
    # print(filled_entry_orders)  # PASS

    # print("Table 4 - live_entry_orders:")
    # print(live_entry_orders)  # PASS

    # print("Table 5 - submitted_exit_orders:")
    # print(submitted_exit_orders)  # PASS

    # print("Table 6 - cancelled_exit_orders:")
    # print(cancelled_exit_orders)  # PASS

    # print("Table 7 - filled_exit_orders:")
    # print(filled_exit_orders)  # PASS

    # print("Table 8 - live_exit_orders:")
    # print(live_exit_orders)  # PASS

    # print("Table 9 - market orders:")
    # print(market_orders)  # PASS

    blotter = pd.concat([
        submitted_entry_orders,  # PASS
        cancelled_entry_orders,  # PASS
        filled_entry_orders,  # PASS
        live_entry_orders,  # PASS
        # VERIFIED ALL ENTRY ORDERS PASSED
        submitted_exit_orders,  # PASS
        cancelled_exit_orders, # PASS
        filled_exit_orders,  # PASS
        live_exit_orders,  # PASS
        market_orders  # PASS
    ]).sort_values(['trade_id', 'trip', 'date'])

    blotter = blotter.reset_index(drop=True)

    # TEST BLOTTER OUTPUT
    print("Blotter:")
    print(blotter)  # Check

    return blotter.to_dict('records')


if __name__ == '__main__':
    app.run_server(debug=True)
