"""
Shared page chrome (header and footer) for the data management portal.

The markup mirrors the STRONG-AYA info portal
(https://github.com/STRONGAYA/strong-aya-info-portal, web/index.html), with
the purple notice banner adjusted for this portal: it is for internal use
only. Accessibility controls and the translation notice of the info portal
are intentionally not included.
"""

import os

from dash import html

from federated_data_management_portal import portal_version

_ASSET = f'..{os.path.sep}assets{os.path.sep}info-portal{os.path.sep}'

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

# The info portal appends this icon to every external link, plus a
# screen-reader-only note that the link opens in a new tab
_EXTERNAL_ICON = html.I(className='fas fa-arrow-up-right-from-square', **{'aria-hidden': 'true'})
_NEW_TAB_NOTE = html.Span(' (opens in a new tab)', className='visually-hidden')


def _external_children(children):
    """Append the external-link icon and the new-tab note to link children."""
    return [*children, _EXTERNAL_ICON, _NEW_TAB_NOTE]


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
                html.Span(f'Version {portal_version()}', className='version-note'),
            ]),
        ]),
    ])
