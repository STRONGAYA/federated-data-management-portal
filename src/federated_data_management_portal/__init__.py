"""Package marker for the federated data management portal distribution."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version


def portal_version():
    """
    Return the version of the deployed portal.

    Reads the version from the installed distribution, so the version shown in
    the dashboard footer always matches the version that was built and deployed.

    Returns:
    str: The distribution version, or 'unknown' when the package metadata is
    not available (for example when the sources are run without installation).
    """
    try:
        return _package_version('federated-data-management-portal')
    except PackageNotFoundError:
        return 'unknown'
