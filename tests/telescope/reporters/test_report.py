import os

import pandas as pd
import pytest

from telescope.reporters.report import assemble, save_xlsx


def get_test_df():
    return pd.DataFrame(
        data=[
            ["y", 0],
            [
                "x",
                2,
            ],
        ],
        columns=["a", "b"],
    )


@pytest.mark.skip(reason="manual integration test")
def test_save():
    df = get_test_df()
    save_xlsx("out.xlsv", MySheet1=df)
    assert os.path.exists("out.xlsx")


@pytest.mark.skip(reason="manual integration test")
def test_from_file_xlsx(sample_report):
    assemble(sample_report, "out.xlsx", "xlsx")


@pytest.mark.skip(reason="manual integration test")
def test_from_file_html(sample_report):
    assemble(sample_report, "out.html", "html")
