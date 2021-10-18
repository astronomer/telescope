
def deep_clean(cleaning_keys: list, dirty_dict: dict):
    """
    >>> deep_clean([], {})
    >>> a = {"a": "1234"}; deep_clean(['a'], a); a
    {'a': '***'}
    >>> a = {"a": {"b": {"c": "1234", "d": "abcd"}}}; deep_clean(['a', 'b', 'c'], a); a
    {'a': {'b': {'c': '***', 'd': 'abcd'}}}
    """
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
