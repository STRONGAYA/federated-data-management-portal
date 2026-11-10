import dash
import os

from dash import html, dcc, dash_table

from federated_data_management_portal import portal_version

page_title = 'STRONG-AYA | Data Management Portal'

aesthetic_logo_alt_text = 'STRONG-AYA Logo'
aesthetic_title = 'Data management portal'

secondary_headers = {
    "HOME": "https://strongaya.eu/",
    "ABOUT US": "https://strongaya.eu/about-us",
    "OUR CONSORTIUM": "https://strongaya.eu/our-consortium/",
    "ECOSYSTEMS": "https://strongaya.eu/what-is-ecosystem/",
    "NEWS": "https://strongaya.eu/news/",
    "CONTACT <white-text>": "https://strongaya.eu/contact/"
}

tile_placeholders = ["0 countries", "0 institutions", "0 AYAs"]

dash.register_page(__name__, path='/data-exploration', title=page_title)

layout = html.Div([
    html.Header([
        html.Div(className='primary-header'),
        html.Div(className='secondary-header', children=[
            html.Div(className='logo', children=[
                html.Img(src=f'..{os.path.sep}assets{os.path.sep}web-logo-1.png',
                         alt=aesthetic_logo_alt_text,
                         style={'width': '200px', 'height': '40px'}
                         )
            ]),
            html.Div(id='text-container', className='text-container', children=[
                *[html.A(className='text-field', children=text, href=link) for text, link in
                  secondary_headers.items() if '<white-text>' not in text],
                *[html.A(className='text-field white-text', children=text[:text.rfind('<white-text>')],
                         href=link) for
                  text, link in
                  secondary_headers.items() if '<white-text>' in text]
            ]),
            html.Div(className='orange-cube')
        ]),
    ]),
    html.Div([
        html.Div(id='btn-return', className='btn-return', children=[
            html.Img(src=f'..{os.path.sep}assets{os.path.sep}arrow-left.svg',
                     alt='Arrowhead pointing left',
                     style={'width': '2.5rem',
                            'height': '2.5rem'}),
            dcc.Link('Return to subjects', href='/', className='no-decoration-link')
        ]),
        html.H5(id='dashboard-title', className='dashboard-title', children=aesthetic_title),
        html.Div(id='dashboard', className='dashboard', children=[
            html.Div(id='tile-1', className='tile-resizeable', children=[
                html.Div(id='tile-content-1', className='tile-content-resizeable', children=tile_placeholders[0])
            ]),
            html.Div(id='tile-2', className='tile-resizeable', children=[
                html.Div(id='tile-content-2', className='tile-content-resizeable', children=tile_placeholders[1])
            ]),
            html.Div(id='tile-3', className='tile-resizeable', children=[
                html.Div(id='tile-content-3', className='tile-content-resizeable', children=tile_placeholders[2])
            ])
        ]),
        html.Div([
            html.H3(id='exploration-title', className='page-title', children='Data exploration'),
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
                    config={'modeBarButtons': [['toImage']],
                        'displayModeBar': True,
                        'displaylogo': False,
                        'toImageButtonOptions': {
                            'format': 'svg',
                            'filename': 'categorical-variable-counts',
                            'height': 500,
                            'width': 1100,
                            'scale': 1
                        }
                    }
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
                        config={'modeBarButtons': [['toImage']],
                            'displayModeBar': True,
                            'displaylogo': False,
                            'toImageButtonOptions': {
                                'format': 'svg',
                                'filename': 'federated-distribution',
                                'height': 500,
                                'width': 1100,
                                'scale': 1
                            }
                        }
                    )
                ]),
                html.Div(id='exploration-distribution-stats', className='explanation', children=[]),
                html.Div(id='exploration-distribution-disclaimer', className='explanation', children=[
                    "The curve is an approximation reconstructed from the federated quartiles "
                    "(q1, median, q3) and IQR; min/max and raw values are not part of the central "
                    "aggregate result."
                ])
            ]),
            html.Div(id='btn-subject-a', className='btn-subject-a', children=[
                html.Img(src=f'..{os.path.sep}assets{os.path.sep}arrow-left.svg',
                         alt='Arrowhead pointing left',
                         style={'width': '2.5rem',
                                'height': '2.5rem'}),
                dcc.Link('Plausibility', href='/data-plausibility',
                         className='no-decoration-link')
            ]),
            html.Div(id='btn-subject-b', className='btn-subject-b', style={'margin-left': '73%'}, children=[
                dcc.Link('Availability', href='/data-availability', className='no-decoration-link'),
                html.Img(src=f'..{os.path.sep}assets{os.path.sep}arrow-right.svg',
                         alt='Arrowhead pointing right',
                         style={'width': '2.5rem',
                                'height': '2.5rem'})
            ]),
        ]),
        html.Div(id='exploration-explanation', className='explanation',
                 children=["Graphics aim to visualise the aggregate data distributions as density curves "
                           "reconstructed from the federated quartiles and IQR, and key variable "
                           "characteristics such as the biological sex balance and the grouped cancer types.",
                           html.Br(), html.Br(),
                           'Distributions and variable info are based on the "Descriptive statistics" Vantage6 '
                           'algorithm ',
                           html.Br(),
                           '(see https://github.com/STRONGAYA/v6-descriptive-statistics)'])
    ]),
    html.Div(id='footer', className='footer',
         children=[html.Div(f'Version {portal_version()}', className='version-note')])
])
