import dash

import dash_bootstrap_components as dbc

from dash import html, dcc

from federated_data_management_portal import chrome

dash.register_page(__name__, path='/data-availability', title=chrome.PAGE_TITLE)

layout = chrome.page_scaffold(
    content=[
        html.Div([
            html.H3(id='availability-title', className='page-title', children='Data availability'),
            html.Hr(className='tile-divider'),
            dbc.Row([
                dbc.Col(
                    html.Div(id='tile-4', className='tile tile-4', children=[
                        dcc.Graph(
                            id={'type': 'dynamic-donut-one', 'index': 1},
                            config=chrome.graph_config('proportions-per-organisation', width=700)
                        )
                    ]),
                    width=6, lg=6, md=12, sm=12, xs=12),
                dbc.Col(
                    html.Div(id='tile-5', className='tile tile-5', children=[
                        dcc.Graph(
                            id={'type': 'dynamic-donut-two', 'index': 2},
                            config=chrome.graph_config('proportions-per-country', width=700)
                        )
                    ]),
                    width=6, lg=6, md=12, sm=12, xs=12)
            ])
        ]),
        html.Div(id='tile-7', className='tile tile-7', children=[
            html.H5('Data availability over time', className='tile-title'),
            html.Hr(className='tile-divider'),
            html.Div(id='tile-content-8', className='tile-content', children=[
                dcc.Graph(
                    id='availability-over-time',
                    config=chrome.graph_config('availability-over-time')
                )
            ])
        ]),
        html.Div(id='tile-6', className='tile tile-6', children=[
            html.H5('Semantic consistency', className='tile-title'),
            html.Div(className='options-row', children=[
                "Select the subset(s) you would like to visualise",
                dcc.Checklist(
                    id='subset-prefix-selection-checkboxes', className='subset-selection-checkboxes',
                    options=[],
                    value=[],
                    labelStyle={'display': 'inline-block'}
                )]),
            html.Hr(className='tile-divider'),
            html.Div(id='tile-content-6', className='tile-content')
        ]),
    ],
    prev_topic=('Plausibility', '/data-plausibility'),
    next_topic=('Completeness', '/data-completeness'),
    explanation=["Graphics aim to visualise how much data is available per location and "
                 "explore the existence of expected and "
                 "possible values between variables with "
                 "semantic relationships between them.",
                 html.Br(), html.Br(),
                 'Availability and semantic consistency is the "Descriptive statistics" Vantage6 algorithm ',
                 html.Br(),
                 '(see https://github.com/STRONGAYA/v6-descriptive-statistics)']
)
