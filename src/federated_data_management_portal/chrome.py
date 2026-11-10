"""
Shared page chrome (header and footer) for the data management portal.

The markup mirrors the STRONG-AYA info portal
(https://github.com/STRONGAYA/strong-aya-info-portal, web/index.html), with
the purple notice banner adjusted for this portal: it is for internal use
only. Accessibility controls and the translation notice of the info portal
are intentionally not included.
"""

import os

from dash import html, dcc

from federated_data_management_portal import portal_version

PAGE_TITLE = 'STRONG-AYA | Data Management Portal'
AESTHETIC_TITLE = 'Data management portal'
TILE_PLACEHOLDERS = ["0 countries", "0 institutions", "0 AYAs"]

_ASSET = f'..{os.path.sep}assets{os.path.sep}info-portal{os.path.sep}'
_ASSETS = f'..{os.path.sep}assets{os.path.sep}'
_ARROW_STYLE = {'width': '2.5rem', 'height': '2.5rem'}


def graph_config(filename, height=500, width=1100):
    """
    Standard dcc.Graph config: only the download button in the mode bar,
    exporting svg with the given filename.
    """
    return {
        'modeBarButtons': [['toImage']],
        'displayModeBar': True,
        'displaylogo': False,
        'toImageButtonOptions': {
            'format': 'svg',
            'filename': filename,
            'height': height,
            'width': width,
            'scale': 1,
        },
    }


def _arrow(direction):
    return html.Img(src=f'{_ASSETS}arrow-{direction}.svg',
                    alt=f'Arrowhead pointing {direction}',
                    style=_ARROW_STYLE)


def subject_tile(tile_id, title, image, alt, explanation, href):
    """
    A landing-page subject tile linking to a topic page.

    Parameters:
    tile_id (str): The tile's component id.
    title (str): The subject title shown on the tile.
    image (str): The image filename inside assets/.
    alt (str): The image alt text.
    explanation (str): The short description under the title.
    href (str): The topic page path.
    """
    return html.Div(id=tile_id, className='subject-tile', children=[
        dcc.Link(href=href, className='no-decoration-link', children=[
            html.Div(className='subject-title-container', children=[
                html.Div(className='subject-title', children=[title])
            ]),
            html.Div(className='subject-tile-content', children=[
                html.Img(src=f'{_ASSETS}{image}', alt=alt, className='subject-image'),
                html.Div(className='subject-explanation', children=[explanation]),
            ])
        ])
    ])


def page_scaffold(content, prev_topic=None, next_topic=None, explanation=None, show_return=True):
    """
    Standard page layout shared by all pages: info portal header, optional
    return-to-subjects button, dashboard title, the three stat tiles, the page
    content, optional previous/next topic navigation arrows, an optional
    explanation block, and the info portal footer.

    Parameters:
    content (list): The page-specific components.
    prev_topic (tuple, optional): (label, href) for the left navigation arrow.
    next_topic (tuple, optional): (label, href) for the right navigation arrow.
    explanation (list, optional): Children of the explanation block.
    show_return (bool): Whether to show the return-to-subjects button.

    Returns:
    The page layout as an html.Div.
    """
    body = []
    if show_return:
        body.append(html.Div(id='btn-return', className='btn-return', children=[
            _arrow('left'),
            dcc.Link('Return to subjects', href='/', className='no-decoration-link'),
        ]))
    body.append(html.H5(id='dashboard-title', className='dashboard-title', children=AESTHETIC_TITLE))
    body.append(html.Div(id='dashboard', className='dashboard', children=[
        html.Div(id=f'tile-{i}', className='tile-resizeable', children=[
            html.Div(id=f'tile-content-{i}', className='tile-content-resizeable',
                     children=TILE_PLACEHOLDERS[i - 1])
        ]) for i in (1, 2, 3)
    ]))
    body.append(html.Div(list(content)))
    if prev_topic:
        body.append(html.Div(id='btn-subject-a', className='btn-subject-a', children=[
            _arrow('left'),
            dcc.Link(prev_topic[0], href=prev_topic[1], className='no-decoration-link'),
        ]))
    if next_topic:
        body.append(html.Div(id='btn-subject-b', className='btn-subject-b', style={'margin-left': '73%'},
                             children=[
                                 dcc.Link(next_topic[0], href=next_topic[1], className='no-decoration-link'),
                                 _arrow('right'),
                             ]))
    if explanation is not None:
        body.append(html.Div(id='page-explanation', className='explanation', children=explanation))
    return html.Div([
        info_portal_header(),
        html.Div(body),
        info_portal_footer(),
    ])

# (label, href, font-awesome icon class or None) — icons as in the info portal
SITE_NAV = [
    ("Home", "https://strongaya.eu/", None),
    ("About us", "https://strongaya.eu/about-us/", "fas fa-chevron-down"),
    ("Our consortium", "https://strongaya.eu/our-consortium/", None),
    ("Ecosystems", "https://strongaya.eu/what-is-ecosystem/", "fas fa-chevron-down"),
    ("Resources", "https://strongaya.eu/publications/", "fas fa-chevron-down"),
    ("News & media", "https://strongaya.eu/news/", "fas fa-chevron-down"),
]

SOCIAL_LINKS = [
    ("fab fa-linkedin-in", "LinkedIn", "https://www.linkedin.com/company/strong-aya/"),
    ("fab fa-bluesky", "Bluesky", "https://bsky.app/profile/strongaya.eu"),
    ("fab fa-instagram", "Instagram", "https://www.instagram.com/strongaya_eu/"),
]

FOOTER_OTHER_LINKS = [
    ("Our consortium", "https://strongaya.eu/our-consortium/"),
    ("Ethics and governance", "https://strongaya.eu/ethics-and-governance/"),
    ("Ecosystems", "https://strongaya.eu/what-is-ecosystem/"),
    ("Project", "https://strongaya.eu/project/"),
]

FOOTER_LINKS = [
    ("How do the ecosystems work?", "https://strongaya.eu/what-is-ecosystem/"),
    ("Vision and objectives", "https://strongaya.eu/vision-and-objectives/"),
    ("Privacy declaration", "https://strongaya.eu/privacy-declaration/"),
    ("Cookie statement", "https://strongaya.eu/cookie-statement/"),
    ("Terms and conditions", "https://strongaya.eu/terms-and-conditions/"),
]


# External links open in a new tab
_EXTERNAL_PROPS = {'target': '_blank', 'rel': 'noopener noreferrer'}

# External links carry a screen-reader-only note that they open in a new tab
# (the info portal's header/footer links are plain text: no icon, no
# underline, inherited colour)
_NEW_TAB_NOTE = html.Span(' (opens in a new tab)', className='visually-hidden')


def _external_children(children):
    """Append the new-tab note to external link children."""
    return [*children, _NEW_TAB_NOTE]


def info_portal_header():
    """Build the info portal site header, with the internal-use notice banner."""
    return html.Header(className='site-header', children=[
        html.Div(className='header-topbar', children=[
            html.Div(className='topbar-social', children=[
                html.A(_external_children([html.I(className=icon), label]),
                       href=href, **{'aria-label': label}, **_EXTERNAL_PROPS)
                for icon, label, href in SOCIAL_LINKS
            ]),
            html.A([html.I(className='fas fa-envelope'), 'INFO@STRONGAYA.EU'],
                   href='mailto:info@strongaya.eu', className='topbar-mail'),
        ]),
        html.Div(className='header-main', children=[
            html.A(className='site-logo', href='https://strongaya.eu/', children=[
                html.Img(src=f'{_ASSET}weblogo1@2x.png', alt='STRONG-AYA'),
            ], **_EXTERNAL_PROPS),
            html.Nav(className='site-nav', children=[
                html.A(_external_children([label, html.I(className=icon)] if icon else [label]),
                       href=href, **_EXTERNAL_PROPS)
                for label, href, icon in SITE_NAV
            ]),
            html.A(_external_children(['Contact']), href='https://strongaya.eu/contact/',
                   className='contact-btn', **_EXTERNAL_PROPS),
        ]),
        html.Div(className='notice-banner', children=[
            html.B('Please note: this portal is for internal use only.'),
            html.Span(f'Version {portal_version()}', className='notice-version'),
            html.Div(id='authenticated-user-container', className='authenticated-user-container',
                     hidden=True, children=[
                html.Span(id='authenticated-user-email', className='authenticated-user-email',
                          **{'aria-label': 'Signed-in user email'}),
                html.Div(className='authenticated-user-actions', children=[
                    html.A('Sign out (switch account)', href='/oauth2/sign_out',
                           className='authenticated-user-action'),
                    html.A('Manage Microsoft permissions ↗', href='https://myapps.microsoft.com/',
                           target='_blank', rel='noopener noreferrer',
                           className='authenticated-user-action')
                ])
            ]),
        ]),
    ])


def info_portal_footer():
    """Build the info portal site footer, with the deployed portal version added."""
    return html.Footer(className='site-footer', children=[
        html.Div(className='footer-overlay', children=[
            html.Div(className='footer-content', children=[
                html.Div(className='footer-col footer-about', children=[
                    html.Img(src=f'{_ASSET}footerlogo@2x.png', alt='STRONG-AYA'),
                    html.P('STRONG-AYA is an interdisciplinary, multi-stakeholder European network to '
                           'improve healthcare services, research and outcomes for adolescents and young '
                           'adults (AYAs) with cancer.'),
                    html.P(className='research-disclaimer', children=[
                        html.B('Research Disclaimer'), html.Br(),
                        'This project is conducted for research purposes only. The content and outcomes '
                        'presented are part of ongoing EU-funded research and may be subject to scientific, '
                        'technical, and ethical limitations. Information on this website is not intended '
                        'for clinical use and should not be interpreted as medical advice.',
                    ]),
                ]),
                html.Div(className='footer-col', children=[
                    html.H2('Other'),
                    html.Ul(children=[html.Li(html.A(_external_children([label]), href=href, **_EXTERNAL_PROPS))
                                      for label, href in FOOTER_OTHER_LINKS]),
                ]),
                html.Div(className='footer-col', children=[
                    html.H2('Links'),
                    html.Ul(children=[html.Li(html.A(_external_children([label]), href=href, **_EXTERNAL_PROPS))
                                      for label, href in FOOTER_LINKS]),
                ]),
                html.Div(className='footer-col quick-contact', children=[
                    html.H2('Quick contact'),
                    html.Div('+31 020 512 9111'),
                    html.Div('INFO@STRONGAYA.EU'),
                    html.Div('Plesmanlaan 121, 1066 CX, AMSTERDAM'),
                ]),
            ]),
            html.Div(className='funding-statement', children=[
                html.P('STRONG AYA is funded by the European Union under grant agreement no 101057482. '
                       'Views and opinions expressed are however those of the author(s) only and do not '
                       'necessarily reflect those of the European Union or the Health and Digital Executive '
                       'Agency (HADEA). Neither the European Union nor the granting authority can be held '
                       'responsible for them.'),
                html.P('STRONG AYA is also funded by Innovate UK under grants 10038931, 10039273, 10041045, '
                       'and 10044189. Views and opinions expressed are however those of the author(s) only '
                       'and do not necessarily reflect those of UK Research and Innovation and Innovate UK. '
                       'Neither UKRI or the granting authority can be held responsible for them.'),
                html.Div(className='funding-logos', children=[
                    html.Img(src=f'{_ASSET}eu-logo-1.jpg', alt='Funded by the European Union'),
                    html.Img(src=f'{_ASSET}9f432dd7298f8cda-800x800ar@2x.png', alt='UKRI Innovate UK'),
                ]),
            ]),
            html.Div(className='copyright', children=[
                '© 2026 Strong Aya. All Rights Reserved.',
            ]),
        ]),
    ])
