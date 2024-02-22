import sys
import typing

import numpy


class MissingArgsError(Exception):
    pass


class ArgsNumberError(Exception):
    pass


def xyz2rtp(*args):
    """Convert (x, y, z) to (r, θ, φ).

    This function treats θ as the polar angle and φ as the azimuthal angle.

    Positional Parameters
    ---------------------
    args : ``int``s or ``tuple`` of ``int``s
    
    The x, y, and z values to convert. The user may either pass individual values or a three-tuple of values.

    Returns
    -------
    ``tuple``
    
    A tuple containing the computed r, θ, and φ values.

    Examples
    --------
    ```
    >>> from goats.core.numerical import xyz2rtp
    >>> xyz2rtp(1.0, 0.0, 0.0)
    (1.0, 1.5707963267948966, 0.0)
    >>> xyz2rtp(0.0, 0.0, 1.0)
    (1.0, 0.0, 0.0)
    >>> xyz = (0.0, 0.0, 1.0)
    >>> xyz2rtp(xyz)
    (1.0, 0.0, 0.0)
    ```
    """

    if not args:
        raise MissingArgsError
    elif len(args) == 1:
        x, y, z = args[0]
    elif len(args) == 3:
        x, y, z = args
    else:
        raise ArgsNumberError
    r = numpy.sqrt(x*x + y*y + z*z)
    r[numpy.asarray(numpy.abs(r) < sys.float_info.epsilon).nonzero()] = 0.0
    t = numpy.arccos(z/r)
    t[numpy.asarray(r == 0).nonzero()] = 0.0
    p = numpy.arctan2(y, x)
    p[numpy.asarray(p < 0.0).nonzero()] += 2*numpy.pi
    p[numpy.asarray(
        [i == 0 and j >= 0 for (i, j) in zip(x, y)]
    ).nonzero()] = +0.5*numpy.pi
    p[numpy.asarray(
        [i == 0 and j < 0  for (i, j) in zip(x, y)]
    ).nonzero()] = -0.5*numpy.pi
    return (r, t, p)


def rtp2xyz(*args):
    """Convert (r, θ, φ) to (x, y, z).

    This function treats θ as the polar angle and φ as the azimuthal angle.

    Positional Parameters
    ---------------------
    args : ``int``s or ``tuple`` of ``int``s

    The r, θ, and φ values to convert. The user may either pass individual values or a three-tuple of values.

    Returns
    -------
    ``tuple``

    A tuple containing the computed x, y, and z values.

    Examples
    --------
    ```
    >>> from goats.core.numerical rtp2xyz
    >>> import numpy
    >>> rtp2xyz(1.0, 0.5*numpy.pi, 0)
    (1.0, 0.0, 0.0)
    >>> rtp2xyz(1.0, 0, 0.5*numpy.pi)
    (0.0, 0.0, 1.0)
    >>> rtp = (1.0, 0, 0.5*numpy.pi)
    >>> rtp2xyz(rtp)
    (0.0, 0.0, 1.0)
    ```
    """

    if not args:
        raise MissingArgsError
    elif len(args) == 1:
        r, t, p = args[0]
    elif len(args) == 3:
        r, t, p = args
    else:
        raise ArgsNumberError
    x = r * numpy.sin(t) * numpy.cos(p)
    x = zero_floor(x)
    y = r * numpy.sin(t) * numpy.sin(p)
    y = zero_floor(y)
    z = r * numpy.cos(t)
    z = zero_floor(z)
    return (x, y, z)


def zero_floor(
    value: typing.Union[float, numpy.ndarray],
) -> typing.Union[float, numpy.ndarray]:
    """Round a small number, or array of small numbers, to zero."""
    if value.shape:
        condition = numpy.asarray(
            numpy.abs(value) < sys.float_info.epsilon
        ).nonzero()
        value[condition] = 0.0
    else:
        value = 0.0 if numpy.abs(value) < sys.float_info.epsilon else value
    return value


