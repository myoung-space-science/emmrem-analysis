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
        f(axs[i], stream, c, yscale, key)


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
    stream: eprem.Stream,
    time: typing.Union[int, quantity.Measurement],
    yscale: str,
    key: str,
) -> None:
    """Plot the given quantities at the given time."""
    radius = stream['radius'][time, :].withunit('au').squeezed
    subset = SUBSETS[key]
    if subset['type'] == 'vector':
        keys = [f"{key}{c}" for c in ('r', 'theta', 'phi')]
    else:
        keys = [key]
    for k in keys:
        x = stream[k][time, :].withunit(subset['unit'])
        array = x.squeezed
        ax.plot(radius, array, label=LABELS[k])
    ax.set_xlabel("Radius [au]", fontsize=14)
    ax.set_ylabel(f"[{x.unit.format('tex')}]")
    ax.set_yscale(yscale)
    ax.legend()
    ax.label_outer()


def plot_at_location(
    ax: Axes,
    stream: eprem.Stream,
    location: typing.Union[int, quantity.Measurement],
    yscale: str,
    key: str,
) -> None:
    """Plot the named quantities at the given location."""
    subset = SUBSETS[key]
    if subset['type'] == 'vector':
        keys = [f"{key}{c}" for c in ('r', 'theta', 'phi')]
    else:
        keys = [key]
    for k in keys:
        x = stream[k][:, location].withunit(subset['unit'])
        array = x.squeezed
        ax.plot(stream.times, array, label=LABELS[k])
    ax.set_xlabel(f"Time [{stream.times.unit}]", fontsize=14)
    ax.set_ylabel(f"[{x.unit.format('tex')}]")
    ax.set_yscale(yscale)
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
        '-v', '--verbose',
        help="print runtime messages",
        action='store_true',
    )
    args = parser.parse_args()
    main(**vars(args))
