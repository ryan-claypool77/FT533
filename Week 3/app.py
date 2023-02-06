from dash import Dash, html, dcc, dash_table, Input, Output, State
import eikon as ek  # cut out refinitiv.dataplatform.eikon
import pandas as pd
import numpy as np
from datetime import datetime, date
import plotly.express as px
import os
import statsmodels as sm

ek.set_app_key(os.getenv('EIKON_API'))

# dt_prc_div_splt = pd.read_csv('unadjusted_price_history.csv')

app = Dash(__name__)
app.layout = html.Div([
    html.Div([
        # html.H5('Benchmark', id="benchmark-id"),
        html.Label('Benchmark', htmlFor="benchmark-id",
                   style={
                       'padding-right': '10px',
                       'padding-left': '10px',
                       'font-size': '20px'
                   }),
        dcc.Input(id='benchmark-id', type='text', value="IVV"),
        html.Label('Asset', htmlFor="asset-id",
                   style={
                       'padding-right': '10px',
                       'padding-left': '10px',
                       'font-size': '20px'

                   }),
        dcc.Input(id='asset-id', type='text', value="AAPL.O")
    ]),

    html.Div([
        dcc.DatePickerRange(
            id='my-date-picker-range',
            start_date_placeholder_text="2017-01-01",  # "Start Period"
            end_date_placeholder_text="2023-01-30",  # "End Period"
            calendar_orientation='vertical',
            max_date_allowed=datetime.now(),
            month_format='YYYY-MM-DD',
            style={
                'font-size': '20px'
            }
        )
    ]),
    html.Button('QUERY Refinitiv', id='run-query', n_clicks=0),
    html.H2('Raw Data from Refinitiv'),
    dash_table.DataTable(
        id="history-tbl",
        page_action='none',
        style_table={'height': '100px', 'overflowY': 'auto'}
    ),
    html.H2('Historical Returns'),
    dash_table.DataTable(
        id="returns-tbl",
        page_action='none',
        style_table={'height': '300px', 'overflowY': 'auto'}
    ),
    html.H2('Alpha & Beta Scatter Plot'),
    html.Label('Alpha:', htmlFor="alpha",
                   style={
                       'padding-right': '10px',
                       'padding-left': '30px',
                       'font-size': '20px'
                   }),
    html.H4(id='alpha'),
    html.Label('Beta:', htmlFor="alpha",
               style={
                   'padding-right': '10px',
                   'padding-left': '30px',
                   'font-size': '20px'
               }),
    html.H4(id='beta'),
    html.Div([
        dcc.DatePickerRange(
            id='my-date-picker-range-plot',
            start_date_placeholder_text="Start Period",
            end_date_placeholder_text="End Period",
            calendar_orientation='vertical',
            max_date_allowed=datetime.now(),
            month_format='YYYY-MM-DD',
            style={
                'font-size': '20px'
            }
        )
    ]),
    html.Button('Update Plot', id='run-query', n_clicks=0),
    dcc.Graph(id="ab-plot"),
    html.P(id='summary-text', children="")
])


@app.callback(
    Output("history-tbl", "data"),
    Input("run-query", "n_clicks"),
    [State('benchmark-id', 'value'), State('asset-id', 'value'),
     State('my-date-picker-range', 'start_date'), State('my-date-picker-range', 'end_date')],
    prevent_initial_call=True
)
def query_refinitiv(n_clicks, benchmark_id, asset_id, start_date, end_date):
    assets = [benchmark_id, asset_id]
    prices, prc_err = ek.get_data(
        instruments=assets,
        fields=[
            'TR.OPENPRICE(Adjusted=0)',
            'TR.HIGHPRICE(Adjusted=0)',
            'TR.LOWPRICE(Adjusted=0)',
            'TR.CLOSEPRICE(Adjusted=0)',
            'TR.PriceCloseDate'
        ],
        parameters={
            'SDate': start_date,  # example placeholder w/ formatting: '2017-01-01',
            'EDate': end_date,  # example with pulling today's date: datetime.now().strftime("%Y-%m-%d"),
            'Frq': 'D'
        }
    )

    divs, div_err = ek.get_data(
        instruments=assets,
        fields=[
            'TR.DivExDate',
            'TR.DivUnadjustedGross',
            'TR.DivType',
            'TR.DivPaymentType'
        ],
        parameters={
            'SDate': start_date,  # example placeholder w/ formatting: '2017-01-01',
            'EDate': end_date,  # example with pulling today's date: datetime.now().strftime("%Y-%m-%d"),
            'Frq': 'D'
        }
    )

    splits, splits_err = ek.get_data(
        instruments=assets,
        fields=['TR.CAEffectiveDate', 'TR.CAAdjustmentFactor'],
        parameters={
            "CAEventType": "SSP",
            'SDate': start_date,  # example placeholder w/ formatting: '2017-01-01',
            'EDate': end_date,  # example with pulling today's date: datetime.now().strftime("%Y-%m-%d"),
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

    divs.rename(
        columns={
            'Dividend Ex Date': 'Date',
            'Gross Dividend Amount': 'div_amt',
            'Dividend Type': 'div_type',
            'Dividend Payment Type': 'pay_type'
        },
        inplace=True
    )
    divs.dropna(inplace=True)
    divs['Date'] = pd.to_datetime(divs['Date']).dt.date
    divs = divs[(divs.Date.notnull()) & (divs.div_amt > 0)]

    splits.rename(
        columns={
            'Capital Change Effective Date': 'Date',
            'Adjustment Factor': 'split_rto'
        },
        inplace=True
    )
    splits.dropna(inplace=True)
    splits['Date'] = pd.to_datetime(splits['Date']).dt.date

    unadjusted_price_history = pd.merge(
        prices, divs[['Instrument', 'Date', 'div_amt']],
        how='outer',
        on=['Date', 'Instrument']
    )
    unadjusted_price_history['div_amt'].fillna(0, inplace=True)

    unadjusted_price_history = pd.merge(
        unadjusted_price_history, splits,
        how='outer',
        on=['Date', 'Instrument']
    )
    unadjusted_price_history['split_rto'].fillna(1, inplace=True)

    if unadjusted_price_history.isnull().values.any():
        raise Exception('missing values detected!')

    return unadjusted_price_history.to_dict('records')


@app.callback(
    Output("returns-tbl", "data"),
    Input("history-tbl", "data"),
    [State('my-date-picker-range-plot', 'start_date'), State('my-date-picker-range-plot', 'end_date')],
    prevent_initial_call=True
)
def calculate_returns(history_tbl, start_date, end_date):
    dt_prc_div_splt = pd.DataFrame(history_tbl)

    if start_date is not None:
        if end_date is not None:
            dt_prc_div_splt = dt_prc_div_splt.loc[(dt_prc_div_splt['Date'] >= start_date)
                                                  & (dt_prc_div_splt['Date'] <= end_date)]



    # Define what columns contain the Identifier, date, price, div, & split info
    ins_col = 'Instrument'
    dte_col = 'Date'
    prc_col = 'close'
    div_col = 'div_amt'
    spt_col = 'split_rto'

    dt_prc_div_splt[dte_col] = pd.to_datetime(dt_prc_div_splt[dte_col])
    dt_prc_div_splt = dt_prc_div_splt.sort_values([ins_col, dte_col])[
        [ins_col, dte_col, prc_col, div_col, spt_col]].groupby(ins_col)
    numerator = dt_prc_div_splt[[dte_col, ins_col, prc_col, div_col]].tail(-1)
    denominator = dt_prc_div_splt[[prc_col, spt_col]].head(-1)

    return (
        pd.DataFrame({
            'Date': numerator[dte_col].reset_index(drop=True),
            'Instrument': numerator[ins_col].reset_index(drop=True),
            'rtn': np.log(
                (numerator[prc_col] + numerator[div_col]).reset_index(drop=True) / (
                        denominator[prc_col] * denominator[spt_col]
                ).reset_index(drop=True)
            )
        }).pivot_table(
            values='rtn', index='Date', columns='Instrument'
        ).to_dict('records')
    )


@app.callback(
    Output("ab-plot", "figure"),
    Input("returns-tbl", "data"),
    [State('benchmark-id', 'value'), State('asset-id', 'value')],
    prevent_initial_call=True
)
def render_ab_plot(returns, benchmark_id, asset_id):
    plot = px.scatter(returns, x=benchmark_id, y=asset_id, trendline='ols')
    model = px.get_trendline_results(plot)
    results = model.iloc[0]["px_fit_results"]
    alpha = results.params[0]
    beta = results.params[1]

    return (
        px.scatter(returns, x=benchmark_id, y=asset_id, trendline='ols')
        # print on the web page (Alpha, Beta)
    )


if __name__ == '__main__':
    app.run_server(debug=True)
