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
    location = get_location(user)
    plotdir = fullpath(outdir or source)
    plotdir.mkdir(parents=True, exist_ok=True)
    for stream in streams:
        plot_stream(stream, location=location)
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


def get_location(user: dict):
    """Get the shell or radius at which to plot."""
    shell = user.get('shell')
    if shell is not None: # allow value to be 0
        return shell
    if radius := user.get('radius'):
        return quantity.measure(float(radius[0]), radius[1]).withunit('au')
    return 0


def plot_stream(stream: eprem.Stream, location):
    """Create a survey plot for this stream."""
    fig, axs = plt.subplots(
        nrows=3,
        ncols=1,
        sharex=True,
    )
    plot_quantities(axs[0], stream, location, 'Br', 'Btheta', 'Bphi')
    plot_quantities(axs[1], stream, location, 'Ur', 'Utheta', 'Uphi')
    plot_quantities(axs[2], stream, location, 'rho')


QUANTITIES = {
    'Br': {'label': r'$B_r$', 'unit': 'nT'},
    'Btheta': {'label': r'$B_\theta$', 'unit': 'nT'},
    'Bphi': {'label': r'$B_\phi$', 'unit': 'nT'},
    'Ur': {'label': r'$U_r$', 'unit': 'cm / s'},
    'Utheta': {'label': r'$U_\theta$', 'unit': 'cm / s'},
    'Uphi': {'label': r'$U_\phi$', 'unit': 'cm / s'},
    'rho': {'label': r'$\rho$', 'unit': 'cm^-3'},
}


def plot_quantities(
    ax: Axes,
    stream: eprem.Stream,
    location: typing.Union[int, quantity.Measurement],
    *keys: str,
) -> None:
    """Plot the named quantities."""
    for key in keys:
        q = QUANTITIES[key]
        x = stream[key][:, location].withunit(q['unit'])
        array = x.squeezed
        ax.plot(stream.times, array, label=q['label'])
    ax.set_xlabel(f"Time [{stream.times.unit}]", fontsize=14)
    ax.set_ylabel(f"[{x.unit.format('tex')}]")
    ax.legend()
    ax.label_outer()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=main.__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
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
    location = parser.add_mutually_exclusive_group()
    location.add_argument(
        '--shell',
        help="shell at which to plot flux (default: 0)",
        type=int,
        nargs=1,
    )
    location.add_argument(
        '--radius',
        help="radius at which to plot flux (default: inner boundary)",
        nargs=2,
        metavar=('RADIUS', 'UNIT'),
    )
    parser.add_argument(
        '-v', '--verbose',
        help="print runtime messages",
        action='store_true',
    )
    args = parser.parse_args()
    main(**vars(args))
