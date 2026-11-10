import dash

from dash import html

from federated_data_management_portal import chrome

dash.register_page(__name__, path='/', title=chrome.PAGE_TITLE)

layout = chrome.page_scaffold(
    content=[
        html.H3(id='landing-title', className='page-title', children='Explore the following subjects'),
        chrome.subject_tile(
            'availability-tile', 'Availability and Semantic Consistency', 'scatter-basic.svg',
            'A simple scatter plot',
            "Investigate how much data is available per location and "
            "explore the existence of expected and "
            "possible values between variables with "
            "semantic relationships between them.",
            '/data-availability'),
        chrome.subject_tile(
            'completeness-tile', 'Completeness', 'scatter-missing.svg',
            'A simple scatter plot with highlighted missing data point',
            "Assess the absence of data at a single moment over time or "
            "when measured at multiple moments over time, "
            "without reference to its structure or plausibility",
            '/data-completeness'),
        chrome.subject_tile(
            'plausibility-tile', 'Plausibility', 'scatter-outlier.svg',
            'A simple scatter plot with highlighted outlier',
            "Explore the believability or truthfulness of data values "
            "by assessing the acceptable variable value range and "
            "distribution in both atemporal as temporal data fields.",
            '/data-plausibility'),
        chrome.subject_tile(
            'exploration-tile', 'Data exploration', 'scatter-basic.svg',
            'A simple scatter plot',
            "Explore the aggregate data distributions via the federated "
            "quartiles and IQR, and key variable characteristics such as "
            "the biological sex balance and the grouped cancer types.",
            '/data-exploration'),
    ],
    show_return=False,
)
