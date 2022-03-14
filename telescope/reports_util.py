from typing import Dict, List, Optional, Union

import logging
from collections.abc import MutableMapping
from functools import partial, reduce

log = logging.getLogger(__name__)


def parse_non_default_configurations(config_report: dict) -> Union[Dict[str, str], MutableMapping]:
    def flatten_dict(d: MutableMapping, parent_key: str = "", sep: str = ".") -> MutableMapping:
        items = []
        for k, v in d.items():
            new_key = parent_key + sep + k if parent_key else k
            if isinstance(v, MutableMapping):
                items.extend(flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    new = {k: {ik: iv for ik, iv in v.items() if iv[1] != "default"} for k, v in config_report.items()}
    filtered = {k: v for k, v in new.items() if len(v)}
    return flatten_dict(filtered)


def parse_non_default_configurations_as_str(config_report: dict) -> str:
    return ", ".join([f"{k}: {v[0]}" for k, v in parse_non_default_configurations(config_report).items()])


def parse_replicas_from_helm(deployment_name: str, component: str, helm_report: dict) -> int:
    for k in helm_report:
        if (
            k.get("namespace") in deployment_name
            and k.get("name") in deployment_name
            and k.get("name") + k.get("namespace") != "astronomerastronomer"
        ):
            return k.get("values", {}).get(component, {}).get("replicas", 1)
    return -1


def parse_chart_version_from_helm(deployment_name: str, helm_report: dict) -> str:
    for k in helm_report:
        if (
            k.get("namespace") in deployment_name
            and k.get("name") in deployment_name
            and k.get("name") + k.get("namespace") != "astronomerastronomer"
        ):
            return k.get("chart", {})
    return ""


def parse_updated_at_from_helm(deployment_name: str, helm_report: dict) -> str:
    for k in helm_report:
        if (
            k.get("namespace") in deployment_name
            and k.get("name") in deployment_name
            and k.get("name") + k.get("namespace") != "astronomerastronomer"
        ):
            return k.get("updated", "")
    return ""


def parse_workspace_id_from_helm(deployment_name: str, helm_report: dict, default: str) -> str:
    for k in helm_report:
        if (
            k.get("namespace") in deployment_name
            and k.get("name") in deployment_name
            and k.get("name") + k.get("namespace") != "astronomerastronomer"
        ):
            return k.get("values", {}).get("labels", {}).get("workspace", default)
    return default


def parse_deployment_id_from_helm(deployment_name: str, helm_report: dict, default: str) -> str:
    for k in helm_report:
        if (
            k.get("namespace") in deployment_name
            and k.get("name") in deployment_name
            and k.get("name") + k.get("namespace") != "astronomerastronomer"
        ):
            return k.get("name", default)
    return default


# noinspection PyBroadException,TryExceptPass
def sum_usage_stats_report_summary(usage_stats_report: Optional[List[Dict[str, int]]]) -> Dict[str, int]:
    """reduce the usage stats split out by dag, and reduce, and calc % of failures"""
    sum_report = {}

    def accumulate(key, accumulator, next_val):
        return accumulator + next_val.get(key, 0)

    # Take all the keys from the first record -
    # keys = ['1_days_success', '1_days_failed', '7_days_success', '7_days_failed', '30_days_success',
    #           '30_days_failed', '365_days_success', '365_days_failed', 'all_days_success', 'all_days_failed']
    # Reduce them all down to a sum value, then further summarize to successes and percents
    if type(usage_stats_report) == list and len(usage_stats_report):
        reduced = {
            key: reduce(partial(accumulate, key), usage_stats_report, 0)
            for key in usage_stats_report[0].keys()
            if key != "dag_id"
        }
        for key, value in reduced.items():
            if "_failed" in key:
                key_success = key.replace("_failed", "_success")
                key_pct = key.replace("_failed", "_failed_pct")
                try:
                    value_all = reduced.get(key_success, 1) + value
                    if value_all != 0:
                        value_pct = int(value / value_all * 100)  # failed / success
                        sum_report[key_pct] = value_pct
                    else:
                        sum_report[key_pct] = 0
                except Exception:
                    sum_report[key_pct] = -1
            else:
                sum_report[key] = value
    return sum_report


def dag_is_active(dag: dict) -> bool:
    return dag.get("is_active", False) and not dag.get("is_paused", False)
