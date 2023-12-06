import argparse
import pathlib
import typing

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from eprempy import eprem
from eprempy import quantity
from eprempy.paths import fullpath


def main(
    num: int=0,
    config: str=None,
    indir: str=None,
    runs: typing.Iterable[str]=None,
    outdir: str=None,
    verbose: bool=False,
    **user
) -> None:
    """Plot flux versus energy at predefined shells."""
    paths = build_paths(indir, runs)
    npaths = len(paths)
    fig, axs = plt.subplots(
        nrows=1,
        ncols=npaths,
        sharex=True,
        sharey=True,
        squeeze=False,
        figsize=(2 + 4*npaths, 4),
    )
    flataxs = tuple(axs.flat)
    for ax, path in zip(flataxs, paths):
        add_panel(ax, num, config=config, source=path, **user)
    flataxs[0].legend()
    fig.tight_layout()
    plotdir = fullpath(outdir or '.')
    plotpath = plotdir / 'flux-energy.png'
    if verbose:
        print(f"Saved {plotpath}")
    plt.savefig(plotpath)
    plt.close()


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
        raise ValueError(
            "Not enough information to build paths"
        ) from None
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


def add_panel(
    ax: Axes,
    num: int=0,
    config: str=None,
    source: str=None,
    **user
) -> None:
    """Add a single plot panel to the figure."""
    stream = eprem.stream(
        num,
        config=(config or 'eprem.cfg'),
        source=source,
    )
    radius = stream['radius'].withunit('au')
    energy = stream['energy'].withunit('MeV')
    flux = stream['flux'].withunit('1 / (cm^2 s sr MeV)')
    time = get_time(user)
    r0 = float(radius[time, 0].squeezed)
    ax.plot(
        energy[:].squeezed,
        flux[time, 0, 'H+', :].squeezed,
        'k:',
        label=f"r = {r0:4.2f} au",
    )
    radii = get_radius(user)
    for r in radii:
        ax.plot(
            energy[:].squeezed,
            flux[time, r, 'H+', :].squeezed,
            label=f"r = {float(r):4.2f} au",
        )
    ax.set_prop_cycle(None)
    shells = get_shell(user)
    for s in shells:
        ax.plot(
            energy[:].squeezed,
            flux[time, s, 'H+', :].squeezed,
            label=f"shell = {s}",
            linestyle='none',
            marker='o',
        )
    ax.set_xlabel("Energy [MeV]")
    ax.set_ylabel(r"Flux [1 / (cm$^2$ s sr MeV)]")
    ax.set_xlim(1e-1, 1e1)
    ax.set_ylim(1e-2, 1e6)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_title(str(stream.dataset.source.parent.name))
    ax.label_outer()


# NOTE: These functions allow for the possibility that `user` contains `None`
# for a given coordinate or its unit, and treat each case as if `user` did not
# contain the corresponding key(s) at all. This is necessary since the CLI will
# populate `user` with explicit null values for missing parameters.

def get_time(user: dict):
    """Get an appropriate time index from user input."""
    time = user.get('time')
    if time is None:
        return 0
    if len(time) == 1:
        return int(time[0])
    if len(time) == 2:
        return float(time[0]), time[1]
    raise ValueError(time)


def get_shell(user: dict):
    """Get appropriate shell indices from user input."""
    shell = user.get('shell')
    if shell is None:
        return ()
    return tuple(shell)


def get_radius(user: dict):
    """Get appropriate radial indices from user input."""
    radius = user.get('radius')
    if radius is None:
        return ()
    if len(radius) == 1:
        return quantity.measure(radius[0], 'au')
    try:
        float(radius[-1])
    except ValueError:
        unit = radius[-1]
        values = [float(r) for r in radius[:-1]]
        return quantity.measure(*values, unit).withunit('au')
    return quantity.measure(radius, 'au')


if __name__ == '__main__':
    p = argparse.ArgumentParser(
        description=main.__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        '-n',
        '--stream',
        dest='num',
        help="which stream to show",
        type=int,
        default=0,
    )
    p.add_argument(
        '-c',
        '--config',
        help="name of simulation configuration file (default: eprem.cfg)",
    )
    p.add_argument(
        '-i',
        '--input',
        dest='indir',
        help="directory containing simulation data (default: current)",
    )
    p.add_argument(
        '-r',
        '--runs',
        help="names of directories (may be relative to INDIR)",
        nargs='*',
    )
    p.add_argument(
        '-o',
        '--output',
        dest='outdir',
        help="output directory (default: input directory)",
    )
    p.add_argument(
        '--time',
        help=(
            "time at which to plot flux (default: initial time step)"
            ";\nmay consist of a single integer or a value-unit pair"
        ),
        nargs='+',
        metavar=('TIME', 'UNIT'),
    )
    p.add_argument(
        '--shell',
        help="shell(s) at which to plot flux (default: 0)",
        type=int,
        nargs='+',
        metavar=('S0', 'S1'),
    )
    p.add_argument(
        '--radius',
        help="radius(-ii) at which to plot flux (default: inner boundary)",
        nargs='+',
        metavar=('R0 [R1 ...]', 'UNIT'),
    )
    p.add_argument(
        '-v',
        '--verbose',
        help="print runtime messages",
        action='store_true',
    )
    args = p.parse_args()
    main(**vars(args))
