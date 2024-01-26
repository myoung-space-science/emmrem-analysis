import argparse
import typing

import numpy
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
    """Create survey plots for one or more point observers."""
    source = indir or '.'
    dataset = eprem.dataset(source=source, config=config)
    points = get_points(dataset, num)
    species = get_species(user)
    plotdir = fullpath(outdir or source)
    plotdir.mkdir(parents=True, exist_ok=True)
    for point in points:
        plot_point(point, species=species)
        plotpath = plotdir / point.source.with_suffix('.png').name
        if verbose:
            print(f"Saved {plotpath}")
        plt.savefig(plotpath)
        plt.close()


def plot_point(point: eprem.Observer, **kwargs):
    """Create a survey plot for this point."""
    fig, axs = plt.subplots(
        nrows=1,
        ncols=3,
        squeeze=True,
        figsize=(20, 6),
        layout='constrained',
    )
    plot_point_flux(axs[0], point, **kwargs)
    plot_point_fluence(axs[1], point, **kwargs)
    plot_point_intflux(axs[2], point, **kwargs)
    fig.suptitle(make_suptitle(point, **kwargs), fontsize=20)


def plot_point_flux(
    ax: Axes,
    point: eprem.Point,
    species: typing.Union[int, str],
) -> None:
    """Create a plot of flux versus time for this point."""
    flux = point['flux'].withunit('1 / (cm^2 s sr MeV/nuc)')
    energies = point.energies.withunit('MeV')
    yvalmax = None
    for i, energy in enumerate(energies):
        array = flux[:, 0, species, i].squeezed
        label = f"{float(energy):.3f} {energies.unit}"
        ax.plot(point.times, array, label=label)
        arraymax = numpy.max(array)
        if yvalmax is None:
            yvalmax = arraymax
        else:
            yvalmax = max(yvalmax, arraymax)
    ylogmax = int(numpy.log10(yvalmax)) + 1
    ax.set_ylim([10**(ylogmax-6), 10**ylogmax])
    ax.set_xlabel(f"Time [{point.times.unit}]", fontsize=14)
    ax.set_ylabel(r"Flux [1 / (cm$^2$ s sr MeV/nuc)]", fontsize=14)
    ax.set_xscale('linear')
    ax.set_yscale('log')
    ax.legend(loc='center left', bbox_to_anchor=(1.0, 0.5), handlelength=1.0)


def plot_point_fluence(
    ax: Axes,
    point: eprem.Point,
    species: typing.Union[int, str],
) -> None:
    """Create a plot of fluence versus energy for this point."""
    fluence = point['fluence'].withunit('1 / (cm^2 sr MeV/nuc)')
    energies = point.energies.withunit('MeV')
    array = fluence[-1, 0, species, :].squeezed
    ax.plot(energies, array)
    ylogmax = int(numpy.log10(numpy.max(array))) + 1
    ax.set_ylim([10**(ylogmax-6), 10**ylogmax])
    ax.set_xlabel(f"Energy [{energies.unit}]", fontsize=14)
    ax.set_ylabel(r"Fluence [1 / (cm$^2$ sr MeV/nuc)]", fontsize=14)
    ax.set_xscale('log')
    ax.set_yscale('log')


def plot_point_intflux(
    ax: Axes,
    point: eprem.Point,
    species: typing.Union[int, str],
) -> None:
    """Create a plot of integral flux versus time for this point."""
    intflux = point['integral flux'].withunit('1 / (cm^2 s sr)')
    energies = quantity.measure(1.0, 5.0, 10.0, 50.0, 100.0, 'MeV')
    yvalmax = None
    for energy in energies:
        array = intflux[:, 0, species, energy].squeezed
        label = f"{float(energy)} {energies.unit}"
        ax.plot(point.times, array, label=label)
        arraymax = numpy.max(array)
        if yvalmax is None:
            yvalmax = arraymax
        else:
            yvalmax = max(yvalmax, arraymax)
    ylogmax = int(numpy.log10(yvalmax)) + 1
    ax.set_ylim([10**(ylogmax-6), 10**ylogmax])
    ax.set_xlabel(f"Time [{point.times.unit}]", fontsize=14)
    ax.set_ylabel(r"Integral Flux [1 / (cm$^2$ s sr)]", fontsize=14)
    ax.set_xscale('linear')
    ax.set_yscale('log')
    ax.legend(loc='center left', bbox_to_anchor=(1.0, 0.5), handlelength=1.0)


def get_points(dataset: eprem.Dataset, num: typing.Optional[int]=None):
    """Get all relevant point observers."""
    points = dataset.points
    if isinstance(num, int):
        return [points[num]]
    return list(points.values())


def make_suptitle(
    point: eprem.Point,
    species: typing.Union[int, str],
) -> str:
    """Create the top-level plot title."""
    radius = point.r.withunit('au')
    strloc = f"radius = {float(radius):.2f} {radius.unit}"
    if isinstance(species, int):
        strspe = f"species = {point.species.data[species]}"
    elif isinstance(species, str):
        strspe = f"species = {species}"
    else:
        raise TypeError(species)
    return f"{strloc} | {strspe}"


def get_species(user: dict):
    """Get the ion species to plot."""
    species = user.get('species')
    if species is not None: # allow value to be 0
        return species
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=main.__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        '-n', '--point',
        dest='num',
        help="which point to show",
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
        '--species',
        help=(
            "ion species to plot"
            "; may be symbol or index (default: 0)"
        ),
    )
    parser.add_argument(
        '-v', '--verbose',
        help="print runtime messages",
        action='store_true',
    )
    args = parser.parse_args()
    main(**vars(args))
