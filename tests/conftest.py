import json
import os
import pprint
from pathlib import Path
import pytest

manual_tests = pytest.mark.skipif(not bool(os.getenv("MANUAL_TESTS")), reason="requires env setup")


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).parent.parent


@pytest.fixture
def sample_report(project_root):
    with open(project_root / "tests/resources/report.json") as f:
        input_report = json.load(f)
        return input_report


@pytest.hookimpl(tryfirst=True)
def pytest_assertrepr_compare(config, op, left, right):
    if op in ("==", "!="):
        return [f"{pprint.pformat(left, width=999)} {op} {pprint.pformat(right, width=999)}"]
