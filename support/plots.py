import math
import typing

import numpy
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from eprempy import eprem
from eprempy import measured
from eprempy import quantity
from . import interfaces


def flux_time(
    stream: eprem.Observer,
    user: dict,
    axes: typing.Optional[Axes]=None,
) -> None:
    """Plot flux versus time for this stream."""
    location = interfaces.get_location(user)
    species = interfaces.get_species(user)
    units = interfaces.get_units(user)
    if user.get('energies'):
        energies = quantity.measure(*user['energies'])
    else:
        energies = stream.energies.withunit(units['energy'])
    flux = stream['flux'].withunit(units['flux'])
    times = stream.times.withunit(units['time'])
    cmap = mpl.colormaps['jet']
    colors = cmap(numpy.linspace(0, 1, len(energies)))
    ax = axes or plt.gca()
    for i, energy in enumerate(energies):
        array = flux[:, location, species, energy].squeezed
        label = f"{float(energy):.3f} {energies.unit}"
        ax.plot(times, array, label=label, color=colors[i])
    if user.get('ylim'):
        ax.set_ylim(user['ylim'])
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


def flux_energy(
    stream: eprem.Observer,
    user: dict,
    axes: typing.Optional[Axes]=None,
) -> None:
    """Create a plot of flux versus energy for this stream."""
    location = interfaces.get_location(user)
    species = interfaces.get_species(user)
    units = interfaces.get_units(user)
    flux = stream['flux'].withunit(units['flux'])
    energies = stream.energies.withunit(units['energy'])
    # TODO:
    # - single time; multiple locations
    # - single location; multiple times
    times = interfaces.get_times(user)
    cmap = mpl.colormaps['jet']
    colors = cmap(numpy.linspace(0, 1, len(times)))
    ax = axes or plt.gca()
    for i, time in enumerate(times):
        array = flux[time, location, species, :].squeezed
        if isinstance(times, measured.Object):
            label = f"t = {float(time):.3f} {times.unit}"
        else:
            label = f"time step {int(time)}"
        ax.plot(energies, array, label=label, color=colors[i])
    if user.get('ylim'):
        ax.set_ylim(user['ylim'])
    ax.set_xlabel(f"Energy [{energies.unit}]", fontsize=14)
    ax.set_ylabel(fr"Flux [{units['flux']}]", fontsize=14)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.legend(
        loc='center left',
        bbox_to_anchor=(1.0, 0.5),
        handlelength=1.0,
        ncols=math.ceil(len(times) / 20),
    )


def fluence_energy(
    stream: eprem.Observer,
    user: dict,
    axes: typing.Optional[Axes]=None,
) -> None:
    """Create a plot of fluence versus energy for this stream."""
    location = interfaces.get_location(user)
    species = interfaces.get_species(user)
    units = interfaces.get_units(user)
    fluence = stream['fluence'].withunit(units['fluence'])
    energies = stream.energies.withunit(units['energy'])
    array = fluence[-1, location, species, :].squeezed
    ax = axes or plt.gca()
    ax.plot(energies, array)
    if user.get('ylim'):
        ax.set_ylim(user['ylim'])
    ax.set_xlabel(f"Energy [{energies.unit}]", fontsize=14)
    ax.set_ylabel(fr"Fluence [{units['fluence']}]", fontsize=14)
    ax.set_xscale('log')
    ax.set_yscale('log')


def intflux_time(
    stream: eprem.Observer,
    user: dict,
    axes: typing.Optional[Axes]=None,
) -> None:
    """Create a plot of integral flux versus time for this stream."""
    location = interfaces.get_location(user)
    species = interfaces.get_species(user)
    units = interfaces.get_units(user)
    intflux = stream['integral flux'].withunit(units['integral flux'])
    if user.get('energies'):
        energies = quantity.measure(*user['energies'])
    else:
        energies = quantity.measure(10.0, 50.0, 100.0, units['energy'])
    times = stream.times.withunit(units['time'])
    ax = axes or plt.gca()
    for energy in energies:
        array = intflux[:, location, species, energy].squeezed
        label = fr"$\geq${float(energy)} {energies.unit}"
        ax.plot(times, array, label=label)
    if user.get('ylim'):
        ax.set_ylim(user['ylim'])
    ax.set_xlabel(f"Time [{times.unit}]", fontsize=14)
    ax.set_ylabel(fr"Integral Flux [{units['integral flux']}]", fontsize=14)
    ax.set_xscale('linear')
    ax.set_yscale('log')
    ax.legend(loc='center left', bbox_to_anchor=(1.0, 0.5), handlelength=1.0)


def compute_yloglim(maxval):
    """Compute logarithmic y-axis limits based on `maxval`."""
    ylogmax = int(numpy.log10(maxval)) + 1
    return 10**(ylogmax-6), 10**ylogmax


def make_title(
    stream: eprem.Stream,
    user: dict,
) -> str:
    """Create a title string for plots."""
    parts = []
    if 'location' in user:
        location = interfaces.get_location(user)
        if isinstance(location, (quantity.Measurement, measured.Value)):
            strloc = f"radius = {float(location)} {location.unit}"
        elif isinstance(location, int):
            strloc = f"shell = {location}"
        else:
            raise TypeError(location)
        parts.append(strloc)
    if 'species' in user:
        species = interfaces.get_species(user)
        if isinstance(species, int):
            strspe = f"species = {stream.species.data[species]}"
        elif isinstance(species, str):
            strspe = f"species = {species}"
        else:
            raise TypeError(species)
        parts.append(strspe)
    return ' | '.join(parts)

