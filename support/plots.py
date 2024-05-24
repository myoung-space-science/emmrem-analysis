import math
import typing

import numpy
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from eprempy import eprem
from eprempy import measured
from eprempy import quantity


def flux(
    observer: typing.Union[eprem.Stream, eprem.Point],
    location: typing.Union[int, quantity.Measurement],
    species: typing.Union[int, str],
    units: typing.Dict[str, str],
    ylim: typing.Tuple[float, float],
    axes: typing.Optional[Axes]=None,
) -> None:
    """Create a plot of flux versus time for this stream."""
    flux = observer['flux'].withunit(units['flux'])
    energies = observer.energies.withunit(units['energy'])
    times = observer.times.withunit(units['time'])
    cmap = mpl.colormaps['jet']
    colors = cmap(numpy.linspace(0, 1, len(energies)))
    yvalmax = None
    ax = axes or plt.gca()
    for i, energy in enumerate(energies):
        array = flux[:, location, species, i].squeezed
        label = f"{float(energy):.3f} {energies.unit}"
        ax.plot(times, array, label=label, color=colors[i])
        arraymax = numpy.max(array)
        if yvalmax is None:
            yvalmax = arraymax
        else:
            yvalmax = max(yvalmax, arraymax)
    ax.set_ylim(ylim or compute_yloglim(yvalmax))
    ax.set_xlabel(f"Time [{times.unit}]", fontsize=14)
    ax.set_ylabel(fr"Flux [{units['flux']}]", fontsize=14)
    ax.set_xscale('linear')
    ax.set_yscale('log')
    ax.legend(
        loc='center left',
        bbox_to_anchor=(1.0, 0.5),
        handlelength=1.0,
        ncols=math.ceil(len(energies) / 20),
    )


def fluence(
    observer: typing.Union[eprem.Stream, eprem.Point],
    location: typing.Union[int, quantity.Measurement],
    species: typing.Union[int, str],
    units: typing.Dict[str, str],
    ylim: typing.Tuple[float, float],
    axes: typing.Optional[Axes]=None,
) -> None:
    """Create a plot of fluence versus energy for this stream."""
    fluence = observer['fluence'].withunit(units['fluence'])
    energies = observer.energies.withunit(units['energy'])
    array = fluence[-1, location, species, :].squeezed
    ax = axes or plt.gca()
    ax.plot(energies, array)
    ax.set_ylim(ylim or compute_yloglim(numpy.max(array)))
    ax.set_xlabel(f"Energy [{energies.unit}]", fontsize=14)
    ax.set_ylabel(fr"Fluence [{units['fluence']}]", fontsize=14)
    ax.set_xscale('log')
    ax.set_yscale('log')


def intflux(
    observer: typing.Union[eprem.Stream, eprem.Point],
    location: typing.Union[int, quantity.Measurement],
    species: typing.Union[int, str],
    units: typing.Dict[str, str],
    ylim: typing.Tuple[float, float],
    axes: typing.Optional[Axes]=None,
) -> None:
    """Create a plot of integral flux versus time for this stream."""
    intflux = observer['integral flux'].withunit(units['integral flux'])
    energies = quantity.measure(1.0, 5.0, 10.0, 50.0, 100.0, units['energy'])
    times = observer.times.withunit(units['time'])
    yvalmax = None
    ax = axes or plt.gca()
    for energy in energies:
        array = intflux[:, location, species, energy].squeezed
        label = f"{float(energy)} {energies.unit}"
        ax.plot(times, array, label=label)
        arraymax = numpy.max(array)
        if yvalmax is None:
            yvalmax = arraymax
        else:
            yvalmax = max(yvalmax, arraymax)
    ax.set_ylim(ylim or compute_yloglim(yvalmax))
    ax.set_xlabel(f"Time [{times.unit}]", fontsize=14)
    ax.set_ylabel(fr"Integral Flux [{units['integral flux']}]", fontsize=14)
    ax.set_xscale('linear')
    ax.set_yscale('log')
    ax.legend(loc='center left', bbox_to_anchor=(1.0, 0.5), handlelength=1.0)


def compute_yloglim(maxval):
    """Compute logarithmic y-axis limits based on `maxval`."""
    ylogmax = int(numpy.log10(maxval)) + 1
    return 10**(ylogmax-6), 10**ylogmax


def make_suptitle(
    stream: eprem.Stream,
    location: typing.Union[int, quantity.Measurement],
    species: typing.Union[int, str],
) -> str:
    """Create the top-level plot title."""
    if isinstance(location, (quantity.Measurement, measured.Value)):
        strloc = f"radius = {float(location)} {location.unit}"
    elif isinstance(location, int):
        strloc = f"shell = {location}"
    else:
        raise TypeError(location)
    if isinstance(species, int):
        strspe = f"species = {stream.species.data[species]}"
    elif isinstance(species, str):
        strspe = f"species = {species}"
    else:
        raise TypeError(species)
    return f"{strloc} | {strspe}"


