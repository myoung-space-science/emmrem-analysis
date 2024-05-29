import argparse
import typing

import matplotlib.pyplot as plt

from eprempy.paths import fullpath
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
    fig = plt.figure(figsize=(6, 6), layout='constrained')
    ax = fig.gca()
    for stream in streams:
        plots.fluence_energy(stream, user, axes=ax)
        title = plots.make_title(stream, user)
        ax.set_title(title, fontsize=20)
        plotpath = plotdir / stream.source.with_suffix('.png').name
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
        '--energy-unit',
        help="metric unit in which to display energies",
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
