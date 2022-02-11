import pytest

from telescope.util import clean_airflow_report_output, deep_clean, get_json_or_clean_str


def test_deep_clean_empty():
    a = {}
    deep_clean([], a)
    actual = a
    expected = {}
    assert actual == expected, "when given nothing, we give back nothing without error"


def test_deep_clean_simple():
    a = {"a": "1234"}
    deep_clean(["a"], a)
    actual = a
    expected = {"a": "***"}
    assert actual == expected, "we can clean nested keys with strings"


def test_deep_clean_nested():
    a = {"a": {"b": {"c": "1234", "d": "abcd"}}}
    deep_clean(["a", "b", "c"], a)
    actual = a
    expected = {"a": {"b": {"c": "***", "d": "abcd"}}}
    assert actual == expected, "we can clean nested keys with strings"


@pytest.mark.parametrize(
    "in_str,expected",
    [
        ("", [""]),
        ("a\nb\nc", ["a", "b", "c"]),
        (
            "INFO 123 - xyz - abc\n\n\nERROR - 1234\n2019-02-17 12:40:14,798 : CRITICAL : __main__ : Fatal error. Cannot continue\n%%%%%%%\ne30=",
            "{}",
        ),
        (
            "INFO 123 - xyz - abc\n\n\nERROR - 1234\n2019-02-17 12:40:14,798 : CRITICAL : __main__ : Fatal error. Cannot continue",
            [
                "INFO 123 - xyz - abc",
                "",
                "",
                "ERROR - 1234",
                "2019-02-17 12:40:14,798 : CRITICAL : __main__ : Fatal error. Cannot continue",
            ],
        ),
    ],
)
def test_clean_airflow_report_output(in_str, expected):
    actual = clean_airflow_report_output(in_str)
    assert actual == expected, "We can remove multiple log lines prepending a JSON output"


@pytest.mark.parametrize(
    "in_str,expected",
    [("", [""]), ("{}", {}), ('{"a":"b"}', {"a": "b"}), ('asdfsadf\n{"a": "b"}', ["asdfsadf", '{"a": "b"}'])],
)
def test_get_json_or_clean_str(in_str, expected):
    assert get_json_or_clean_str(in_str) == expected
