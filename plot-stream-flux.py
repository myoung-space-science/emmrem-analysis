import argparse
import pathlib
import typing

import matplotlib.pyplot as plt
import numpy

from eprempy import eprem


def main(
    number: int,
    time: typing.Iterable[float],
    radius: typing.Iterable[float],
    show_initial: bool=False,
    xlim: typing.Iterable[float]=None,
    ylim: typing.Iterable[float]=None,
    datadir: str=None,
    savedir: str=None,
) -> None:
    """Plot the flux on a given stream."""
    stream = eprem.stream(number, path=datadir)
    flux = stream['flux']
    units = {
        'energy': 'MeV',
        'flux': 'cm^-2 s^-1 sr^-1 (MeV/nuc)^-1',
    }
    ntimes = len(time)
    nradii = len(radius)
    if ntimes > 1 and nradii > 1:
        raise ValueError(
            "Either time or radius, but not both, may be multi-valued"
        ) from None
    observations = flux.observe(
        time=[*time, 'hour'],
        radius=[*radius, 'au']
    ).unit(units['flux'])
    labels = [
        f"r = {r} au" for r in radius
    ] if nradii > 1 else [
        f"t = {t} hour" for t in time
    ]
    energy = stream.energy(units['energy'])
    arrays = numpy.squeeze(observations)
    for array, label in zip(arrays, labels):
        plt.plot(energy, array, label=label)
    if show_initial:
        flux.reset()
        initial = numpy.squeeze(
            flux.observe(time=0, shell=0).unit(units['flux'])
        )
        plt.plot(energy, initial, 'k--', label='Seed Spectrum')
    plt.legend()
    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel(f'Energy [{units["energy"]}]')
    plt.ylabel(f'Flux [{units["flux"]}]')
    if xlim:
        plt.xlim(xlim)
    if ylim:
        plt.ylim(ylim)
    if nradii > 1:
        info = f"t = {time[0]} hours"
        name = f"t{time[0]}h"
    else:
        info = f"r = {radius[0]} au"
        name = f"r{radius[0]}au"
    plt.title(f"Stream {number} ({info})")
    plotdir = pathlib.Path(savedir or '.').expanduser().resolve()
    plotpath = plotdir / f'stream{number}_flux-{name}.png'
    print(f"Saving {plotpath}")
    plt.savefig(plotpath)


epilog = """
Note on time and radius: You may provide a single value for both parameters, or
a single value for one and multiple values for the other. The latter case will
produce a plot with a line for each value of the multi-valued parameter.
"""
if __name__ == '__main__':
    p = argparse.ArgumentParser(
        description=main.__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog,
    )
    p.add_argument(
        'number',
        help="The stream number.",
        type=int,
    )
    p.add_argument(
        '-t',
        '--time',
        help="The time, in hours, at which to plot flux.",
        type=float,
        nargs='*',
    )
    p.add_argument(
        '-r',
        '--radius',
        help="The radius, in au, at which to plot flux.",
        type=float,
        nargs='*',
    )
    p.add_argument(
        '--show_initial',
        help="Include the initial spectrum at the solar surface.",
        action='store_true',
    )
    p.add_argument(
        '-i',
        '--datadir',
        help="The directory from which to read (default: current directory).",
    )
    p.add_argument(
        '-o',
        '--savedir',
        help="The directory to which to write (default: current directory).",
    )
    p.add_argument(
        '--xlim',
        help="The x-axis limits.",
        nargs=2,
        type=float,
    )
    p.add_argument(
        '--ylim',
        help="The y-axis limits.",
        nargs=2,
        type=float,
    )
    args = p.parse_args()
    main(**vars(args))
