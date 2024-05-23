import argparse
import typing

import matplotlib.pyplot as plt

from eprempy import eprem
from eprempy import quantity
from eprempy.paths import fullpath
from support import observers


def main(
    num: typing.Optional[int]=None,
    source: typing.Optional[str]=None,
    config: typing.Optional[str]=None,
    outdir: typing.Optional[str]=None,
    verbose: bool=False,
    **user
) -> None:
    """Plot flux versus energy on a given stream."""
    streams = observers.get_streams(source, config, num)
    plotdir = fullpath(outdir or source or '.')
    plotdir.mkdir(parents=True, exist_ok=True)
    for stream in streams:
        stream_flux(stream, user)
        plotname = f"{stream.source.stem}-flux-energy.png"
        plotpath = plotdir / plotname
        if verbose:
            print(f"Saved {plotpath}")
        plt.savefig(plotpath)
        if user.get('show'):
            plt.show()
        plt.close()


def stream_flux(
    stream: eprem.Stream,
    user: dict,
) -> None:
    """Plot the flux on a given stream."""
    times = observers.get_times(user)
    locations = observers.get_locations(user)
    ntimes = len(times)
    nlocations = len(locations)
    units = {k: user.get(f'{k}_unit') or u for k, u in observers.UNITS.items()}
    flux = stream['flux'].withunit(units['flux'])
    species = observers.get_species(user)
    arrays = flux[times, locations, species, :].squeezed
    energies = stream.energies.withunit(units['energy'])
    if ntimes == 1 and nlocations == 1:
        plt.plot(energies, arrays[0])
    elif ntimes > 1 and nlocations == 1:
        for time, array in zip(times, arrays):
            if isinstance(times, quantity.Measurement):
                label = f"t = {float(time)} {times.unit}"
            else:
                label = f"t = {time}"
            plt.plot(energies, array, label=label)
    elif nlocations > 1 and ntimes == 1:
        for location, array in zip(locations, arrays):
            if isinstance(locations, quantity.Measurement):
                label = f"r = {float(location)} {locations.unit}"
            else:
                label = f"s = {location}"
            plt.plot(energies, array, label=label)
    else:
        raise ValueError(
            "Either time or location, but not both, may be multi-valued"
        ) from None
    if user.get('show_initial'):
        initial = flux[0, 0, species, :].squeezed
        plt.plot(energies, initial, 'k--', label='Seed Spectrum')
    plt.legend()
    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel(f'Energy [{units["energy"]}]')
    plt.ylabel(f'Flux [{units["flux"]}]')
    if xlim := user.get('xlim'):
        plt.xlim(xlim)
    if ylim := user.get('ylim'):
        plt.ylim(ylim)


epilog = """
Notes on time and location:
    * You may provide a single value for both parameters, or a single value for
      one and multiple values for the other. The latter case will produce a plot
      with a line for each value of the multi-valued parameter.
    * Passing a metric unit as the final argument to --time will cause this
      routine to interpret the preceeding numerical values as physical times.
      Otherwise, this routine will interpret them as time-step indices.
    * Passing a metric unit as the final argument to --location will cause this
      routine to interpret the preceeding numerical values as physical radii.
      Otherwise, this routine will interpret them as shell indices.
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
        '--time',
        help="time(s) at which to plot flux (default: 0)",
        nargs='*',
    )
    parser.add_argument(
        '--location',
        help="location(s) at which to plot flux (default: 0)",
        nargs='*',
    )
    parser.add_argument(
        '--species',
        help=(
            "ion species to plot"
            "; may be symbol or index (default: 0)"
        ),
    )
    parser.add_argument(
        '--energy-unit',
        help="metric unit in which to display energy values",
    )
    parser.add_argument(
        '--flux-unit',
        help="metric unit in which to display flux values",
    )
    parser.add_argument(
        '--xlim',
        help="x-axis limits.",
        nargs=2,
        type=float,
    )
    parser.add_argument(
        '--ylim',
        help="y-axis limits.",
        nargs=2,
        type=float,
    )
    parser.add_argument(
        '--show-initial',
        help="include the initial spectrum at the solar surface.",
        action='store_true',
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
