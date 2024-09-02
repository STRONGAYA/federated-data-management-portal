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

dash.register_page(__name__, path='/', title=page_title)

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
        html.Div(id='dashboard-content', className='dashboard',
                 children=[
                     html.H3(id='landing-title', className='landing-title', children='Explore the following subjects'),
                     html.Div(id='availability-tile', className='subject-tile',
                              children=[
                                  html.Div(className='tile-content',
                                           children=[
                                               html.Img(src=f'..{os.path.sep}assets{os.path.sep}scatter-basic.svg',
                                                        alt='A simple scatter plot',
                                                        style={'width': '5rem', 'height': '5rem'}
                                                        ),
                                               dcc.Link('Data availability', href='/data-availability',
                                                        className='no-decoration-link')
                                           ])
                              ]),
                     html.Div(id='missing-tile', className='subject-tile',
                              children=[
                                  html.Div(className='tile-content',
                                           children=[
                                               html.Img(src=f'..{os.path.sep}assets{os.path.sep}scatter-missing.svg',
                                                        alt='A simple scatter plot with highlighted missing data',
                                                        style={'width': '5rem', 'height': '5rem'}
                                                        ),
                                               dcc.Link('Data missingness', href='/data-missingness',
                                                        className='no-decoration-link')
                                           ])
                              ]),
                     html.Div(id='outlier-tile', className='subject-tile',
                              children=[
                                  html.Div(className='tile-content',
                                           children=[
                                               html.Img(src=f'..{os.path.sep}assets{os.path.sep}scatter-outlier.svg',
                                                        alt='A simple scatter plot with highlighted outlier',
                                                        style={'width': '5rem', 'height': '5rem'}
                                                        ),
                                               dcc.Link('Data outliers', href='/data-outliers',
                                                        className='no-decoration-link')
                                           ])
                              ]),

                 ])
    ]),
    html.Div(id='footer', className='footer')
])
