import argparse
import pathlib
import typing

import numpy
import numpy.typing

from eprempy import eprem
from eprempy import paths
from eprempy import physical


def main(
    n: int,
    physics: str,
    datadir: typing.Union[str, pathlib.Path]=None,
    time_step: int=0,
    shell: int=0,
    energy: float=0.0,
    writepath: typing.Union[str, pathlib.Path]=None,
    verbose: bool=False,
) -> None:
    """Plot histories of an identified node."""
    stream = eprem.stream(n, source=datadir)
    readdir = paths.fullpath(datadir or '.')
    if writepath is None:
        writepath = (readdir / __file__).with_suffix('.txt').name
    writepath = paths.fullpath(writepath)
    writepath.parent.mkdir(parents=True, exist_ok=True)
    write(
        physics,
        stream,
        writepath,
        s0=shell-time_step,
        species='H+',
        energy=(energy, 'MeV'),
        verbose=verbose,
    )


def write(
    physics: str,
    stream: eprem.Stream,
    path: pathlib.Path,
    t0: int=0,
    s0: int=0,
    verbose: bool=False,
    **indices
) -> numpy.typing.NDArray:
    """Compute a node history and write to file."""
    observable = stream[physics]
    times = stream.times.withunit('day')
    idx = tuple(indices[d] for d in observable.dimensions)
    observation = observable[idx]
    if verbose:
        print(f"Computing history of {physics} ...")
    history = compute(times, observation, t0=t0, s0=s0)
    header = build_header(physics, observation)
    text = '\n'.join(f'{str(t)} {str(v)}' for t, v in zip(times, history))
    if verbose:
        print(f"Writing history to {path} ...")
    path.write_text(f"{header}{text}")
    if verbose:
        print()


def compute(
    times: physical.Coordinates,
    observation: physical.Array,
    t0: int=0,
    s0: int=0,
) -> numpy.typing.NDArray:
    """Compute a physical quantity on a node as a function of time."""
    ntimes = len(times)
    array = numpy.array(observation)
    times_and_shells = zip(range(t0, t0+ntimes), range(s0, s0+ntimes))
    return numpy.squeeze([array[t, s, ...] for t, s in times_and_shells])


def build_header(physics: str, observation: physical.Array) -> str:
    """Build a header from observation metadata."""
    text = '#'
    text += f' data name: {physics};'
    text += f' time unit: days;'
    text += f' data unit: {observation.unit};'
    if 'species' in observation.dimensions:
        text += f' species: {observation["species"]};'
    if 'energy' in observation.dimensions:
        text += f' energy: {observation["energy"]["MeV"]}'
    text += '\n'
    return text


if __name__ == '__main__':
    p = argparse.ArgumentParser(
        description=main.__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        'n',
        help="The stream number",
        type=int,
    )
    p.add_argument(
        'physics',
        help="the physical quantity to compute on the target node",
    )
    p.add_argument(
        '-d',
        '--datadir',
        help="the directory containing the EPREM output (default: ./)",
    )
    p.add_argument(
        '-t',
        '--time_step',
        help="the time step (0-based) at which to identify the target node",
        type=int,
        default=0,
    )
    p.add_argument(
        '-s',
        '--shell',
        help="the shell (0-based) on which to identify the target node",
        type=int,
        default=0,
    )
    p.add_argument(
        '-e',
        '--energy',
        help="the target energy (in MeV), if applicable",
        type=float,
        default=0.0,
    )
    p.add_argument(
        '-w',
        '--writepath',
        help="path to which to write the node history",
    )
    p.add_argument(
        '-v',
        '--verbose',
        help="print runtime information",
        action='store_true',
    )
    args = p.parse_args()
    main(**vars(args))
