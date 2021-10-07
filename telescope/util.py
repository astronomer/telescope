import json
import logging
from json import JSONDecodeError
from typing import Union, List, Dict

import yaml
from jsonschema import validate

from telescope.coordinator import HOSTS_JSON_SCHEMA


def get_json_or_clean_str(o: str) -> Union[List, Dict]:
    try:
        return json.loads(o)
    except (JSONDecodeError, TypeError) as e:
        logging.debug(e)
        logging.debug(o)
        return o.strip().split('\n')


def get_and_validate_hosts_input(hosts_file: str):
    with open(hosts_file) as hosts_f:
        schema = open(HOSTS_JSON_SCHEMA)
        hosts_by_type = yaml.safe_load(hosts_f)
        validate(hosts_by_type, schema=schema)  # will throw ValidationError
        return hosts_by_type