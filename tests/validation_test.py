import pytest


@pytest.fixture
def local_version(project_root, *args):
    from astronomer_telescope import __version__

    return __version__


def test_version(local_version):
    import requests

    package = "astronomer-starship"

    releases = requests.get(f"https://pypi.org/pypi/{package}/json").json()["releases"]
    shipped_versions = []
    [shipped_versions.append(version) for version, details in releases.items()]

    assert local_version not in shipped_versions
