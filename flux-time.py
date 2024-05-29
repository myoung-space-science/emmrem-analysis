import argparse
import math
import typing

import numpy
import matplotlib as mpl
import matplotlib.pyplot as plt

from eprempy import eprem
from eprempy.paths import fullpath
from eprempy import quantity
from support import interfaces
from support import plots


def main(
    num: typing.Optional[int]=None,
    source: typing.Optional[str]=None,
    config: typing.Optional[str]=None,
    outdir: typing.Optional[str]=None,
    verbose: bool=False,
    **user
) -> None:
    """Create survey plots for one or more stream observers."""
    streams = interfaces.get_streams(source, config, num)
    plotdir = fullpath(outdir or source or '.')
    plotdir.mkdir(parents=True, exist_ok=True)
    for stream in streams:
        plot_flux_time(stream, user)
        plotpath = plotdir / stream.source.with_suffix('.png').name
        if verbose:
            print(f"Saved {plotpath}")
        plt.savefig(plotpath)
        if user.get('show'):
            plt.show()
        plt.close()


def plot_flux_time(stream: eprem.Observer, user: dict):
    """Plot flux versus time for this stream."""
    fig = plt.figure(figsize=(10, 6), layout='constrained')
    ax = fig.gca()
    location = interfaces.get_location(user)
    species = interfaces.get_species(user)
    units = interfaces.get_units(user)
    if user['energies']:
        energies = quantity.measure(*user['energies'])
    else:
        energies = stream.energies.withunit(units['energy'])
    flux = stream['flux'].withunit(units['flux'])
    times = stream.times.withunit(units['time'])
    cmap = mpl.colormaps['jet']
    colors = cmap(numpy.linspace(0, 1, len(energies)))
    yvalmax = None
    for i, energy in enumerate(energies):
        array = flux[:, location, species, energy].squeezed
        label = f"{float(energy):.3f} {energies.unit}"
        ax.plot(times, array, label=label, color=colors[i])
        arraymax = numpy.max(array)
        if yvalmax is None:
            yvalmax = arraymax
        else:
            yvalmax = max(yvalmax, arraymax)
    if user['ylim']:
        ax.set_ylim(user['ylim'])
    ax.set_xlabel(f"Time [{times.unit}]", fontsize=14)
    ax.set_ylabel(fr"Flux [{units['flux']}]", fontsize=14)
    ax.set_xscale('linear')
    ax.set_yscale('log')
    ax.legend(
        loc='center left',
        bbox_to_anchor=(1.0, 0.5),
        handlelength=1.0,
        ncols=math.ceil(len(energies) / 20),
    )
    fig.suptitle(plots.make_suptitle(stream, location, species), fontsize=20)


epilog = """
The argument to --location may be one or more values followed by an optional
metric unit. If the unit is present, this routine will interpret the values as
radii. Otherwise, it will interpret the values as shell indices. The argument to --energy behaves similarly.
"""
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=main.__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument(
        '-n', '--stream',
        dest='num',
        help="which stream to show",
        type=int,
    )
    parser.add_argument(
        '-c', '--config',
        help="name of simulation configuration file (default: eprem.cfg)",
    )
    parser.add_argument(
        '-i', '--input',
        dest='source',
        help="directory containing simulation data (default: current)",
    )
    parser.add_argument(
        '-o', '--output',
        dest='outdir',
        help="output directory (default: input directory)",
    )
    parser.add_argument(
        '--location',
        help="location(s) at which to plot flux (default: 0)",
        nargs='*',
    )
    parser.add_argument(
        '--species',
        help="ion species to plot (symbol or index; default: 0)",
    )
    parser.add_argument(
        '--energy',
        dest="energies",
        help="energy(-ies) at which to plot flux",
        nargs='*',
    )
    parser.add_argument(
        '--time-unit',
        help="metric unit in which to display times",
    )
    parser.add_argument(
        '--ylim',
        help="y-axis limits",
        nargs=2,
        type=float,
        metavar=('LO', 'HI'),
    )
    parser.add_argument(
        '-v', '--verbose',
        help="print runtime messages",
        action='store_true',
    )
    parser.add_argument(
        '--show',
        help="display the plot on the screen",
        action='store_true',
    )
    args = parser.parse_args()
    main(**vars(args))
