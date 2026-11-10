import dash

from dash import html, dcc, dash_table

from federated_data_management_portal import chrome

dash.register_page(__name__, path='/data-exploration', title=chrome.PAGE_TITLE)

layout = chrome.page_scaffold(
    content=[
        html.Div(id='tile-exploration-categorical', className='tile tile-7', children=[
            html.H5('Variable info', className='tile-title'),
            html.Div(children=[
                "Select the organisation(s) for this chart",
                dcc.Checklist(
                    id='exploration-subset-selection-checkboxes', className='subset-selection-checkboxes',
                    options=[],
                    value=[],
                    labelStyle={'display': 'inline-block'}
                )]),
            html.Div(children=[
                "Select the categorical variable",
                dcc.Dropdown(
                    id='exploration-categorical-variable',
                    options=[],
                    value=None,
                    clearable=False
                )]),
            html.Div(children=[
                "View as ",
                dcc.RadioItems(
                    id='exploration-categorical-view',
                    options=[
                        {'label': 'Pie chart', 'value': 'pie'},
                        {'label': 'Bar chart', 'value': 'bar'},
                        {'label': 'CSV', 'value': 'csv'},
                    ],
                    value='pie',
                    inline=True,
                    labelStyle={'display': 'inline-block'}
                )]),
            dcc.Graph(
                id='exploration-categorical-graph',
                config=chrome.graph_config('categorical-variable-counts')
            ),
            html.Div(id='exploration-categorical-csv', hidden=True, children=[
                dash_table.DataTable(
                    id='exploration-categorical-csv-table',
                    columns=[{'name': 'Category', 'id': 'category'},
                             {'name': 'Count', 'id': 'count'}]
                ),
                html.Button('Download CSV', id='exploration-csv-download-btn'),
                dcc.Download(id='exploration-csv-download')
            ]),
            dcc.Store(id='exploration-csv-store')
        ]),
        html.Div(id='tile-exploration-distributions', className='tile tile-7', children=[
            html.H5('Data distributions', className='tile-title'),
            html.Div(className='explanation', children=[
                "Based on the central aggregate result across all organisations; "
                "the organisation selection above does not apply here."
            ]),
            html.Div(children=[
                "Select the variable you would like to visualise",
                dcc.Dropdown(
                    id='exploration-variable-dropdown',
                    options=[],
                    value=None,
                    clearable=False
                )]),
            html.Div(id='tile-content-exploration-distribution', className='tile-content', children=[
                dcc.Graph(
                    id='exploration-distribution-graph',
                    config=chrome.graph_config('federated-distribution')
                )
            ]),
            html.Div(id='exploration-distribution-stats', className='explanation', children=[]),
            html.Div(id='exploration-distribution-disclaimer', className='explanation', children=[
                "The curve is an approximation reconstructed from the federated quartiles "
                "(q1, median, q3) and IQR; min/max and raw values are not part of the central "
                "aggregate result."
            ])
        ]),
    ],
    prev_topic=('Plausibility', '/data-plausibility'),
    next_topic=('Availability', '/data-availability'),
    explanation=["Graphics aim to visualise the aggregate data distributions as density curves "
                 "reconstructed from the federated quartiles and IQR, and key variable "
                 "characteristics such as the biological sex balance and the grouped cancer types.",
                 html.Br(), html.Br(),
                 'Distributions and variable info are based on the "Descriptive statistics" Vantage6 '
                 'algorithm ',
                 html.Br(),
                 '(see https://github.com/STRONGAYA/v6-descriptive-statistics)']
)
