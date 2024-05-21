import typing

import numpy
import matplotlib as mpl
from matplotlib.axes import Axes

from eprempy import eprem
from eprempy import quantity


def flux(
    ax: Axes,
    observer: typing.Union[eprem.Stream, eprem.Point],
    location: typing.Union[int, quantity.Measurement],
    species: typing.Union[int, str],
    units: typing.Dict[str, str],
    ylim: typing.Tuple[float, float],
) -> None:
    """Create a plot of flux versus time for this stream."""
    flux = observer['flux'].withunit(units['flux'])
    energies = observer.energies.withunit(units['energy'])
    times = observer.times.withunit(units['time'])
    cmap = mpl.colormaps['jet']
    colors = cmap(numpy.linspace(0, 1, len(energies)))
    yvalmax = None
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
    ax.set_ylabel(r"Flux [1 / (cm$^2$ s sr MeV/nuc)]", fontsize=14)
    ax.set_xscale('linear')
    ax.set_yscale('log')
    ax.legend(loc='center left', bbox_to_anchor=(1.0, 0.5), handlelength=1.0)


def fluence(
    ax: Axes,
    observer: typing.Union[eprem.Stream, eprem.Point],
    location: typing.Union[int, quantity.Measurement],
    species: typing.Union[int, str],
    units: typing.Dict[str, str],
    ylim: typing.Tuple[float, float],
) -> None:
    """Create a plot of fluence versus energy for this stream."""
    fluence = observer['fluence'].withunit(units['fluence'])
    energies = observer.energies.withunit(units['energy'])
    array = fluence[-1, location, species, :].squeezed
    ax.plot(energies, array)
    ax.set_ylim(ylim or compute_yloglim(numpy.max(array)))
    ax.set_xlabel(f"Energy [{energies.unit}]", fontsize=14)
    ax.set_ylabel(r"Fluence [1 / (cm$^2$ sr MeV/nuc)]", fontsize=14)
    ax.set_xscale('log')
    ax.set_yscale('log')


def intflux(
    ax: Axes,
    observer: typing.Union[eprem.Stream, eprem.Point],
    location: typing.Union[int, quantity.Measurement],
    species: typing.Union[int, str],
    units: typing.Dict[str, str],
    ylim: typing.Tuple[float, float],
) -> None:
    """Create a plot of integral flux versus time for this stream."""
    intflux = observer['integral flux'].withunit(units['integral flux'])
    energies = quantity.measure(1.0, 5.0, 10.0, 50.0, 100.0, units['energy'])
    times = observer.times.withunit(units['time'])
    yvalmax = None
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
    ax.set_ylabel(r"Integral Flux [1 / (cm$^2$ s sr)]", fontsize=14)
    ax.set_xscale('linear')
    ax.set_yscale('log')
    ax.legend(loc='center left', bbox_to_anchor=(1.0, 0.5), handlelength=1.0)


def compute_yloglim(maxval):
    """Compute logarithmic y-axis limits based on `maxval`."""
    ylogmax = int(numpy.log10(maxval)) + 1
    return 10**(ylogmax-6), 10**ylogmax


