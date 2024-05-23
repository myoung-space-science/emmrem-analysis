import argparse
import typing

import matplotlib.pyplot as plt

from eprempy.paths import fullpath
from support import observers
from support import plots


def main(
    num: typing.Optional[int]=None,
    source: typing.Optional[str]=None,
    config: typing.Optional[str]=None,
    outdir: typing.Optional[str]=None,
    ylim: typing.Optional[typing.Tuple[float, float]]=None,
    verbose: bool=False,
    **user
) -> None:
    """Plot flux versus energy on a given stream."""
    streams = observers.get_streams(source, config, num)
    plotdir = fullpath(outdir or source or '.')
    plotdir.mkdir(parents=True, exist_ok=True)
    location = observers.get_location(user)
    species = observers.get_species(user)
    units = observers.get_units(user)
    for stream in streams:
        plt.figure(figsize=(12, 6))
        plots.flux(stream, location, species, units, ylim)
        plt.title(plots.make_suptitle(stream, location, species), fontsize=20)
        plt.tight_layout()
        plotname = f"{stream.source.stem}-flux-time.png"
        plotpath = plotdir / plotname
        if verbose:
            print(f"Saved {plotpath}")
        plt.savefig(plotpath)
        if user.get('show'):
            plt.show()
        plt.close()


epilog = """
The argument to --location may be one or more values followed by an optional
metric unit. If the unit is present, this routine will interpret the values as
radii. Otherwise, it will interpret the values as shell indices.

DEPRECATION NOTICE
------------------
Please use stream-survey.py instead of this program.
 
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
        dest='indir',
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
        help=(
            "ion species to plot"
            "; may be symbol or index (default: 0)"
        ),
    )
    parser.add_argument(
        '--time-unit',
        help="metric unit in which to display times",
    )
    parser.add_argument(
        '--energy-unit',
        help="metric unit in which to display energies",
    )
    parser.add_argument(
        '--flux-unit',
        help="metric unit in which to display flux values",
    )
    parser.add_argument(
        '--ylim',
        help="y-axis limits.",
        nargs=2,
        type=float,
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
