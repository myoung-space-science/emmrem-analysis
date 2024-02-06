import argparse
import typing

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from eprempy import eprem
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
    plotdir = fullpath(outdir or source)
    plotdir.mkdir(parents=True, exist_ok=True)
    for stream in streams:
        plot_stream(stream)


def get_streams(dataset: eprem.Dataset, num: typing.Optional[int]=None):
    """Get all relevant stream observers."""
    streams = dataset.streams
    if isinstance(num, int):
        return [streams[num]]
    return list(streams.values())


def plot_stream(stream: eprem.Observer, **kwargs):
    """Create a survey plot for this stream."""
    # Layout:
    #   ----------------
    # R | Br | Bt | Bp |
    #   ----------------
    # T | Br | Bt | Bp |
    #   ----------------
    # P | Br | Bt | Bp |
    #   ----------------
    #        Time
    fig, axs = plt.subplot_mosaic(
        [
            ['Brr', 'Btr', 'Bpr'],
            ['Brt', 'Btt', 'Bpt'],
            ['Brp', 'Btp', 'Bpp'],
        ],
        sharex=True,
    )
    br = stream['Br']
    bt = stream['Btheta']
    bp = stream['Bphi']
    plt.pcolormesh()


def plot_brr(ax: Axes):
    """"""
    ax.pcolormesh()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=main.__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument()
    parser.add_argument(
        '-v', '--verbose',
        help="print runtime messages",
        action='store_true',
    )
    args = parser.parse_args()
    main(**vars(args))
