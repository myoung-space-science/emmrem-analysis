import argparse
import typing

import matplotlib.pyplot as plt
import numpy

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
        plot_stream_intflux(stream, user)
        plotpath = plotdir / stream.source.with_suffix('.png').name
        if verbose:
            print(f"Saved {plotpath}")
        plt.savefig(plotpath)
        if user.get('show'):
            plt.show()
        plt.close()


def plot_stream_intflux(stream: eprem.Observer, user: dict) -> None:
    """Create a plot of integral flux versus time for this stream."""
    location = interfaces.get_location(user)
    species = interfaces.get_species(user)
    units = interfaces.get_units(user)
    intflux = stream['integral flux'].withunit(units['integral flux'])
    if user['energies']:
        energies = quantity.measure(*user['energies'])
    else:
        energies = quantity.measure(10.0, 50.0, 100.0, units['energy'])
    times = stream.times.withunit(units['time'])
    yvalmax = None
    fig = plt.figure(figsize=(6, 6), layout='constrained')
    ax = fig.gca()
    for energy in energies:
        array = intflux[:, location, species, energy].squeezed
        label = fr"$\geq${float(energy)} {energies.unit}"
        ax.plot(times, array, label=label)
        arraymax = numpy.max(array)
        if yvalmax is None:
            yvalmax = arraymax
        else:
            yvalmax = max(yvalmax, arraymax)
    if user['ylim']:
        ax.set_ylim(user['ylim'])
    ax.set_xlabel(f"Time [{times.unit}]", fontsize=14)
    ax.set_ylabel(fr"Integral Flux [{units['integral flux']}]", fontsize=14)
    ax.set_xscale('linear')
    ax.set_yscale('log')
    ax.legend(loc='center left', bbox_to_anchor=(1.0, 0.5), handlelength=1.0)
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
        help="location(s) at which to plot quantities (default: 0)",
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
