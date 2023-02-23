"""
Parameters
alpha1: %, default = -1%
n1: integer, default = 3
alpha2: %, default = 1%
n2: integer, default = 5
asset: string, default = 'IVV'

Task: Create an interactive backtest in Dash for a simple strategy

Strategy:
1. Before market open each morning, submit a limit order to buy asset at
    Entry Price = (1 + alpha1) * Yesterday Close
2. If the limit order does not fill within n1 trading days then cancel it.
3. If the limit order does fill, then IMMEDIATELY issue a limit order to sell the asset at
   Exit Price = (1 + alpha2) * Price Entry
4. If the exit order is not filled by the time the market is about to close at the end of the
    (n2)th trading day, then CANCEL it and immediately issue a market order to sell. You may
    assume you get the day's closing price.


Design Notes:
*** Abstract enough to plug in Refinitiv in place of IVV later; model everything on IVV
*** Before moving to Refinitiv, run UnitTest on critical functions

"""
import pandas as pd

# Redesign for Refinitiv data creating a csv file for the user's requested stock
asset = 'IVV'  # in the future, this needs to be fed in as a parameter from Refinitiv
stock_data = pd.read_csv('IVV.csv')

# trading parameters for buy and sell orders
alpha1 = -.01  # buying -1% below yest. close
n1 = 3  # days buy order is open
alpha2 = .01  # selling +1% above entry_price
n2 = 5  # days sell order is open


# sandbox for playing around with DataFrames in Pandas https://www.dataquest.io/blog/tutorial-indexing-dataframes-in-pandas/#:~:text=Essentially%2C%20there%20are%20two%20main,different%20types%20of%20dataframe%20indexing.
# print(stock_data)
# print(stock_data[['Date', 'Close']])


class Order:
    trade_id = 0

    def __init__(self, date, trip, action, order_type):
        Order.trade_id += 1
        self.date = date
        self.asset = asset
        self.trip = trip  # Enter/Exit
        self.action = action
        self.type = order_type
        self.price = buy_price(stock_data[['Close']])

        # use Unittest to check an Order before expanding


def buy_price(close):
    result = close
    return result  # placeholder
    # 1. Create a loop that indexes over n1 trading days (logic for weekends?), by trade ID
    # 2. Two Paths:
    #    i.  Cancel
    #    ii. Log the buy in the blotter and call sell_strategy(entry_price) immediately


def sell_price(entry_price):
    result = entry_price  # placeholder
    return result  # should return sell price
    # 1. Create a loop that indexes over n2 trading days (logic for weekends?),
    # 2. Two Paths:
    #    i.  Fill the sell order and log sale on blotter.
    #    ii. Exit the order if not filled by the time the market is about to close at the end of the
    #        (n2)th trading day, immediately post a market order sale to blotter at closing price.


if __name__ == "__main__":
    pass

    # 1. Sort csv by date (maybe in the initialization?)
    # 2. While-loop the Pandas dataframe
    # 3. For each day on the csv, create an Order object that fills the parameters in the blotter table
