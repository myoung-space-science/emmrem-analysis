import argparse
import pathlib
import typing

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import numpy

from eprempy import eprem
from eprempy.paths import fullpath


def main(
    num: int=0,
    config: str=None,
    indir: str=None,
    runs: typing.Iterable[str]=None,
    outdir: str=None,
    verbose: bool=False,
) -> None:
    """Plot flux versus energy at predefined shells."""
    paths = build_paths(indir, runs)
    npaths = len(paths)
    fig, axs = plt.subplots(
        nrows=1,
        ncols=npaths,
        sharex=True,
        sharey=True,
        figsize=(2 + 4*npaths, 4),
    )
    for ax, path in zip(axs, paths):
        add_panel(ax, num, config=config, source=path)
    axs[0].legend()
    fig.tight_layout()
    plotdir = outdir or pathlib.Path.cwd()
    plotpath = plotdir / 'flux-energy.png'
    if verbose:
        print(f"Saved {plotpath}")
    plt.savefig(plotpath)
    plt.close()


def build_paths(
    indir: str=None,
    runs: typing.Union[str, typing.Iterable[str]]=None,
) -> typing.Tuple[pathlib.Path]:
    """Convert user input into full paths."""
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
        if path.is_dir():
            return tuple(path.glob('*'))
        return (path,)
    if len(runs) == 1:
        return tuple(path / run for run in path.glob(runs[0]))
    return tuple(path / run for run in runs)


def add_panel(
    ax: Axes,
    num: int=0,
    config: str=None,
    source: str=None,
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
    time = 1.0, 'day'
    r = float(radius[time, 0].squeezed)
    ax.plot(
        energy[:].squeezed,
        flux[time, 0, 'H+', :].squeezed,
        'k:',
        label=f"r = {r:4.2f} au",
    )
    radii = numpy.linspace(0.5, 3.5, 7)
    for r in radii:
        ax.plot(
            energy[:].squeezed,
            flux[time, (r, 'au'), 'H+', :].squeezed,
            label=f"r = {r:4.2f} au",
        )
    ax.set_xlabel("Energy [MeV]")
    ax.set_ylabel(r"Flux [1 / (cm$^2$ s sr MeV)]")
    ax.set_xlim(1e-1, 1e1)
    ax.set_ylim(1e-2, 1e6)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_title(str(stream.dataset.source.parent.name))
    ax.label_outer()


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
        '-v',
        '--verbose',
        help="print runtime messages",
        action='store_true',
    )
    args = p.parse_args()
    main(**vars(args))
