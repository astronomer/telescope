import json
from importlib.resources import path

import pytest

from tests import resources


@pytest.fixture
def sample_report():
    with path(resources, "report.json") as p:
        report = str(p.resolve())

        with open(report) as f:
            input_report = json.load(f)
            return input_report
