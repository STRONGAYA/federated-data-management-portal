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


def define_layout():
    """
    Defines the layout of the dashboard.

    Returns:
    layout (html.Div): The layout of the dashboard.
    """
    layout = html.Div([
        dcc.Store(id='store'),
        dcc.Store(id='data-availability-store-1'),
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
            html.Div(id='dashboard', className='dashboard', children=[
                html.H5(id='dashboard-title', className='dashboard-title', children=aesthetic_title),
                html.Div(id='tile-1', className='tile', children=[
                    html.Div(id='tile-content-1', className='tile-content', children=tile_placeholders[0])
                ]),
                html.Div(id='tile-2', className='tile', children=[
                    html.Div(id='tile-content-2', className='tile-content', children=tile_placeholders[1])
                ]),
                html.Div(id='tile-3', className='tile', children=[
                    html.Div(id='tile-content-3', className='tile-content', children=tile_placeholders[2])
                ])
            ]),
            html.Div([
                dbc.Row([
                    dbc.Col(
                        html.Div(id='tile-4', className='tile tile-4', children=[
                            dcc.Graph(
                                id={'type': 'dynamic-donut-one', 'index': 1},
                                config={
                                    'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d',
                                                               'zoomOut2d', 'autoScale2d', 'resetScale2d',
                                                               'hoverClosestCartesian', 'hoverCompareCartesian',
                                                               'toggleSpikelines'],
                                    'toImageButtonOptions': {
                                        'format': 'svg',
                                        'filename': 'proportions-per-organisation',
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
                                id={'type': 'dynamic-donut-two', 'index': 2},
                                config={
                                    'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d',
                                                               'zoomOut2d', 'autoScale2d', 'resetScale2d',
                                                               'hoverClosestCartesian', 'hoverCompareCartesian',
                                                               'toggleSpikelines'],
                                    'toImageButtonOptions': {
                                        'format': 'svg',
                                        'filename': 'proportions-per-country',
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
            html.Div(id='tile-6', className='tile tile-6', children=[
                html.H5('Data availability', className='tile-title'),
                html.Div(id='tile-content-6', className='tile-content')
            ]),

            html.Div(id='tile-7', className='tile tile-6', children=[
                html.H5('Data Completeness', className='tile-title'),
                html.Div(id='tile-content-7', className='tile-content', children=[
                    dcc.Graph(
                        id={'type': 'dynamic-bar', 'index': 3},
                        config={
                            'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d',
                                                       'zoomOut2d', 'autoScale2d', 'resetScale2d',
                                                       'hoverClosestCartesian', 'hoverCompareCartesian',
                                                       'toggleSpikelines'],
                            'toImageButtonOptions': {
                                'format': 'svg',
                                'filename': 'data-completeness',
                                'height': 500,
                                'width': 700,
                                'scale': 1
                            }
                        }
                    )
                ])
            ]),
        ]),
        html.Div(id='footer', className='footer')
    ])

    return layout, page_title
