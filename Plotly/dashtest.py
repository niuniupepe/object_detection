#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#12/16
import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output,State
from pandas_datareader import data as web
from datetime import datetime
import json
from urllib.request import urlopen


def get_jsonparsed_data(url):
    response = urlopen(url)
    data = response.read().decode("utf-8")
    return json.loads(data)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

if 'DYNO' in os.environ:
    app_name = os.environ['DASH_APP_NAME']
else:
    app_name = 'dash-timeseriesplot'

url = ("https://financialmodelingprep.com/api/v3/company/stock/list")
list_tics = get_jsonparsed_data(url)["symbolsList"]
dropdown = {}
for d in list_tics:
    d['value'] = d.pop('symbol')
    d['label'] = d.pop('name')
    del d['price']
    drd = {d['value']:d['label']}
    d['label'] = d['value'] + ":" +d['label']
    dropdown.update(drd)
end = datetime.now().strftime("%Y/%m/%d")
start=datetime(datetime.today().year-10, 1,1)

#Financial Matrix List Value
url = ("https://financialmodelingprep.com/api/v3/financials/income-statement/AAPL?period=quarter")
list_fin = pd.DataFrame( get_jsonparsed_data(url)["financials"]).drop(['date'], axis=1).columns.values
dropdown_fin = { }
drd_fin = []
for d in list_fin:
    dropdown_fin["value"]=d
    dropdown_fin["label"] =d
    drd_fin.append(dict(dropdown_fin))

df_histdivs = web.DataReader("AAPL", 'yahoo-dividends', start, end)
dvbyyear = df_histdivs.groupby(pd.Grouper(freq='Y')).sum()
dvbyyear = dvbyyear.rename(columns={'value': 'DIV'})


app.layout = html.Div([
    html.Div([html.H1("US Stock Analysis")],style={'textAlign': 'center'}),
    html.Div(dcc.Dropdown(id='my-dropdown',options=list_tics,
                multi=False,value='AAPL',style={"display": "block","margin-left": "auto","margin-right": "auto","width": "90%"}),),
    html.Div
        ([
            html.H6("Fundmental", style={'textAlign': 'center'}),
            html.Div
            ([dcc.Dropdown(id='Fin-dropdown', options=drd_fin,
                     multi=False, value='EPS Diluted',
                     style={"display": "block", "margin-left": "auto", "margin-right": "auto", "width": "80%"}),],style={'width': '45%'},className="two columns"),
            html.Div
            ([
            dcc.Dropdown(id='BSPL-dropdown',
                    options=[{"value":"company-key-metrics","label":"Popular Metrics"},{"value":"financials/balance-sheet-statement","label":"B/S"},
                             {"value":"financials/income-statement","label":"P/L"},{"value":"financials/cash-flow-statement","label":"C/F"},],
                    multi=False, value='financials/income-statement',
                    style={"display": "block", "margin-left": "auto", "margin-right": "auto", "width": "80%"}),],style={'width': '45%'},className="two columns"),

            dcc.RadioItems(
                        id='time-type',
                        options=[{'label': i, 'value': i} for i in ['Year', 'Quarter']],
                        value='Year',
                        labelStyle={'display': 'inline-block'}
                    ),
            dcc.RadioItems(
                        id='yaxis-type',
                        options=[{'label': i, 'value': i} for i in ['Linear', 'Log']],
                        value='Linear',
                        labelStyle={'display': 'inline-block'}
                    ),
            dcc.Graph(id='fundmental-graph'),

        ],style={'width': '45%'},className="two columns"),

    html.Div
        ([
            html.H6("Dividend", style={'textAlign': 'center'}),
            html.Div(),
            dcc.Graph(id='dividend-graph',hoverData = {'points': [{'text': 'AAPL'}]}),
        ],style={'width': '45%'},className="two columns"),

    ])


#Dropdown action
@app.callback(
    [Output('Fin-dropdown', 'options'),Output('Fin-dropdown', 'value')],
    [Input("BSPL-dropdown","value")])
def update_fundmental_dropdown_matrix(bspl):
    url = ("https://financialmodelingprep.com/api/v3/{}/AAPL?period=quarter")
    if bspl=="company-key-metrics":
        list_fin = pd.DataFrame(get_jsonparsed_data(url.format(bspl))["metrics"]).drop(['date'], axis=1).columns.values
    else:
        list_fin = pd.DataFrame(get_jsonparsed_data(url.format(bspl))["financials"]).drop(['date'], axis=1).columns.values
    dropdown_fin = {}
    drd_fin = []
    defaultvalue = list_fin[0]
    for d in list_fin:
        dropdown_fin["value"] = d
        dropdown_fin["label"] = d
        drd_fin.append(dict(dropdown_fin))
    return drd_fin, defaultvalue


#Fundmental Chart
@app.callback(
    Output('fundmental-graph', 'figure'),
    [Input('my-dropdown', 'value'),
     Input('Fin-dropdown','value'),
     Input('time-type','value'),
     Input('yaxis-type','value')],
    [State("BSPL-dropdown","value")])
def display_fundmental_data(tic,matrix,timetype,yaxis_type,bspltype):
    if tic is None or len(tic) == 0:
        tic = "AAPL"

    if timetype == "Year":
        url = ("https://financialmodelingprep.com/api/v3/{}/{}")
    else:
        url = ("https://financialmodelingprep.com/api/v3/{}/{}?period=quarter")

    if bspltype == "company-key-metrics":
        df_pl = pd.DataFrame(get_jsonparsed_data(url.format(bspltype,tic))["metrics"])
    else:
        df_pl = pd.DataFrame(get_jsonparsed_data(url.format(bspltype,tic))["financials"])
    df_pl.set_index('date', inplace=True)

    df_price = web.DataReader(tic, 'yahoo', df_pl.index.min(), end)
    df_price = df_price.resample('D').ffill()
    df = df_price.merge(df_pl, left_index=True, right_index=True, how='left')
    # df = df.fillna(method='pad')


    figure = { 'data': [
                    go.Scatter(x=df.index, y=df[matrix], connectgaps=True,mode='lines+markers', name=f"{tic}{matrix}", yaxis='y1'),
                    go.Scatter( x=df.index, y=df["Adj Close"],mode='lines',name=f"{tic}Adj Close", yaxis='y2'),
                    ],
                    'layout': go.Layout(title=tic,
                    xaxis={
                        'title': 'Year',
                        'rangeselector': {'buttons': list(
                            [{'count': 1, 'label': '1Y', 'step': 'year', 'stepmode': 'backward'},
                             {'count': 5, 'label': '5Y', 'step': 'year', 'stepmode': 'backward'},
                             {'count': 10, 'label': '10Y', 'step': 'year', 'stepmode': 'backward'},
                             {'step': 'all'}])},
                        'rangeslider': {'visible': True}, 'type': 'date'
                            },

                    yaxis={
                        'title': matrix,
                    },
                    yaxis2={
                        'title': 'Price',
                        'overlaying': 'y1',
                        'side': 'right','showgrid': False,
                         'type': 'linear' if yaxis_type == 'Linear' else 'log'
                    },

                    margin={'l': 45, 'b': 40, 't': 40, 'r': 40},
                            hovermode='closest',
                        showlegend=False,
                        ) }

    return figure
#Dividend
@app.callback(
    Output('dividend-graph', 'figure'),
    [Input('my-dropdown', 'value'),
     ])
def display_dividend_data(tic):
    if tic is None or len(tic) == 0:
        tic = "AAPL"

    df = pd.DataFrame()
    dfprice = web.DataReader(tic, 'yahoo', start, end)

    dfprice["Stock"] = tic
    dfprice = dfprice.asfreq(freq='D', method='bfill')

    df_div = web.DataReader(tic, 'yahoo-dividends', start, end)
    df_div = df_div.rename(columns={'value': 'DIV'})
    dv = df_div.groupby(pd.Grouper(freq='BA')).sum()
    dfprice = dfprice.merge(dv, left_index=True, right_index=True, how='outer')
    dfprice["DIV"] = dfprice["DIV"].fillna(value=0)
    dfprice['Yield'] = dfprice['DIV'] / dfprice['Close']
    dfprice['Yield'] = dfprice['Yield'].map(lambda n: '{:,.2%}'.format(n))
    df = df.append(dfprice)

    trace1 = []
    trace2 = []
    dff = df.asfreq("BA")
    trace1.append(go.Bar(x=dff.index, y=dff['DIV'],name=f"Div(USD)",text= dff["Stock"], yaxis='y1'))
    trace2.append(go.Scatter(x=dff.index, y=dff['Yield'], name=f"Yield",yaxis='y2'))
    # trace2.append(go.Scatter(x=dff.index, y=dff['DIV'].pct_change().fillna(0).map(lambda n: '{:,.2%}'.format(n)),
    #                          name=f"Growth",connectgaps=True,mode='lines+markers',yaxis='y3'))
    traces = [trace1, trace2]
    data = [val for sublist in traces for val in sublist]
    figure = {'data': data,

            'layout': go.Layout(
                barmode= 'group',clickmode = 'event+select',
                margin= {'l': 30, 'b': 40, 'r': 10, 't': 20},
                showlegend=True,
                legend={
                    'x':0,
                    'y':1,
                    'traceorder':"normal",
                },
                yaxis= {'title':f"Div",'showgrid': False,},
                yaxis2= {
                             'title': 'Yield',
                             'overlaying': 'y1','showgrid': False,
                             'side': 'right',"anchor":"x",
                         },
                # yaxis3= {
                #     'title': 'Growth',
                #     'overlaying': 'y1',
                #     'side': 'right',"anchor":"free","position":0.95,
                # },
                xaxis = {
                'title': 'Year',#'domain':[0, 0.85],
                'rangeselector': {'buttons': list(
                    [{'count': 1, 'label': '1Y', 'step': 'year', 'stepmode': 'backward'},
                     {'count': 5, 'label': '5Y', 'step': 'year', 'stepmode': 'backward'},
                     {'count': 10, 'label': '10Y', 'step': 'year', 'stepmode': 'backward'},
                     {'step': 'all'}])},
                'rangeslider': {'visible': True}, 'type': 'date'
                },)
            }

    return figure




if __name__ == '__main__':
    app.run_server(debug=False)
