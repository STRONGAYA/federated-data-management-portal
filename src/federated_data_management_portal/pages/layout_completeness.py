import dash

import dash_bootstrap_components as dbc

from dash import html, dcc

from federated_data_management_portal import chrome

dash.register_page(__name__, path='/data-completeness', title=chrome.PAGE_TITLE)

layout = chrome.page_scaffold(
    content=[
        html.Div([
            html.H3(id='completeness-title', className='page-title',
                    children='Data completeness'),
            dbc.Row([
                dbc.Col(
                    html.Div(id='tile-4', className='tile tile-4', children=[
                        chrome.chart_area(dcc.Graph(
                            id={'type': 'dynamic-donut-three', 'index': 1},
                            config=chrome.graph_config('missing-per-organisation', width=700)
                        ))
                    ]),
                    width=6, lg=6, md=12, sm=12, xs=12),
                dbc.Col(
                    html.Div(id='tile-5', className='tile tile-5', children=[
                        chrome.chart_area(dcc.Graph(
                            id={'type': 'dynamic-donut-four', 'index': 2},
                            config=chrome.graph_config('missing-per-country', width=700)
                        ))
                    ]),
                    width=6, lg=6, md=12, sm=12, xs=12)
            ])
        ]),
        html.Div(id='tile-7', className='tile tile-6', children=[
            html.H5('Variable completeness', className='tile-title'),
            html.Div(className='options-row', children=[
                "Select the subset(s) you would like to visualise",
                dcc.Checklist(
                    id='subset-prefix-selection-checkboxes', className='subset-selection-checkboxes',
                    options=[],
                    value=[],
                    labelStyle={'display': 'inline-block'}
                )]),
            html.Div(className='options-row', children=[
                "Select the organisation(s) you would like to visualise",
                dcc.Checklist(
                    id='subset-selection-checkboxes', className='subset-selection-checkboxes',
                    options=[],
                    value=[],
                    labelStyle={'display': 'inline-block'}
                )]),
            chrome.chart_toolbar(view_switch=('completeness', [('bar', 'Bar chart'), ('pie', 'Pie chart')], ('bar', 'Bar chart'))),
            html.Hr(className='tile-divider'),
            html.Div(id='tile-content-7', className='tile-content', children=[
                dcc.Graph(
                    id={'type': 'dynamic-completeness-bar', 'index': 3},
                    config=chrome.graph_config('variable-completeness', width=700),
                    figure={
                        'layout': {
                            'yaxis': {'fixedrange': True}
                        }
                    }
                )
            ]),
            html.Div(children=[
                html.Br(),
                "This graphic contains information about the following countries:",
                dcc.Checklist(
                    id='country-selection-checkboxes', className='country-selection-checkboxes',
                    options=[],
                    value=[],
                    labelStyle={'display': 'inline-block'}
                )])
        ]),
    ],
    prev_topic=('Availability', '/data-availability'),
    next_topic=('Plausibility', '/data-plausibility'),
    explanation=['The shown graphics aim to portray the absence of data at a single moment in time '
                 'without reference to its structure or plausibility.',
                 html.Br(), html.Br(),
                 'Data completeness is based on the "Descriptive statistics" Vantage6 algorithm ',
                 html.Br(),
                 '(see https://github.com/STRONGAYA/v6-descriptive-statistics)']
)
