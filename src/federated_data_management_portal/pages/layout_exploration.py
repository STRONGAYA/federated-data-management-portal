import dash

from dash import html, dcc, dash_table

from federated_data_management_portal import chrome

dash.register_page(__name__, path='/data-exploration', title=chrome.PAGE_TITLE)

layout = chrome.page_scaffold(
    content=[
        html.Div(id='tile-exploration-categorical', className='tile tile-7', children=[
            html.H5('Categorical variables', className='tile-title'),
            html.Div(className='options-row', children=[
                "Select the organisation(s) for these charts",
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
            ]),
            html.Hr(className='tile-divider'),
            # the per-organisation chart is its own section: label on the left,
            # visualisation selector and download on the right
            html.Div(className='exploration-categorical-section', children=[
                html.Div(className='filter-bar', children=[
                    html.Div('Selected organisations', className='exploration-plot-label'),
                    chrome.toolbar_right(
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
                        chrome.plot_download_control(include_csv=True, csv_button_id='exploration-csv-download-btn'),
                    ),
                ]),
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
                ]),
                dcc.Store(id='exploration-csv-store'),
                dcc.Download(id='exploration-csv-download'),
            ]),
            # the per-country chart is its own section below a subtle dotted
            # line, with its own visualisation selector and download button;
            # it follows the same organisation selection
            html.Hr(className='exploration-categorical-divider'),
            html.Div(className='exploration-country-section', children=[
                html.Div(className='filter-bar', children=[
                    html.Div('Per country (selected organisations)',
                             className='exploration-plot-label'),
                    chrome.toolbar_right(
                        html.Div(className='filter-wrap visualisation-selector', children=[
                            html.Button([
                                'Select visualisation ',
                                html.Span(id='exploration-country-view-indicator',
                                          className='view-type-indicator',
                                          children='(Bar chart)'),
                                html.I(className='fas fa-chevron-down'),
                            ], id='exploration-country-view-toggle',
                               className='vis-btn view-selection-btn'),
                            html.Div(id='exploration-country-view-menu',
                                     className='filter-dropdown', hidden=True, children=[
                                html.Button('Bar chart', id='exploration-country-view-bar',
                                            className='filter-option current'),
                                html.Button('Proportions', id='exploration-country-view-percent',
                                            className='filter-option'),
                                html.Button('CSV', id='exploration-country-view-csv',
                                            className='filter-option'),
                            ]),
                            dcc.Store(id='exploration-country-view-store', data='bar'),
                        ]),
                        chrome.plot_download_control(
                            include_csv=True, csv_button_id='exploration-country-csv-download-btn'),
                    ),
                ]),
                dcc.Graph(
                    id='exploration-categorical-graph-country',
                    config=chrome.graph_config('categorical-variable-counts-per-country')
                ),
                html.Div(id='exploration-categorical-country-csv', hidden=True, children=[
                    dash_table.DataTable(
                        id='exploration-categorical-country-csv-table',
                        columns=[{'name': 'Country', 'id': 'country'},
                                 {'name': 'Category', 'id': 'category'},
                                 {'name': 'Count', 'id': 'count'}]
                    ),
                ]),
                dcc.Store(id='exploration-country-csv-store'),
                dcc.Download(id='exploration-country-csv-download'),
            ]),
        ]),
        html.Div(id='tile-exploration-distributions', className='tile tile-7', children=[
            html.H5('Numerical variables', className='tile-title'),
            html.Div(className='explanation', children=[
                "Based on the central aggregate result across all organisations; "
                "the organisation selection above does not apply here."
            ]),
            html.Div(className='filter-bar', children=[
                html.Div(children=[
                    dcc.Dropdown(
                        id='exploration-variable-dropdown',
                        className='pill-dropdown',
                        options=[],
                        value=None,
                        placeholder='Numerical variable',
                        clearable=False
                    )]),
                chrome.toolbar_right(chrome.plot_download_control()),
            ]),
            html.Hr(className='tile-divider'),
            html.Div(id='tile-content-exploration-distribution', className='tile-content', children=[
                dcc.Graph(
                    id='exploration-distribution-graph',
                    config=chrome.graph_config('federated-distribution')
                )
            ]),
            html.Div(id='exploration-distribution-stats', className='explanation', children=[]),
            html.Div(id='exploration-distribution-warnings', className='explanation', children=[]),
            html.Div(id='exploration-distribution-disclaimer', className='explanation', children=[
                "The solid line is what the federated quartiles record: the Q1–Q3 range, which "
                "holds the middle 50% of patients in a typical organisation, with the Q1, Q2 and "
                "Q3 values labelled in the plot and the median marked by a short dashed tick. No "
                "density curve is drawn, because the quartiles do "
                "not record the shape or peak of the distribution. The grey dashed extensions "
                "show that a further 25% of patients lie on each side of the IQR, but their "
                "actual range is not shared (minimum, maximum and raw values are removed), so "
                "that extent is inferred, not recorded. The federated quartiles combine each "
                "organisation's quartiles, so they describe a typical organisation rather than "
                "all patients combined; the whiskers below show each organisation's Q1–median–Q3 "
                "in the same style, and beneath those each country's whisker on the same axis — "
                "estimated by combining that country's organisations' quartiles weighted by "
                "their counts, so an estimate rather than a recorded value."
            ])
        ]),
    ],
    prev_topic=('Plausibility', '/data-plausibility'),
    next_topic=('Availability', '/data-availability'),
    explanation=["These graphics show the overall data distributions through "
                 "the federated quartiles, and key variable characteristics such as "
                 "the biological sex balance and the grouped cancer types.",
                 html.Br(), html.Br(),
                 'Distributions and variable info are based on the "Descriptive statistics" Vantage6 '
                 'algorithm ',
                 html.Br(),
                 '(see https://github.com/STRONGAYA/v6-descriptive-statistics)']
)
