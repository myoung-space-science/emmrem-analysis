"""
Graphics utilities for EPREM analysis scripts.
"""

import typing


def parse_plot_kws(string: str) -> typing.Dict[str, typing.Any]:
    """Parse plot-related key-value pairs from CLI."""
    if not string:
        return {}
    pairs = string.split(',')
    result = {}
    for pair in pairs:
        i = pair.split('=')
        result[i[0].strip()] = i[1]
    return result

