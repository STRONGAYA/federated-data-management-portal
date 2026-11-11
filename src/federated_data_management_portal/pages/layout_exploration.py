import dash

from dash import html, dcc, dash_table

from federated_data_management_portal import chrome

dash.register_page(__name__, path='/data-exploration', title=chrome.PAGE_TITLE)

layout = chrome.page_scaffold(
    content=[
        html.Div(id='tile-exploration-categorical', className='tile tile-7', children=[
            html.H5('Variable info', className='tile-title'),
            html.Div(className='options-row', children=[
                "Select the organisation(s) for this chart",
                dcc.Checklist(
                    id='exploration-subset-selection-checkboxes', className='subset-selection-checkboxes',
                    options=[],
                    value=[],
                    labelStyle={'display': 'inline-block'}
                )]),
            html.Div(className='filter-bar', children=[
                html.Div(children=[
                    dcc.Dropdown(
                        id='exploration-categorical-variable',
                        className='pill-dropdown',
                        options=[],
                        value=None,
                        placeholder='Categorical variable',
                        clearable=False
                    )]),
                html.Div(className='filter-wrap visualisation-selector', children=[
                    html.Button([
                        'Select visualisation ',
                        html.Span(id='exploration-view-indicator', className='view-type-indicator',
                                  children='(Pie chart)'),
                        html.I(className='fas fa-chevron-down'),
                    ], id='exploration-view-toggle', className='vis-btn view-selection-btn'),
                    html.Div(id='exploration-view-menu', className='filter-dropdown', hidden=True, children=[
                        html.Button('Pie chart', id='exploration-view-pie', className='filter-option current'),
                        html.Button('Bar chart', id='exploration-view-bar', className='filter-option'),
                        html.Button('CSV', id='exploration-view-csv', className='filter-option'),
                    ]),
                    dcc.Store(id='exploration-view-store', data='pie'),
                ]),
            ]),
            html.Hr(className='tile-divider'),
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
                html.Button('Download CSV', id='exploration-csv-download-btn', className='portal-btn'),
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
                    className='pill-dropdown',
                    options=[],
                    value=None,
                    clearable=False
                )]),
            html.Hr(className='tile-divider'),
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
