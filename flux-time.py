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
    for stream in streams:
        fig = plt.figure(figsize=(10, 6), layout='constrained')
        ax = fig.gca()
        plots.flux_time(stream, user, axes=ax)
        title = plots.make_title(stream, user, ['location', 'species'])
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
radii. Otherwise, it will interpret the values as shell indices. The argument to
--energy behaves similarly.
"""
if __name__ == '__main__':
    parser = interfaces.Parser(
        description=main.__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog,
        parents=[interfaces.common],
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
    args = parser.parse_args()
    main(**vars(args))
