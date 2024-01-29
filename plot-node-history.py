import argparse
import pathlib
import typing
import sys

import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.axes import Axes
import  matplotlib.ticker as tck
import numpy
import numpy.typing
from scipy import signal

from eprempy import eprem
from eprempy import paths
from eprempy import physical
from eprempy import atomic
from eprempy import universal
from tools.graphics import parse_plot_kws

ERG_MEV = 1e6 * universal.CGS['eV']
R_SUN = 6.96e10


def main(
    quantities: typing.List[str],
    filedir: str=None,
    pattern: str=None,
    species: str='H+',
    energy: float=0.0,
    plot_kws: str=None,
    verbose: bool=False,
) -> None:
    """Plot node histories."""
    readpath = paths.fullpath(filedir)
    kwargs = parse_plot_kws(plot_kws or '')
    for quantity in quantities:
        if quantity == 'dqdt':
            plot_dqdt_terms(
                filedir=filedir,
                pattern=pattern,
                species=species,
                energy=energy,
            )
        else:
            filepath = readpath / f"{quantity}{pattern}.txt"
            plot_quantity_history(
                filepath=filepath,
                **kwargs
            )
    savename = f'{pattern}-{species}_{energy}MeV{pattern}.png'
    savepath = readpath / savename
    if verbose:
        print(f"Saving {savepath}")
    plt.savefig(savepath)
    plt.close()


def plot_quantity_history(
    filepath: pathlib.Path,
    **kwargs
) -> None:
    """Plot the node history of one or more observable quantities."""
    history = parse_node_history(filepath)
    info = history['info'].copy()
    plt.plot(history['time'], history['data'])
    plt.xscale(kwargs.get('xscale', 'linear'))
    plt.yscale(kwargs.get('yscale', 'linear'))
    plt.xlabel(f"Time [{info['time unit']}]")
    plt.ylabel(f"{info['data name']} [{info['data unit']}]")


def plot_dqdt_terms(
    readpath: pathlib.Path,
    pattern: str=None,
    species: str='H+',
    energy: float=0.0,
) -> None:
    """Read and plot acceleration terms at one node as functions of time."""
    names = [
        'rho',
        'bmag',
        'br', 'btheta', 'bphi',
        'vr', 'vtheta', 'vphi',
    ]
    arrays = {
        name: get_array(readpath / f"{name}{pattern}.txt")
        for name in names
    }
    parsed = parse_node_history(readpath / f"{names[0]}{pattern}.txt")
    time = 86400.0 * parsed['time']
    # TODO: Can we get species and energy from the header, thereby precluding
    # the need to pass them as arguments?
    s = atomic.species(species)
    e = physical.scalar(energy, unit='MeV')
    vpart = numpy.sqrt(2 * e.withunit('erg') / s.mass.withunit('g')) # -> cm/s
    groups = [
        {'filter': False, 'linestyle': 'dotted'},
        {'filter': True, 'linestyle': 'solid'},
    ]
    plt.figure(figsize=(10, 10))
    mosaic = [
        ['dQdt'],
        ['dQdt'],
        ['dQdt'],
        ['flux'],
        ['divV'],
        ['radius'],
    ]
    fig, axd = plt.subplot_mosaic(
        mosaic,
        sharex=True,
        figsize=(10, 10),
    )
    plt.sca(axd['dQdt'])
    time_scale = 24.0 / 86400.0
    plot_accel_terms(
        axd['dQdt'],
        time,
        vpart=vpart,
        **arrays,
        time_scale=time_scale,
        groups=groups,
    )
    plt.sca(axd['flux'])
    flux = get_array(readpath / f"flux{pattern}.txt")
    plot_flux(axd['flux'], time_scale * time, flux, scale=1.0)
    plt.sca(axd['divV'])
    plot_divV(axd['divV'], time, arrays['rho'], time_scale=time_scale)
    plt.sca(axd['radius'])
    radius = get_array(readpath / f"radius{pattern}.txt")
    plot_radius(axd['radius'], time_scale * time, radius=radius)
    plt.xlabel('Time [hours]', fontsize=16)


def get_array(path: pathlib.Path) -> numpy.typing.NDArray:
    """Get the data array from a node history."""
    history = parse_node_history(path)
    return history['data']


def parse_node_history(
    path: typing.Union[str, pathlib.Path]
) -> typing.Dict[str, typing.Union[numpy.typing.NDArray, dict]]:
    """Parse a text file containing a node history."""
    filepath = paths.fullpath(path)
    with filepath.open('r') as fp:
        header = fp.readline()
        time, data = numpy.loadtxt(fp, unpack=True)
    info = header.lstrip('#').rstrip('\n').split(';')
    result = {'time': time, 'data': data, 'info': {}}
    for entry in info:
        if entry:
            k, v = entry.split(':')
            result['info'][k.strip()] = v.strip()
    return result


def plot_accel_terms(
    ax: Axes,
    time: numpy.typing.NDArray,
    rho: numpy.typing.NDArray,
    bmag: numpy.typing.NDArray,
    vr: numpy.typing.NDArray,
    vtheta: numpy.typing.NDArray,
    vphi: numpy.typing.NDArray,
    br: numpy.typing.NDArray,
    btheta: numpy.typing.NDArray,
    bphi: numpy.typing.NDArray,
    vpart: numpy.typing.NDArray,
    time_scale: float=1.0,
    colors: typing.List[str]=None,
    groups: typing.Iterable[dict]=None,
    **plot_kw
) -> None:
    """Compute and plot acceleration terms as functions of time."""
    groups = groups or {}
    for group in groups:
        filter_on = group.get('filter', False)
        if filter_on:
            rho = smooth(rho)
            bmag = smooth(bmag)
        rho_b = rho / bmag
        dln_rho_dt = numpy.gradient(numpy.log(rho), time)
        dln_rho_b_dt = numpy.gradient(numpy.log(rho_b), time)
        dln_b_dt = numpy.gradient(numpy.log(bmag), time)
        vb = (br*vr + btheta*vtheta + bphi*vphi) / bmag
        dvb_dt = numpy.gradient(vb, time)

        sm = ' [smoothed]' if filter_on else ''
        quantities = {
            rf'$\ln({{n/B}})${sm}': dln_rho_b_dt,
            rf'$\ln({{B}})${sm}': dln_b_dt,
            rf'$\ln({{n/B}}) + \ln({{B}})${sm}': dln_rho_b_dt + dln_b_dt,
            # rf'$\ln({{n}})${sm}': dln_rho_dt,
            rf'$-\hat{{b}}\cdot\vec{{V}}/w${sm}': -dvb_dt / vpart,
        }
        colors = colors or [f'C{i}' for i in range(len(quantities))]
        if 'linestyle' in group:
            plot_kw['linestyle'] = group['linestyle']

        t = time * time_scale
        for color, (label, physics) in zip(colors, quantities.items()):
            plt.plot(t, physics, color=color, label=label, **plot_kw)

    plt.ylabel(r'$dQ/dt$ [$s^{-1}$]', fontsize=16)
    plt.legend(title='Q', loc='upper right', ncol=2)
    plt.ylim([-2e-3, +2e-3])
    plt.grid(which='major', axis='both', linewidth=2)
    plt.grid(which='minor', axis='both', linewidth=1)
    ax.xaxis.set_minor_locator(tck.MultipleLocator(0.25))
    ax.yaxis.set_minor_locator(tck.MultipleLocator(5))
    ax.ticklabel_format(scilimits=(0, 0))


def smooth(x) -> numpy.typing.NDArray:
    """Smooth x and set negative values to a small positive value."""
    xs = signal.savgol_filter(x, 11, 2)
    return numpy.where(xs > 0, xs, sys.float_info.min)


def plot_flux(
    ax: Axes,
    time: numpy.typing.NDArray,
    flux: numpy.typing.NDArray,
    scale: float=1.0,
) -> None:
    """Plot flux at this node as a function of time."""
    if scale != 1.0:
        tmp_str = f"{scale:e}"
        exp = int(tmp_str.split('e')[1])
        scale_str = fr' $\times$ $10^{{{exp}}}$'
    else:
        scale_str = ''
    label = fr'J(E){scale_str} [# / cm$^2$ s sr (MeV/nuc)]'
    plt.plot(time, flux * ERG_MEV * scale, 'k.', label=label)
    plt.legend(loc='upper right')
    plt.grid(which='major', axis='both', linewidth=2)
    plt.grid(which='minor', axis='both', linewidth=1)
    ax.yaxis.set_minor_locator(tck.MultipleLocator(1))


def plot_divV(
    ax: Axes,
    time: numpy.typing.NDArray,
    rho: numpy.typing.NDArray,
    time_scale: float=1.0,
) -> None:
    """Plot div(V) at this node as a function of time.
    
    Notes
    -----
    - div(V) = -dln(n)/dt from the convective (co-moving) continuity equation.
    """
    label = r"$-\frac{1}{3}\nabla\cdot\vec{V}$"
    divV = -numpy.gradient(numpy.log(rho), time)
    plt.plot(time_scale * time, -(1 / 3) * divV, 'g-', label=label)
    plt.ylim([-2e-4, 0])
    plt.legend(loc='lower right')
    plt.grid(which='major', axis='both', linewidth=2)
    plt.grid(which='minor', axis='both', linewidth=1)
    ax.yaxis.set_minor_locator(tck.MultipleLocator(1))
    ax.ticklabel_format(scilimits=(0, 0))


def plot_radius(
    ax: Axes,
    time: numpy.typing.NDArray,
    radius: numpy.typing.NDArray=None,
) -> None:
    """Plot the node radius as a function of time."""
    label = r'r [$R_\odot$]'
    plt.plot(time, radius / R_SUN, label=label)
    plt.ylim([0, 5])
    plt.legend(loc='lower right')
    plt.grid(which='major', axis='both', linewidth=2)
    plt.grid(which='minor', axis='both', linewidth=1)
    ax.yaxis.set_minor_locator(tck.MultipleLocator(1))


def plot_rtp(
    time: numpy.typing.NDArray,
    radius: numpy.typing.NDArray=None,
    theta: numpy.typing.NDArray=None,
    phi: numpy.typing.NDArray=None,
) -> mlines.Line2D:
    """Plot the node radius as a function of time."""
    lines = []
    if radius is not None:
        label = r'r [$R_\odot$]'
        lines.extend(plt.plot(time, radius / R_SUN, 'k--', label=label))
    if theta is not None:
        label = r'$\theta$'
        lines.extend(plt.plot(time, theta, 'r--', label=label))
    if phi is not None:
        label = r'$\phi$'
        lines.extend(plt.plot(time, phi, 'r', label=label))
    return lines


# CLI defaults:
# - step = 0
# - shell = 0
# - species = 'H+'
# - energy ['MeV'] = 0.0
