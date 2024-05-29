"""
Command-line support for EPREM analysis programs.
"""

import argparse
import pathlib
import textwrap
import typing

from eprempy import eprem
from eprempy import quantity
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



def get_streams(
    source: typing.Optional[str]=None,
    config: typing.Optional[str]=None,
    num: typing.Optional[int]=None,
) -> typing.List[eprem.Stream]:
    """Get all relevant stream observers."""
    dataset = eprem.dataset(source=source, config=config)
    streams = dataset.streams
    if isinstance(num, int):
        return [streams[num]]
    return list(streams.values())


def get_times(user: dict):
    """Get appropriate times or steps from user input."""
    return compute_indexer(user.get('time'))


def get_location(user: dict):
    """Get the shell or radius at which to plot."""
    locations = get_locations(user)
    return locations[0]


def get_locations(user: dict):
    """Get appropriate radii or shells from user input."""
    return compute_indexer(user.get('location'))


def compute_indexer(args: typing.Union[typing.Sequence, None]):
    """Get appropriate indices or values from user input."""
    if args is None:
        return (0,)
    if len(args) == 1:
        return (int(args[0]),)
    try:
        indices = [int(arg) for arg in args]
    except ValueError:
        unit = args[-1]
        values = [float(arg) for arg in args[:-1]]
        return quantity.measure(*values, unit)
    return tuple(indices)


def get_species(user: dict):
    """Get the ion species to plot."""
    species = user.get('species')
    if species is not None: # allow value to be 0
        return species
    return 0


def get_units(user: dict):
    """Get appropriate metric units."""
    return {k: user.get(f'{k}_unit') or u for k, u in UNITS.items()}


UNITS = {
    'time': 'hour',
    'energy': 'MeV',
    'flux': '1 / (cm^2 s sr MeV/nuc)',
    'fluence': '1 / (cm^2 sr MeV/nuc)',
    'integral flux': '1 / (cm^2 s sr)',
}
"""Default units for observable quantities."""


class Parser(argparse.ArgumentParser):
    """An argument parser with custom file-line parsing."""

    def __init__(
        self,
        *args,
        wrap: int=0,
        ignore_missing_file: bool=False,
        **kwargs,
    ) -> None:
        """
        Parameters
        ----------
        *args
            Any positional arguments accepted by `argparse.ArgumentParser`.

        wrap : int, default=0
            The column at which to wrap lines of text. Setting `wrap` <= 0
            suppresses line wrapping.

        ignore_missing_file : bool, default=false
            If true, this will silently ignore a missing file name associated
            with the `fromfile_prefix_char` option. For example, this allows
            users to set the default name of a config file to "" in scripts. If
            false (the default), passing an empty file name will cause an error.

        **kwargs
            Any keyword arguments accepted by `argparse.ArgumentParser`.
        """
        self.wrap = max(wrap, 0)
        self.ignore_missing_file = ignore_missing_file
        kwargs['epilog'] = self._update_text(kwargs['epilog'])
        super().__init__(*args, **kwargs)

    def add_argument(self, *args, **kwargs):
        kwargs['help'] = self._update_text(kwargs['help'])
        return super().add_argument(*args, **kwargs)

    def _update_text(self, text: str) -> str:
        """Update a string of text based on state attributes."""
        if self.wrap:
            wrapped = textwrap.wrap(text, width=self.wrap)
            return '\n'.join(wrapped)
        return text

    def _read_args_from_files(
        self,
        arg_strings: typing.List[str],
    ) -> typing.List[str]:
        """Expand arguments referencing files.

        This overloads the argparse.ArgumentParser method to support the
        `ignore_missing_file` option (cf. `__init__`).
        """
        if self._removable_file(arg_strings):
            arg_strings = [
                s for s in arg_strings
                if s != self.fromfile_prefix_chars
            ]
        return super()._read_args_from_files(arg_strings)

    def _removable_file(self, arg_strings):
        return (
            self.fromfile_prefix_chars in arg_strings
            and self.ignore_missing_file
        )

    def convert_arg_line_to_args(self, arg_line: str):
        return arg_line.split()


