import json
import os
from importlib.resources import path

import pytest

from tests import resources

manual_tests = pytest.mark.skipif(not bool(os.getenv("MANUAL_TESTS")), reason="requires env setup")


@pytest.fixture
def sample_report():
    with path(resources, "report.json") as p:
        report = str(p.resolve())

        with open(report) as f:
            input_report = json.load(f)
            return input_report
