import typing

from eprempy import eprem
from eprempy import quantity


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


def get_location(user: dict):
    """Get the shell or radius at which to plot."""
    shell = user.get('shell')
    if shell is not None: # allow value to be 0
        return shell
    if radius := user.get('radius'):
        return quantity.measure(float(radius[0]), radius[1]).withunit('au')
    return 0


def get_species(user: dict):
    """Get the ion species to plot."""
    species = user.get('species')
    if species is not None: # allow value to be 0
        return species
    return 0


UNITS = {
    'time': 'hour',
    'energy': 'MeV',
    'flux': '1 / (cm^2 s sr MeV/nuc)',
    'fluence': '1 / (cm^2 sr MeV/nuc)',
    'integral flux': '1 / (cm^2 s sr)',
}
"""Default units for observable quantities."""

