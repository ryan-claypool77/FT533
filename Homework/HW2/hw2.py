import pandas as pd

stock_data = pd.read_csv('IVV.csv')
print(stock_data)

# sandbox for playing around with DataFrames in Pandas https://www.dataquest.io/blog/tutorial-indexing-dataframes-in-pandas/#:~:text=Essentially%2C%20there%20are%20two%20main,different%20types%20of%20dataframe%20indexing.
print(stock_data[['Date', 'Close']])

# Parameters
# alpha1: %, default = -1%
# n1: integer, default = 3
# alpha2: %, default = 1%
# n2: integer, default = 5
# asset: string, default = 'IVV'

# Task: Create an interactive backtest in Dash for a simple strategy
# Strategy:
# 1. Before market open each morning, submit a limit order to buy asset at
#    Entry Price = (1 + alpha1) * Yesterday Close
# 2. If the limit order does not fill within n1 trading days then cancel it.
# 3. If the limit order does fill, then IMMEDIATELY issue a limit order to sell the asset at
#    Exit Price = (1 + alpha2) * Price Entry
# 4. If the exit order is not filled by the time the market is about to close at the end of the
#    (n2)th trading day, then CANCEL it and immediately issue a market order to sell. You may
#    assume you get the day's closing price.

"""
Design Idea:
*** Abstract enough to plug in Refinitiv in place of IVV later; model everything on IVV
*** Before moving to Refinitiv, run UnitTest on critical functions
1. 

"""


class Order:
    def __init__(self):
        self.alpha1 = -.01
        self.n1 = 3
        self.alpha2 = .01
        self.n2 = 5
        self.asset = 'IVV'  # in the future, this needs to be fed in as a parameter from Refinitiv
        self.data = pd.read_csv('IVV.csv')

    def buy_strategy(self, entry_price):
        pass
        # 1. Create a loop that indexes over n1 trading days (logic for weekends?),
        # 2. Two Paths:
        #    i. Cancel
        #    ii. Log the buy in the blotter and call sell_strategy(entry_price) immediately

    def sell_strategy(self, entry_price):
        pass
        # 1. Create a loop that indexes over n2 trading days (logic for weekends?),
        # 2. Two Paths:
        #    i. Fill the sell order and log sale on blotter.
        #    ii. Exit the order if not filled by the time the market is about to close at the end of the
    #        (n2)th trading day, immediately post a market order sale to blotter at closing price.


if __name__ == "__main__":
    pass
