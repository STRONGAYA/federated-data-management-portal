import dash
import os
import dash_bootstrap_components as dbc
from dash import html, dcc

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

dash.register_page(__name__, path='/data-plausibility', title=page_title)

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
            html.H3(id='plausibility-title', className='page-title',
                    children='Data plausibility'),
            dbc.Row([
                dbc.Col(
                    html.Div(id='tile-4', className='tile tile-4', children=[
                        dcc.Graph(
                            id={'type': 'dynamic-donut-five', 'index': 1},
                            config={
                                'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d',
                                                           'zoomOut2d', 'autoScale2d', 'resetScale2d',
                                                           'hoverClosestCartesian', 'hoverCompareCartesian',
                                                           'toggleSpikelines'],
                                'toImageButtonOptions': {
                                    'format': 'svg',
                                    'filename': 'plausible-per-organisation',
                                    'height': 500,
                                    'width': 700,
                                    'scale': 1
                                }
                            }
                        )
                    ]),
                    width=6),
                dbc.Col(
                    html.Div(id='tile-5', className='tile tile-5', children=[
                        dcc.Graph(
                            id={'type': 'dynamic-donut-six', 'index': 2},
                            config={
                                'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d',
                                                           'zoomOut2d', 'autoScale2d', 'resetScale2d',
                                                           'hoverClosestCartesian', 'hoverCompareCartesian',
                                                           'toggleSpikelines'],
                                'toImageButtonOptions': {
                                    'format': 'svg',
                                    'filename': 'plausible-per-country',
                                    'height': 500,
                                    'width': 700,
                                    'scale': 1
                                }
                            }
                        )
                    ]),
                    width=6)
            ])
        ]),

        html.Div(id='tile-7', className='tile tile-6', children=[
            html.H5('Atemporal plausibility', className='tile-title'),
            html.Div(children=[
                "Select the organisation(s) you would like to visualise",
                dcc.Checklist(
                    id='subset-selection-checkboxes', className='subset-selection-checkboxes',
                    options=[],
                    value=[],
                    labelStyle={'display': 'inline-block'}
                )]),
            html.Div(id='tile-content-7', className='tile-content', children=[
                dcc.Graph(
                    id={'type': 'dynamic-plausibility-bar', 'index': 3},
                    config={
                        'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d',
                                                   'zoomOut2d', 'autoScale2d', 'resetScale2d',
                                                   'hoverClosestCartesian', 'hoverCompareCartesian',
                                                   'toggleSpikelines'],
                        'toImageButtonOptions': {
                            'format': 'svg',
                            'filename': 'variable-atemporal-plausibility',
                            'height': 500,
                            'width': 700,
                            'scale': 1
                        }
                    },
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
        html.Div(id='btn-subject-a', className='btn-subject-a', children=[
            html.Img(src=f'..{os.path.sep}assets{os.path.sep}arrow-left.svg',
                     alt='Arrowhead pointing left',
                     style={'width': '2.5rem',
                            'height': '2.5rem'}),
            dcc.Link('Completeness', href='/data-completeness',
                     className='no-decoration-link')
        ]),
        html.Div(id='btn-subject-b', className='btn-subject-b', style={'margin-left': '73%'}, children=[
            dcc.Link('Availability', href='/data-availability', className='no-decoration-link'),
            html.Img(src=f'..{os.path.sep}assets{os.path.sep}arrow-right.svg',
                     alt='Arrowhead pointing right',
                     style={'width': '2.5rem',
                            'height': '2.5rem'})
        ]),
        html.Div(id='availability-explanation', className='explanation',
                 children=['The shown graphics aim to portray the believability or truthfulness of data values '
                           'by assessing the acceptable variable value range and '
                           'distribution in both atemporal as temporal data fields.',
                           html.Br(), html.Br(),
                           'Data plausibility is based on the "Descriptive statistics" Vantage6 algorithm ',
                           html.Br(),
                           '(see https://github.com/STRONGAYA/v6-descriptive-statistics)'])
    ]),
    html.Div(id='footer', className='footer')
])
