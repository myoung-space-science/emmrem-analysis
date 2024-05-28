import argparse
import typing

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from eprempy import eprem
from eprempy import quantity
from eprempy.paths import fullpath
from support import interfaces


def main(
    num: int=None,
    source: str=None,
    config: str=None,
    outdir: str=None,
    verbose: bool=False,
    **user
) -> None:
    """Plot a survey of MHD quantities for a given stream observer."""
    streams = interfaces.get_streams(source, config, num)
    plotdir = fullpath(outdir or source or '.')
    plotdir.mkdir(parents=True, exist_ok=True)
    for stream in streams:
        plot_stream(stream, user)
        plotname = f"mhd-{stream.source.stem}.png"
        plotpath = plotdir / plotname
        if verbose:
            print(f"Saved {plotpath}")
        plt.savefig(plotpath)
        if user.get('show'):
            plt.show()
        plt.close()


def get_streams(dataset: eprem.Dataset, num: typing.Optional[int]=None):
    """Get all relevant stream observers."""
    streams = dataset.streams
    if isinstance(num, int):
        return [streams[num]]
    return list(streams.values())


def get_ylims(user: dict):
    """Get the y-axis limits from user arguments."""
    return {
        'B': user.get('B_ylim'),
        'U': user.get('U_ylim'),
        'rho': user.get('rho_ylim'),
    }


SUBSETS = {
    'B':   {'unit': 'nT',     'type': 'vector'},
    'U':   {'unit': 'cm / s', 'type': 'vector'},
    'rho': {'unit': 'cm^-3',  'type': 'scalar'},
}


def plot_stream(stream: eprem.Stream, user: dict) -> None:
    """Create a survey plot for this stream."""
    fig, axs = plt.subplots(
        nrows=3,
        ncols=1,
        sharex=True,
    )
    # NOTE: Either time or location could be 0, so we can't rely on `if time and
    # not location` or `if location and not time`.
    if user['time'] is None and user['location'] is not None:
        f = plot_at_location
        c = interfaces.get_locations(user)
        u = 'hour'
    elif user['location'] is None and user['time'] is not None:
        f = plot_at_time
        c = interfaces.get_times(user)
        u = 'au'
    else:
        raise ValueError(
            f"One of either time or location must be None"
        ) from None
    ylog = user.get('ylog')
    ylims = get_ylims(user)
    if ylog == []:
        ylog = list(SUBSETS)
    elif ylog is None:
        ylog = []
    for i, key in enumerate(('B', 'U', 'rho')):
        yscale = 'log' if key in ylog else 'linear'
        f(axs[i], key, stream, c, u, yscale, user['xlim'], ylims[key])


LABELS = {
    'Br': r'$B_r$',
    'Btheta': r'$B_\theta$',
    'Bphi': r'$B_\phi$',
    'Ur': r'$U_r$',
    'Utheta': r'$U_\theta$',
    'Uphi': r'$U_\phi$',
    'rho': r'$\rho$',
}


def plot_at_time(
    ax: Axes,
    key: str,
    stream: eprem.Stream,
    time: typing.Union[int, quantity.Measurement],
    unit: str,
    yscale: str,
    xlim: tuple,
    ylim: tuple,
) -> None:
    """Plot the given quantities at the given time."""
    indices = (time, slice(None))
    plot_quantities(
        ax,
        key,
        stream['radius'][indices].withunit(unit).squeezed,
        stream,
        indices,
        f"Radius [{unit}]",
        yscale,
        xlim,
        ylim,
    )


def plot_at_location(
    ax: Axes,
    key: str,
    stream: eprem.Stream,
    location: typing.Union[int, quantity.Measurement],
    unit: str,
    yscale: str,
    xlim: tuple,
    ylim: tuple,
) -> None:
    """Plot the named quantities at the given location."""
    plot_quantities(
        ax,
        key,
        stream.times.withunit(unit),
        stream,
        (slice(None), location),
        f"Time [{unit}]",
        yscale,
        xlim,
        ylim,
    )


def plot_quantities(
    ax: Axes,
    key: str,
    x,
    stream: eprem.Stream,
    indices: tuple,
    xlabel: str,
    yscale: str,
    xlim: tuple,
    ylim: tuple,
) -> None:
    """Common plotting logic."""
    subset = SUBSETS[key]
    if subset['type'] == 'vector':
        quantities = [f"{key}{c}" for c in ('r', 'theta', 'phi')]
    else:
        quantities = [key]
    for quantity in quantities:
        y = stream[quantity][indices].withunit(subset['unit'])
        ax.plot(x, y.squeezed, label=LABELS[quantity])
    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel(f"[{y.unit.format('tex')}]")
    ax.set_yscale(yscale)
    if xlim is not None:
        ax.set_xlim(xlim)
    if ylim is not None:
        ax.set_ylim(ylim)
    ax.legend()
    ax.label_outer()


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
        help="time(s) at which to plot MHD quantities (default: 0)",
        nargs='*',
    )
    parser.add_argument(
        '--location',
        help="location(s) at which to plot MHD quantities (default: 0)",
        nargs='*',
    )
    parser.add_argument(
        '--ylog',
        help="log scale the y axis of all or some quantities",
        nargs='*',
        metavar=('B, U, rho'),
    )
    parser.add_argument(
        '--xlim',
        help="x-axis limits",
        nargs=2,
        type=float,
        metavar=("LO", 'HI'),
    )
    parser.add_argument(
        '--B-ylim',
        help="magnetic-field y-axis limits",
        nargs=2,
        type=float,
        metavar=("LO", 'HI'),
    )
    parser.add_argument(
        '--U-ylim',
        help="velocity-field y-axis limits",
        nargs=2,
        type=float,
        metavar=("LO", 'HI'),
    )
    parser.add_argument(
        '--rho-ylim',
        help="density y-axis limits",
        nargs=2,
        type=float,
        metavar=("LO", 'HI'),
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
