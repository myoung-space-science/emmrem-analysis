import argparse
import typing

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from eprempy import eprem
from eprempy import quantity
from eprempy.paths import fullpath


def main(
    num: int=None,
    indir: str=None,
    config: str=None,
    outdir: str=None,
    verbose: bool=False,
    **user
) -> None:
    """Plot a survey of MHD quantities for a given stream observer."""
    source = indir or '.'
    dataset = eprem.dataset(source=source, config=config)
    streams = get_streams(dataset, num)
    time = get_time(user)
    location = get_location(user)
    plotdir = fullpath(outdir or source)
    plotdir.mkdir(parents=True, exist_ok=True)
    for stream in streams:
        plot_stream(
            stream,
            time=time,
            location=location,
            ylog=user.get('ylog'),
            ylims=get_ylims(user),
        )
        plotname = f"mhd-{stream.source.stem}.png"
        plotpath = plotdir / plotname
        if verbose:
            print(f"Saved {plotpath}")
        plt.savefig(plotpath)
        plt.close()


def get_streams(dataset: eprem.Dataset, num: typing.Optional[int]=None):
    """Get all relevant stream observers."""
    streams = dataset.streams
    if isinstance(num, int):
        return [streams[num]]
    return list(streams.values())


def get_time(user: dict):
    """Get the time at which to plot, if given."""
    step = user.get('step')
    if step is not None: # allow value to be 0
        return step
    if time := user.get('time'):
        return quantity.measure(float(time[0]), time[1])


def get_location(user: dict):
    """Get the shell or radius at which to plot, if given."""
    shell = user.get('shell')
    if shell is not None: # allow value to be 0
        return shell
    if radius := user.get('radius'):
        return quantity.measure(float(radius[0]), radius[1]).withunit('au')


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


def plot_stream(
    stream: eprem.Stream,
    time: typing.Optional[typing.Union[int, quantity.Measurement]],
    location: typing.Optional[typing.Union[int, quantity.Measurement]],
    ylog: typing.Optional[typing.List[str]],
    ylims: typing.Dict[str, typing.Optional[tuple]],
) -> None:
    """Create a survey plot for this stream."""
    fig, axs = plt.subplots(
        nrows=3,
        ncols=1,
        sharex=True,
    )
    # NOTE: Either time or location could be 0, so we can't rely on `if time and
    # not location` or `if location and not time`.
    if time is None and location is not None:
        f = plot_at_location
        c = location
    elif location is None and time is not None:
        f = plot_at_time
        c = time
    else:
        raise ValueError(
            f"Either time ({time}) or location ({location}) must be None"
        ) from None
    if ylog == []:
        ylog = list(SUBSETS)
    elif ylog is None:
        ylog = []
    for i, key in enumerate(('B', 'U', 'rho')):
        yscale = 'log' if key in ylog else 'linear'
        f(axs[i], key, stream, c, yscale, ylims[key])


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
    yscale: str,
    ylim: tuple,
) -> None:
    """Plot the given quantities at the given time."""
    indices = (time, slice(None))
    plot_quantities(
        ax,
        key,
        stream['radius'][indices].withunit('au').squeezed,
        stream,
        indices,
        "Radius [au]",
        yscale,
        ylim,
    )


def plot_at_location(
    ax: Axes,
    key: str,
    stream: eprem.Stream,
    location: typing.Union[int, quantity.Measurement],
    yscale: str,
    ylim: tuple,
) -> None:
    """Plot the named quantities at the given location."""
    plot_quantities(
        ax,
        key,
        stream.times,
        stream,
        (slice(None), location),
        f"Time [{stream.times.unit}]",
        yscale,
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
    if ylim is not None:
        ax.set_ylim(ylim)
    ax.legend()
    ax.label_outer()


epilog = \
"""
Notes
-----
You must pass a constraint via one (and only one) of --step, --time, --shell, 
or --radius.
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
    constraint = parser.add_mutually_exclusive_group(required=True)
    constraint.add_argument(
        '--step',
        help="time step at which to plot MHD quantities",
        type=int,
        nargs=1,
    )
    constraint.add_argument(
        '--time',
        help="time at which to plot MHD quantities",
        nargs=2,
        metavar=('TIME', 'UNIT'),
    )
    constraint.add_argument(
        '--shell',
        help="shell at which to plot MHD quantities",
        type=int,
        nargs=1,
    )
    constraint.add_argument(
        '--radius',
        help="radius at which to plot MHD quantities",
        nargs=2,
        metavar=('RADIUS', 'UNIT'),
    )
    parser.add_argument(
        '--ylog',
        help="log scale the y axis of all or some quantities",
        nargs='*',
        metavar=('B, U, rho'),
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
    args = parser.parse_args()
    main(**vars(args))
