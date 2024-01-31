import argparse
import typing
import sys

import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.axes import Axes
import  matplotlib.ticker as tck
import numpy
import numpy.typing
from scipy import signal

from eprempy import atomic
from eprempy import eprem
from eprempy import paths
from eprempy import physical
from eprempy import universal
from tools.graphics import parse_plot_kws

ERG_MEV = 1e6 * universal.CGS['eV'].asscalar
R_SUN = 6.96e10


def main(
    quantities: typing.List[str],
    n: int,
    source: str,
    step: int,
    shell: int,
    species: str,
    energy: float,
    kwargs_str: str,
    outdir: str,
    verbose: bool,
) -> None:
    """Plot node histories."""
    kwargs = parse_plot_kws(kwargs_str or '')
    stream = eprem.stream(n, source=source)
    mosaic = []
    for quantity in quantities:
        if quantity.lower() == 'dqdt':
            mosaic.extend([[quantity]]*3)
        else:
            mosaic.append([quantity])
    fig, axd = plt.subplot_mosaic(
        mosaic,
        sharex=True,
        figsize=(10, 10),
    )
    plt.xlabel('Time', fontsize=16)
    for quantity in quantities:
        ax = axd[quantity]
        if quantity.lower() == 'dqdt':
            plot_dqdt_terms(
                ax=ax,
                stream=stream,
                step=step,
                shell=shell,
                species=species,
                energy=energy,
            )
        else:
            plot_quantity_history(
                ax=ax,
                quantity=quantity,
                stream=stream,
                step=step,
                shell=shell,
                species=species,
                energy=energy,
                **kwargs
            )
    savename = f'history-{step}_{shell}_{species}_{energy}MeV.png'
    savedir = paths.fullpath(outdir or '.')
    savedir.mkdir(exist_ok=True, parents=True)
    savepath = savedir / savename
    if verbose:
        print(f"Saving {savepath}")
    plt.savefig(savepath)
    plt.close()


PLOT_KWS = {
    'rho': {'yscale': 'log'},
    'flux': {'yscale': 'log'},
    'acceleration rate': {'yscale': 'log'},
}

def plot_quantity_history(
    ax: Axes,
    quantity: str,
    stream: eprem.Stream,
    step: int,
    shell: int,
    species: str,
    energy: float,
) -> None:
    """Plot the node history of one or more observable quantities."""
    time = numpy.array(stream.times)
    array = compute_history(
        quantity=quantity,
        stream=stream,
        step=step,
        shell=shell,
        species=species,
        energy=energy,
    )
    ax.plot(time, array, color='black', label=quantity)
    ax.set_yscale(PLOT_KWS.get('yscale', 'linear'))
    # ax.legend(loc='lower right')
    ax.grid(which='major', axis='both', linewidth=2)
    ax.grid(which='minor', axis='both', linewidth=1)
    # ax.yaxis.set_minor_locator(tck.MultipleLocator(1))
    ax.set_ylabel(f"{quantity}")


def plot_dqdt_terms(
    ax: Axes,
    stream: eprem.Stream,
    step: int,
    shell: int,
    species: str,
    energy: float,
) -> None:
    """Read and plot acceleration terms at one node as functions of time."""
    for (filter, linestyle) in zip((False, True), ('dotted', 'solid')):
        plot_accel_terms(
            ax=ax,
            stream=stream,
            step=step,
            shell=shell,
            species=species,
            energy=energy,
            filter=filter,
            linestyle=linestyle,
        )
    ax.set_ylabel(r'$dQ/dt$ [$s^{-1}$]', fontsize=16)
    ax.legend(title='Q', loc='upper right', ncol=2)
    ax.set_ylim([-2e-3, +2e-3])
    ax.grid(which='major', axis='both', linewidth=2)
    ax.grid(which='minor', axis='both', linewidth=1)
    # ax.xaxis.set_minor_locator(tck.MultipleLocator(0.25))
    # ax.yaxis.set_minor_locator(tck.MultipleLocator(5))
    ax.ticklabel_format(scilimits=(0, 0))


def plot_accel_terms(
    ax: Axes,
    stream: eprem.Stream,
    step: int,
    shell: int,
    species: str,
    energy: float,
    filter: bool,
    **kwargs
) -> None:
    """Compute and plot acceleration terms as functions of time."""
    rho = compute_history('rho', stream, step, shell, species, energy)
    br = compute_history('br', stream, step, shell, species, energy)
    btheta = compute_history('btheta', stream, step, shell, species, energy)
    bphi = compute_history('bphi', stream, step, shell, species, energy)
    ur = compute_history('ur', stream, step, shell, species, energy)
    utheta = compute_history('utheta', stream, step, shell, species, energy)
    uphi = compute_history('uphi', stream, step, shell, species, energy)
    s = atomic.species(species)
    e = physical.scalar(energy, unit='MeV')
    v = numpy.sqrt(2 * e.withunit('erg') / s.mass.withunit('g')) # -> cm/s
    time = numpy.array(stream['time'])
    bmag = numpy.sqrt(br**2 + btheta**2 + bphi**2)
    if filter:
        rho = smooth(rho)
        bmag = smooth(bmag)
    rho_b = rho / bmag
    dln_rho_dt = numpy.gradient(numpy.log(rho), time)
    dln_rho_b_dt = numpy.gradient(numpy.log(rho_b), time)
    dln_b_dt = numpy.gradient(numpy.log(bmag), time)
    ub = (br*ur + btheta*utheta + bphi*uphi) / bmag
    dub_dt = numpy.gradient(ub, time)
    smstr = ' [smoothed]' if filter else ''
    quantities = {
        rf'$\ln({{n/B}})${smstr}': dln_rho_b_dt,
        rf'$\ln({{B}})${smstr}': dln_b_dt,
        rf'$\ln({{n/B}}) + \ln({{B}})${smstr}': dln_rho_b_dt + dln_b_dt,
        # rf'$\ln({{n}})${smstr}': dln_rho_dt,
        rf'$-\hat{{b}}\cdot\vec{{V}}/w${smstr}': -dub_dt / v,
    }
    colors = [f'C{i}' for i in range(len(quantities))]
    for color, (label, array) in zip(colors, quantities.items()):
        ax.plot(time, array, color=color, label=label, **kwargs)


# TODO: Consider passing in `times` and `observable` instead of `quantity` and
# `stream`.
def compute_history(
    quantity: str,
    stream: eprem.Stream,
    step: int,
    shell: int,
    species: str,
    energy: float,
) -> numpy.typing.NDArray:
    """Compute the history of a named quantity on a certain node."""
    observable = stream[quantity]
    indices = [slice(None), slice(None)]
    if 'species' in observable.dimensions:
        indices.append(species)
    if 'energy' in observable.dimensions:
        indices.append((energy, 'MeV'))
    array = observable[*tuple(indices)]
    times = stream.times.withunit('day')
    ntimes = len(times)
    ts = zip(range(step, step+ntimes), range(shell, shell+ntimes))
    return numpy.squeeze([array[t-step, s-step, ...] for t, s in ts])


def smooth(x) -> numpy.typing.NDArray:
    """Smooth x and set negative values to a small positive value."""
    xs = signal.savgol_filter(x, 11, 2)
    return numpy.where(xs > 0, xs, sys.float_info.min)


if __name__ == '__main__':
    p = argparse.ArgumentParser(
        description=main.__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        'quantities',
        help="observable quantities to plot; may include 'dQdt'",
        nargs='*',
    )
    p.add_argument(
        '--stream',
        dest='n',
        help="the stream number to use",
        type=int,
        default=0,
    )
    p.add_argument(
        '--timestep',
        dest='step',
        help="the time step (0-based) at which to identify the target node",
        type=int,
        default=0,
    )
    p.add_argument(
        '--shell',
        help="the shell (0-based) on which to identify the target node",
        type=int,
        default=0,
    )
    p.add_argument(
        '--species',
        help="the target atomic species, if applicable (default: H+)",
        default='H+',
    )
    p.add_argument(
        '--energy',
        help="the target energy (in MeV), if applicable (default: 0.0)",
        type=float,
        default=0.0,
    )
    p.add_argument(
        '--plot_kws',
        dest='kwargs_str',
        help=(
            "key-value pairs to pass to plotting routines"
            "\nPass multiple comma-separated key-value pairs"
            " as a single quoted string"
        ),
    )
    p.add_argument(
        '-i', '--indir',
        dest='source',
        help="the directory containing the EPREM output (default: ./)",
    )
    p.add_argument(
        '-o', '--outdir',
        help="the directory in which to save the plot (default: ./)",
    )
    p.add_argument(
        '-v', '--verbose',
        help="print runtime messages",
        action='store_true',
    )
    args = p.parse_args()
    main(**vars(args))
