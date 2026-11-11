import dash

import dash_bootstrap_components as dbc

from dash import html, dcc

from federated_data_management_portal import chrome

dash.register_page(__name__, path='/data-plausibility', title=chrome.PAGE_TITLE)

layout = chrome.page_scaffold(
    content=[
        html.Div([
            html.H3(id='plausibility-title', className='page-title',
                    children='Data plausibility'),
            dbc.Row([
                dbc.Col(
                    html.Div(id='tile-4', className='tile tile-4', children=[
                        chrome.chart_area(dcc.Graph(
                            id={'type': 'dynamic-donut-five', 'index': 1},
                            config=chrome.graph_config('plausible-per-organisation', width=700)
                        ))
                    ]),
                    width=6, lg=6, md=12, sm=12, xs=12),
                dbc.Col(
                    html.Div(id='tile-5', className='tile tile-5', children=[
                        chrome.chart_area(dcc.Graph(
                            id={'type': 'dynamic-donut-six', 'index': 2},
                            config=chrome.graph_config('plausible-per-country', width=700)
                        ))
                    ]),
                    width=6, lg=6, md=12, sm=12, xs=12)
            ])
        ]),
        html.Div(id='tile-7', className='tile tile-6', children=[
            html.H5('Atemporal plausibility', className='tile-title'),
            html.Div(className='options-row', children=[
                dcc.Dropdown(
                    id='plausibility-variable-dropdown',
                    className='pill-dropdown',
                    options=[],
                    value=[],
                    multi=True,
                    placeholder='Variables',
                    clearable=True
                )]),
            html.Div(className='options-row', children=[
                "Select the organisation(s) you would like to visualise",
                dcc.Checklist(
                    id='subset-selection-checkboxes', className='subset-selection-checkboxes',
                    options=[],
                    value=[],
                    labelStyle={'display': 'inline-block'}
                )]),
            chrome.chart_toolbar(view_switch=('plausibility', [('bar', 'Bar chart'), ('pie', 'Pie chart')], ('bar', 'Bar chart'))),
            html.Hr(className='tile-divider'),
            html.Div(id='tile-content-7', className='tile-content', children=[
                dcc.Graph(
                    id={'type': 'dynamic-plausibility-bar', 'index': 3},
                    config=chrome.graph_config('variable-atemporal-plausibility', width=700),
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
    prev_topic=('Completeness', '/data-completeness'),
    next_topic=('Data exploration', '/data-exploration'),
    explanation=['The shown graphics aim to portray the believability or truthfulness of data values '
                 'by assessing the acceptable variable value range and '
                 'distribution in both atemporal as temporal data fields.',
                 html.Br(), html.Br(),
                 'Data plausibility is based on the "Descriptive statistics" Vantage6 algorithm ',
                 html.Br(),
                 '(see https://github.com/STRONGAYA/v6-descriptive-statistics)']
)
