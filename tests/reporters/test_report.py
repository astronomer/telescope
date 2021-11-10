import os

import pandas as pd
import pytest

from telescope.reporters.report import save_xlsx


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


@pytest.mark.skip(reason="integration test")
def test_save():
    df = get_test_df()
    save_xlsx("out.xlsv", MySheet1=df)
    assert os.path.exists("out.xlsv")
