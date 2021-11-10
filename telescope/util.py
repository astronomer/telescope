import json
import logging
from json import JSONDecodeError
from typing import Union, List, Dict, Any

log = logging.getLogger(__name__)


def get_json_or_clean_str(o: str) -> Union[List[Any], Dict[Any, Any], Any]:
    try:
        return json.loads(o)
    except (JSONDecodeError, TypeError) as e:
        log.debug(e)
        log.debug(o)
        return o.strip().split('\n')


def deep_clean(cleaning_keys: List[Any], dirty_dict: Dict[Any, Any]) -> None:
    """Look for keys recursively within a dictionary, change the values to '***' """
    if not len(cleaning_keys) or not len(dirty_dict):
        return

    if len(cleaning_keys) > 1:
        [cleaning_key, *cleaning_keys] = cleaning_keys
        if cleaning_key in dirty_dict:
            deep_clean(cleaning_keys, dirty_dict[cleaning_key])
        else:
            return
    else:
        [cleaning_key] = cleaning_keys
        if cleaning_key in dirty_dict:
            dirty_dict[cleaning_key] = "***"
        else:
            return


def remove_initial_log_lines(log_string: str) -> str:
    log_lines = log_string.split("\n")
    enumerated_log_lines = list(enumerate(log_lines))
    found_i = -1
    for i, line in enumerated_log_lines:
        if '{' in line:
            found_i = i
            break
    if found_i != -1:
        return "\n".join(log_lines[found_i:])
    else:
        return log_string
