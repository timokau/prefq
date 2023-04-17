"""Basic tests"""

from prefq import __version__


def test_version():
    """Check that the import is working and the version is configured properly."""
    assert __version__ == "0.1.0"
