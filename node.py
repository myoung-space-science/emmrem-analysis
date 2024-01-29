import pathlib
import typing

import numpy
import numpy.typing

from eprempy import paths


def parse_history(
    path: typing.Union[str, pathlib.Path]
) -> typing.Dict[str, typing.Union[numpy.typing.NDArray, dict]]:
    """Parse a text file containing a node history."""
    filepath = paths.fullpath(path)
    with filepath.open('r') as fp:
        header = fp.readline()
        time, data = numpy.loadtxt(fp, unpack=True)
    info = header.lstrip('#').rstrip('\n').split(';')
    result = {'time': time, 'data': data, 'info': {}}
    for entry in info:
        if entry:
            k, v = entry.split(':')
            result['info'][k.strip()] = v.strip()
    return result

