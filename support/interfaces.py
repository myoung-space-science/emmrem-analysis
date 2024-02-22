"""
Command-line support for EPREM analysis programs.
"""

import argparse
import typing


class ConvertStreamIDs(argparse.Action):
    """Convert string stream IDs to integers if necessary."""

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self._nargs = nargs
        super(
            ConvertStreamIDs,
            self,
        ).__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        target = []
        for value in values:
            try:
                target.append(int(value))
            except ValueError:
                target.append(value)
        setattr(namespace, self.dest, target)


class StoreKeyValuePair(argparse.Action):
    """Store key-value pairs from the CLI.
    
    This method adapts the following StackOverflow answer: 
    https://stackoverflow.com/a/42355279/4739101
    """

    def __init__(
        self,
        option_strings,
        dest,
        nargs=None,
        value_type=None,
        **kwargs
    ) -> None:
        self._nargs = nargs
        self._type = value_type
        super(
            StoreKeyValuePair,
            self,
        ).__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        _type = str if self._type is None else self._type
        values = split_key_value_pairs(values, dest_type=_type)
        setattr(namespace, self.dest, values)


def split_key_value_pairs(
    pairs: typing.Iterable[str],
    dest_type: type=None,
) -> dict:
    """Split ``'key=value'`` strings into ``{key: value}`` pairs."""
    target = {}
    for pair in pairs:
        k, v = pair.split("=")
        if dest_type is not None:
            v = dest_type(v)
        target[k] = v
    return target


