import argparse
import re
import typing
import sys

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import matplotlib.ticker as tck
import numpy
import numpy.typing
from scipy import signal

from eprempy import atomic
from eprempy import container
from eprempy import eprem
from eprempy import Observable
from eprempy import paths
from eprempy import physical


def main(
    quantities: typing.List[str],
    n: int,
    source: str,
    step: int,
    shell: int,
    species: str,
    energy: float,
    outdir: str,
    ylog: typing.Optional[typing.List[str]],
    verbose: bool,
) -> None:
    """Plot node histories."""
    stream = eprem.stream(n, source=source)
    if not quantities:
        raise ValueError("Nothing to plot") from None
    mosaic = [[quantity] for quantity in quantities]
    fig, axd = plt.subplot_mosaic(
        mosaic,
        sharex=True,
        figsize=(12, 3*len(quantities)),
    )
    times = stream['time'].withunit('hour')
    plt.xlabel(f'Time [{times.unit}]', fontsize=16)
    suptitle = create_suptitle(stream, step, shell, species, energy)
    plt.suptitle(suptitle, fontsize=20)
    for quantity in container.unique(quantities):
        ax = axd[quantity]
        if quantity.lower() == 'dqdt':
            plot_dqdt_history(
                ax=ax,
                stream=stream,
                times=times,
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
                times=times,
                step=step,
                shell=shell,
                species=species,
                energy=energy,
                ylog=ylog,
            )
    savename = (
        f"{stream.source.stem}-history"
        f"-{step}_{shell}_{species}_{energy}MeV"
        f".png"
        # NOTE: .with_suffix('.png') may clobber part of the energy string
    )
    savedir = paths.fullpath(outdir or '.')
    savedir.mkdir(exist_ok=True, parents=True)
    savepath = savedir / savename
    if verbose:
        print(f"Saving {savepath}")
    plt.savefig(savepath)
    plt.close()


def compute_yscales(
    ylog: typing.Optional[typing.List],
    quantities: typing.List[str],
) -> typing.Dict[str, str]:
    """Create a mapping from quantity name to y-axis scale type."""
    if ylog == []:
        return {quantity: 'log' for quantity in quantities}
    yscales = {quantity: 'linear' for quantity in quantities}
    for quantity in ylog or ():
        yscales[quantity] = 'log'
    return yscales


def create_suptitle(
    stream: eprem.Stream,
    step: int,
    shell: int,
    species: str,
    energy: float,
) -> str:
    """Create the plot super title."""
    r = stream['r'][step, shell].withunit('au')
    theta = stream['theta'][step, shell].withunit('deg')
    phi = stream['phi'][step, shell].withunit('deg')
    posstr = (
        r"$(r_0, \theta_0, \phi_0) = ($"
        f"{float(r):.1} {r.unit}, "
        f"{float(theta):.1f}"r"$^\circ$, "
        f"{float(phi):.1f}"r"$^\circ)$"
    )
    return f"{species} | {energy} MeV\n{posstr}"


RE = re.compile(r"(?P<name>.*)\s*\[(?P<unit>.*)\]")


def plot_quantity_history(
    ax: Axes,
    quantity: str,
    stream: eprem.Stream,
    times: physical.Array,
    step: int,
    shell: int,
    species: str,
    energy: float,
    ylog: typing.Optional[typing.List[str]],
) -> None:
    """Plot the node history of one or more observable quantities."""
    observable, name = get_observable(quantity, stream)
    array = compute_history(
        observable=observable,
        step=step,
        shell=shell,
        species=species,
        energy=energy,
    )
    ax.plot(times, array, 'k')
    if isinstance(ylog, list) and (not ylog or name in ylog):
        yscale = 'log'
    else:
        yscale = 'linear'
    ax.set_yscale(yscale)
    ax.grid(which='major', axis='both', linewidth=2)
    ax.grid(which='minor', axis='both', linewidth=1)
    ax.set_ylabel(
        f"{name}\n[{observable.unit.format('tex')}]",
        fontsize=16,
    )
    if yscale == 'linear':
        ax.ticklabel_format(axis='y', scilimits=(0, 0))


def get_observable(quantity: str, stream: eprem.Stream):
    """Create an observable quantity from `quantity`."""
    if all(c in quantity for c in '[]'):
        matched = RE.match(quantity)
        if not matched:
            raise ValueError(
                f"Cannot determine name and unit of {quantity!r}"
            ) from None
        parsed = matched.groupdict()
        name = parsed['name'].rstrip()
        return stream[name].withunit(parsed['unit']), name
    try:
        return stream[quantity], quantity
    except Exception as err:
        raise ValueError(
            f"Cannot determine observable quantity from {quantity!r}"
        ) from err


def plot_dqdt_history(
    ax: Axes,
    stream: eprem.Stream,
    times: physical.Array,
    step: int,
    shell: int,
    species: str,
    energy: float,
) -> None:
    """Plot terms from the FTE at one node as functions of time.

    This function plots acceleration terms from the focused transport equation
    (FTE) as functions of time. In the co-moving reference frame, FTE
    acceleration terms all have the form dQ/dt.
    """
    for (filter, linestyle) in zip((False, True), ('dotted', 'solid')):
        plot_fte_dqdt(
            ax=ax,
            stream=stream,
            times=times,
            step=step,
            shell=shell,
            species=species,
            energy=energy,
            filter=filter,
            linestyle=linestyle,
        )
    ax.set_ylabel(r"$dQ/dt$ ""\n"r"[$s^{-1}$]", fontsize=16)
    ax.legend(title='Q', loc='best', ncol=2, fontsize=16)
    ax.set_ylim([-2e-3, +2e-3])
    ax.grid(which='major', axis='both', linewidth=2)
    ax.grid(which='minor', axis='both', linewidth=1)
    ax.xaxis.set_minor_locator(tck.MultipleLocator(0.25))
    ax.ticklabel_format(axis='y', scilimits=(0, 0))


def plot_fte_dqdt(
    ax: Axes,
    stream: eprem.Stream,
    times: physical.Array,
    step: int,
    shell: int,
    species: str,
    energy: float,
    filter: bool,
    **kwargs
) -> None:
    """Compute and plot FTE acceleration terms as functions of time."""
    rho = compute_history(stream['rho'], step, shell, species, energy)
    br = compute_history(stream['br'], step, shell, species, energy)
    btheta = compute_history(stream['btheta'], step, shell, species, energy)
    bphi = compute_history(stream['bphi'], step, shell, species, energy)
    ur = compute_history(stream['ur'], step, shell, species, energy)
    utheta = compute_history(stream['utheta'], step, shell, species, energy)
    uphi = compute_history(stream['uphi'], step, shell, species, energy)
    s = atomic.species(species)
    e = physical.scalar(energy, unit='MeV')
    v = numpy.sqrt(2 * e.withunit('erg') / s.mass.withunit('g')) # -> cm/s
    t = numpy.array(times.withunit('s'))
    bmag = numpy.sqrt(br**2 + btheta**2 + bphi**2)
    if filter:
        rho = smooth(rho)
        bmag = smooth(bmag)
    rho_b = rho / bmag
    dln_n_dt = numpy.gradient(numpy.log(rho), t)
    dln_n_b_dt = numpy.gradient(numpy.log(rho_b), t)
    dln_b_dt = numpy.gradient(numpy.log(bmag), t)
    ub = (br*ur + btheta*utheta + bphi*uphi) / bmag
    dub_dt = numpy.gradient(ub, t)
    smstr = ' [smoothed]' if filter else ''
    quantities = {
        rf'$\ln({{n/B}})${smstr}': dln_n_b_dt,
        rf'$\ln({{B}})${smstr}': dln_b_dt,
        rf'$\ln({{n}})${smstr}': dln_n_dt,
        rf'$-\hat{{b}}\cdot\vec{{V}}/w${smstr}': -dub_dt / v,
    }
    colors = [f'C{i}' for i in range(len(quantities))]
    for color, (label, array) in zip(colors, quantities.items()):
        ax.plot(
            times,
            array,
            color=color,
            label=label,
            **kwargs,
        )


def compute_history(
    observable: Observable,
    step: int,
    shell: int,
    species: str,
    energy: float,
) -> numpy.typing.NDArray:
    """Compute the history of a named quantity on a certain node."""
    indices = [slice(None), slice(None)]
    if 'species' in observable.dimensions:
        indices.append(species)
    if any(s in observable.dimensions for s in ('energy', 'minimum energy')):
        indices.append((energy, 'MeV'))
    array = observable[*tuple(indices)]
    ntimes = array.shape[0]
    ts = zip(range(step, step+ntimes), range(shell, shell+ntimes))
    return numpy.squeeze([array[t-step, s-step, ...] for t, s in ts])


def smooth(x) -> numpy.typing.NDArray:
    """Smooth x and set negative values to a small positive value."""
    xs = signal.savgol_filter(x, 11, 2)
    return numpy.where(xs > 0, xs, sys.float_info.min)


epilog = \
"""
Observable quantities must include a name and may also include a unit. Each
quantity must be quoted unless it comprises only a name without whitespace. For
example, the following are valid arguments

    * mfp
    * "mfp [au]"
    * mean_free_path
    * "mean free path"
    * "mean free path [au]"
    etc.

while the following will cause an error

    * mfp [au]
    * mean free path [au]
    etc.

The caller may repeat a quantity to increase the vertical extent of the
corresponding panel. Note that repeating a quantity with a different unit will
produce a new panel.
"""
if __name__ == '__main__':
    p = argparse.ArgumentParser(
        description=main.__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog,
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
        '--ylog',
        help="log scale the y axis or all or some quantities",
        nargs='*',
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
