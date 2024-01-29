"""
This script is designed to work with files created by `write-node-history.py`.
"""

import argparse
import pathlib
import typing

import matplotlib.pyplot as plt

import node
from tools.graphics import parse_plot_kws


def main(
    filepaths: typing.Iterable[str],
    plot_kws: str=None,
    verbose: bool=False,
) -> None:
    """Plot the node histories contained in the given files."""
    plot_kws = plot_kws or ''
    kwargs = parse_plot_kws(plot_kws)
    for filepath in filepaths:
        history = node.parse_history(filepath)
        info = history['info'].copy()
        plt.plot(history['time'], history['data'])
        plt.xscale(kwargs.get('xscale', 'linear'))
        plt.yscale(kwargs.get('yscale', 'linear'))
        plt.xlabel(f"Time [{info['time units']}]")
        plt.ylabel(f"{info['data name']} [{info['data units']}]")
        savepath = pathlib.Path(filepath).with_suffix('.png')
        if verbose:
            print(f"Saving {savepath} ...")
        plt.savefig(savepath)
        plt.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(
        description=main.__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        'filepaths',
        help="path(s) to file(s) written by write-node-history.py",
        nargs='*',
    )
    p.add_argument(
        '--plot_kws',
        help=(
            "key-value pairs to pass to plotting routines"
            "\nPass multiple comma-separated key-value pairs"
            " as a single quoted string"
        ),
    )
    p.add_argument(
        '-v',
        '--verbose',
        help="print runtime messages",
        action='store_true',
    )
    args = p.parse_args()
    main(**vars(args))
