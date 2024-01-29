import argparse
import pathlib
import sys
import typing

import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.legend import Legend
import  matplotlib.ticker as tck
import numpy
import numpy.typing
from scipy import signal

from eprempy import paths
from eprempy import physical
from eprempy import atomic
from eprempy import universal
import node


ERG_MEV = 1e6 * universal.CGS['eV']
R_SUN = 6.96e10

def smooth(x) -> numpy.typing.NDArray:
    """Smooth x and set negative values to a small positive value."""
    xs = signal.savgol_filter(x, 11, 2)
    return numpy.where(xs > 0, xs, sys.float_info.min)


def main(
    filedir: str=None,
    pattern: str=None,
    species: str='H+',
    energy: float=0.0,
    title: str=None,
    verbose: bool=False,
) -> None:
    """Read and plot acceleration terms at one node as functions of time."""
    readpath = paths.fullpath(filedir)
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
    parsed = node.parse_history(readpath / f"{names[0]}{pattern}.txt")
    time = 86400.0 * parsed['time']
    s = atomic.species(species)
    e = physical.scalar(energy, unit='MeV')
    vpart = numpy.sqrt(2 * e.withunit('erg') / s.mass.withunit('g')) # -> cm/s
    groups = [
        {'filter': False, 'linestyle': 'dotted'},
        {'filter': True, 'linestyle': 'solid'},
    ]
    plt.figure(figsize=(10, 10))
    plt.title(title)
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
        time,
        vpart=vpart,
        **arrays,
        time_scale=time_scale,
        groups=groups,
    )
    plt.ylim([-2e-3, +2e-3])
    plt.grid(which='major', axis='both', linewidth=2)
    plt.grid(which='minor', axis='both', linewidth=1)
    axd['dQdt'].xaxis.set_minor_locator(tck.MultipleLocator(0.25))
    axd['dQdt'].yaxis.set_minor_locator(tck.MultipleLocator(5))
    axd['dQdt'].ticklabel_format(scilimits=(0, 0))

    plt.sca(axd['flux'])
    flux = get_array(readpath / f"flux{pattern}.txt")
    plot_flux(time_scale * time, flux, scale=1.0)
    plt.legend(loc='upper right')
    plt.grid(which='major', axis='both', linewidth=2)
    plt.grid(which='minor', axis='both', linewidth=1)
    axd['flux'].yaxis.set_minor_locator(tck.MultipleLocator(1))

    plt.sca(axd['divV'])
    plot_divV(time, arrays['rho'], time_scale=time_scale)
    plt.ylim([-2e-4, 0])
    plt.legend(loc='lower right')
    plt.grid(which='major', axis='both', linewidth=2)
    plt.grid(which='minor', axis='both', linewidth=1)
    axd['divV'].yaxis.set_minor_locator(tck.MultipleLocator(1))
    axd['divV'].ticklabel_format(scilimits=(0, 0))

    plt.sca(axd['radius'])
    radius = get_array(readpath / f"radius{pattern}.txt")
    plot_rtp(time_scale * time, radius=radius)
    plt.ylim([0, 5])
    plt.legend(loc='lower right')
    plt.grid(which='major', axis='both', linewidth=2)
    plt.grid(which='minor', axis='both', linewidth=1)
    axd['radius'].yaxis.set_minor_locator(tck.MultipleLocator(1))

    plt.xlabel('Time [hours]', fontsize=16)
    savename = f'accel_terms-{species}_{energy}MeV{pattern}.png'
    savepath = readpath / savename
    if verbose:
        print(f"Saving {savepath}")
    plt.savefig(savepath)


def get_array(path: pathlib.Path) -> numpy.typing.NDArray:
    """Get the data array from a node history."""
    history = node.parse_history(path)
    return history['data']


def plot_accel_terms(
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
) -> Legend:
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
    return plt.legend(title='Q', loc='upper right', ncol=2)


def plot_reference(
    readpath: pathlib.Path,
    pattern: str,
    time: numpy.typing.NDArray,
    quantities: typing.Iterable[str],
    rho: numpy.typing.NDArray=None,
    degrees: bool=False,
    time_scale: float=1.0,
    flux_scale: float=1.0,
) -> typing.Optional[Legend]:
    """Plot reference quantities."""
    quantities = list(quantities)
    handles = []
    if 'flux' in quantities:
        flux = get_array(readpath / f"flux{pattern}.txt")
        handles.extend(
            plot_flux(time_scale * time, flux, scale=flux_scale)
        )
    if 'divV' in quantities:
        handles.extend(plot_divV(time, rho, time_scale=time_scale))
    rtp = ['r', 'theta', 'phi']
    if 'rtp' in quantities:
        quantities.extend(rtp)
    radius = (
        get_array(readpath / f"radius{pattern}.txt")
        if 'r' in quantities
        else None
    )
    theta = (
        get_angle('theta', readpath, pattern, degrees=degrees)
        if 'theta' in quantities
        else None
    )
    phi = (
        get_angle('phi', readpath, pattern, degrees=degrees)
        if 'phi' in quantities
        else None
    )
    if any(q in quantities for q in rtp):
        handles.extend(
            plot_rtp(
                time_scale * time,
                radius=radius,
                theta=theta,
                phi=phi,
            )
        )
    if handles:
        return plt.legend(handles=handles, loc='upper right')


def get_angle(
    name: str,
    readpath: pathlib.Path,
    pattern: str,
    degrees: bool=False,
) -> numpy.typing.NDArray:
    """Get the theta or phi coordinate."""
    angle = get_array(readpath / f"{name}{pattern}.txt")
    if degrees:
        angle = numpy.degrees(angle)
    return angle


def plot_flux(
    time: numpy.typing.NDArray,
    flux: numpy.typing.NDArray,
    scale: float=1.0,
) -> mlines.Line2D:
    """Plot flux at this node as a function of time."""
    if scale != 1.0:
        tmp_str = f"{scale:e}"
        exp = int(tmp_str.split('e')[1])
        scale_str = fr' $\times$ $10^{{{exp}}}$'
    else:
        scale_str = ''
    label = fr'J(E){scale_str} [# / cm$^2$ s sr (MeV/nuc)]'
    return plt.plot(time, flux * ERG_MEV * scale, 'k.', label=label)


def plot_divV(
    time: numpy.typing.NDArray,
    rho: numpy.typing.NDArray,
    time_scale: float=1.0,
) -> mlines.Line2D:
    """Plot div(V) at this node as a function of time.
    
    Notes
    -----
    - div(V) = -dln(n)/dt from the convective (co-moving) continuity equation.
    """
    label = r"$-\frac{1}{3}\nabla\cdot\vec{V}$"
    divV = -numpy.gradient(numpy.log(rho), time)
    return plt.plot(time_scale * time, -(1 / 3) * divV, 'g-', label=label)


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


if __name__ == '__main__':
    p = argparse.ArgumentParser(
        description=main.__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        '-i',
        '--filedir',
        help=(
            "Location of node-history text files"
            " (default: current directory)"
        )
    )
    p.add_argument(
        '-p',
        '--pattern',
        help="Common file-name pattern (default: '')",
    )
    p.add_argument(
        '--species',
        help="The species (symbol) of particles to plot (default: H+)",
        default='H+',
    )
    p.add_argument(
        '--energy',
        help="The energy (in MeV) of particles to plot (default: 0.0)",
        type=float,
        default=0.0,
    )
    p.add_argument(
        '--title',
        help="A title for the plot (default: no title)",
    )
    p.add_argument(
        '-v',
        '--verbose',
        help="Print runtime messages",
        action='store_true',
    )
    args = p.parse_args()
    main(**vars(args))
