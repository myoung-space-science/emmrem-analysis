"""
Command-line support for EPREM analysis programs.
"""

import argparse
import pathlib
import typing

from eprempy.paths import fullpath


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


def build_paths(
    indir: str=None,
    runs: typing.Union[str, typing.Iterable[str]]=None,
) -> typing.Tuple[pathlib.Path]:
    """Convert user input into full paths.

    Parameters
    ----------
    indir : string, optional
        The path to a single simulation directory or the parent path of multiple
        simulation directories.
    runs : string or iterable of strings, optional
        The name of a simulation run or a globbing pattern representing multiple
        simulation runs.
    """
    if runs is None and indir is None:
        return (pathlib.Path.cwd(),)
    if indir is None:
        if isinstance(runs, str):
            return (fullpath(run) for run in pathlib.Path.cwd().glob(runs))
        return tuple(fullpath(run) for run in runs)
    path = fullpath(indir)
    if runs is None:
        contents = tuple(path.glob('*'))
        if path.is_dir() and all(p.is_dir() for p in contents):
            return contents
        return (path,)
    if len(runs) == 1:
        return tuple(path / run for run in path.glob(runs[0]))
    return tuple(path / run for run in runs)


