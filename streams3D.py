import abc
import argparse
import pathlib
from collections import Counter
import datetime
import textwrap
from types import SimpleNamespace
import typing
import sys

import numpy
import numpy.typing
import plotly.graph_objects as go
from plotly.basedatatypes import BaseTraceType
from plotly.subplots import make_subplots
from eprempy import eprem
from eprempy import quantity
from eprempy import paths

from support import numerics
from support import labels


class PanelElement(abc.ABC):
    """Abstract base class for panel elements"""

    @property
    @abc.abstractmethod
    def display_name() -> str:
        pass

    @abc.abstractmethod
    def render() -> BaseTraceType:
        pass


class Stream(PanelElement):
    """A class to render simulation streams."""

    @typing.overload
    def __init__(
        self,
        __id: int,
        config: typing.Optional[paths.PathLike]=None,
        source: typing.Optional[paths.PathLike]=None,
        time_step: int=0,
        distance_unit: typing.Optional[str]=None,
        marker: typing.Optional[dict]=None,
    ) -> None: ...

    @typing.overload
    def __init__(
        self,
        __id: int,
        stream: eprem.Stream,
        time_step: int=0,
        distance_unit: typing.Optional[str]=None,
        marker: typing.Optional[dict]=None,
    ) -> None: ...

    def __init__(
        self,
        __id: int,
        *args,
        time_step: int=0,
        distance_unit: typing.Optional[str]=None,
        marker: typing.Optional[dict]=None,
    ) -> None:
        self.interface = self._get_interface(__id, args)
        self._name = __id
        self.time_step = time_step
        self._distance_unit = distance_unit
        self._marker = marker
        self._r = None
        self._theta = None
        self._phi = None
        self._x = None
        self._y = None
        self._z = None
        self._text = None

    def _get_interface(self, __id, args):
        """Create or return a valid stream-observer interface."""
        if len(args) == 2:
            return eprem.stream(__id, *args)
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, eprem.Stream):
                return arg
            raise TypeError(arg)
        raise ValueError(args)

    @property
    def name(self) -> str:
        """The ID of this simulation stream."""
        return self._name

    @property
    def source(self) -> eprem.Stream:
        """The stream-observer data."""
        return self.interface.source.parent

    @property
    def distance_unit(self) -> str:
        """Units in which to express distances."""
        if self._distance_unit is None:
            self._distance_unit = 'Rs'
        return self._distance_unit

    @property
    def radial_scale(self) -> float:
        """The value by which to scale node radial distances."""
        return (
            eprem.BASETYPES['RSAU']['value']
            if self.distance_unit.lower() == 'rs' 
            else 1.0
        )

    @property
    def r(self) -> numpy.typing.NDArray:
        """The radial distance of each of this stream's nodes."""
        if self._r is None:
            observed = self.interface['r'][self.time_step, :]
            r = self.radial_scale * observed.withunit(self.distance_unit)
            self._r = r.squeezed
        return self._r

    @property
    def theta(self) -> numpy.typing.NDArray:
        """The polar angle of each of this stream's nodes."""
        if self._theta is None:
            observed = self.interface['theta'][self.time_step, :]
            self._theta = observed.squeezed
        return self._theta

    @property
    def phi(self) -> numpy.typing.NDArray:
        """The azimuthal angle of each of this stream's nodes."""
        if self._phi is None:
            observed = self.interface['phi'][self.time_step, :]
            self._phi = observed.squeezed
        return self._phi

    @property
    def x(self) -> numpy.typing.NDArray:
        """The Cartesian x coordinate of each of this stream's nodes."""
        if self._x is None:
            self._x = self.r * numpy.sin(self.theta) * numpy.cos(self.phi)
        return self._x

    @property
    def y(self) -> numpy.typing.NDArray:
        """The Cartesian y coordinate of each of this stream's nodes."""
        if self._y is None:
            self._y = self.r * numpy.sin(self.theta) * numpy.sin(self.phi)
        return self._y

    @property
    def z(self) -> numpy.typing.NDArray:
        """The Cartesian z coordinate of each of this stream's nodes."""
        if self._z is None:
            self._z = self.r * numpy.cos(self.theta)
        return self._z

    @property
    def text(self) -> list:
        """An informational string for each node."""
        return [
            f"r: {r:.6}<br>θ: {theta:.6}<br>φ: {phi:.6}"
            for (r, theta, phi) in zip(self.r, self.theta, self.phi)
        ]

    @property
    def marker(self) -> dict:
        """A dictionary of Plotly marker properties.
        
        See https://plotly.com/python/reference/scatter3d/  

        or

        https://plotly.github.io/plotly.py-docs/generated/plotly.graph_objects.scatter3d.html#plotly.graph_objects.scatter3d.Marker

        for more information.
        """
        if self._marker is None:
            self._marker = {}
        if specs := self._marker.pop('resize', {}):
            self.resize_marker(specs)
        return self._marker

    def resize_marker(self, specs: dict):
        """Resize the plot marker based on user specifications."""
        s0 = self._marker.get('size', 1.0)
        try:
            length = len(s0)
        except TypeError:
            length = -1
        sizes = s0 if length >= 0 else [s0] * len(self.r)
        if 'power' in specs:
            sizes = self._radial_resize(specs, sizes)
        if 'scale' in specs or 'cadence' in specs:
            sizes = self._periodic_resize(specs, sizes)
        self._marker['size'] = sizes
        if 'line' in self._marker:
            color = self._marker['line'].get('color', self._marker['color'])
            self._marker['line'].update({'color': color})
        else:
            self._marker['line'] = {'color': self._marker['color']}
        self._marker['sizemin'] = min(sizes)
        self._marker['sizemode'] = 'diameter'

    def _radial_resize(self, specs: dict, sizes: typing.Iterable):
        """Resize markers by radial distance from the solar surface."""
        power = specs['power']
        if power <= 0.0:
            return sizes
        r0 = self.r[0]
        scales = numpy.array(self.r / r0)**power
        return [size * scale for size, scale in zip(sizes, scales)]

    def _periodic_resize(self, specs: dict, sizes: typing.Iterable):
        """Resize every nth marker by a multiplicative factor."""
        n = specs.get('cadence', 1)
        scale = specs.get('scale', 2.0)
        return [
            size if i % n else size * scale
            for i, size in enumerate(sizes)
        ]

    @property
    def display_name(self) -> str:
        """The name to display when the user hovers over this stream."""
        return f"stream {self.name}"

    def render(self) -> go.Scatter3d:
        """Render this stream as a 3-D scatter trace."""
        return go.Scatter3d(
            x=self.x, y=self.y, z=self.z,
            mode='markers',
            marker=self.marker,
            name=self.display_name,
            text=self.text,
        )


class ObserverStream(Stream):
    """A class to manage observer streams."""
    def __init__(
        self,
        *args,
        mode: str=None,
        physics: dict=None,
        data_scale: str='linear',
        data_unit: str=None,
        **kwargs
    ) -> None:
        self.mode = mode
        self._physics = physics
        self.data_scale = data_scale
        self.data_unit = data_unit
        self._values = None
        self._text = None
        super().__init__(*args, **kwargs)

    @property
    def physics(self) -> dict:
        """Physical properties necessary, if any, to compute observations."""
        if self._physics is None:
            self._physics = {}
        return self._physics

    @property
    def values(self) -> numpy.typing.NDArray:
        """The value of the named observable, if any, at each node."""
        if self._values is None:
            self._values = self._observed_values if self.mode else []
        return self._values

    @property
    def _observed_values(self) -> numpy.typing.NDArray:
        """Values from an observerable."""
        x = self.interface[self.mode]
        this = x.withunit(self.data_unit) if self.data_unit else x
        observed = this[self.time_step, ...]
        values = numpy.array(numpy.squeeze(observed.data), ndmin=1)
        if self.data_scale == 'log':
            values[numpy.where(values == 0)] = sys.float_info.min
            values = numpy.log10(values)
        return values

    @property
    def color(self) -> typing.Union[str, numpy.ndarray]:
        """The color(s) of each node along this stream.

        This method will first check if the array of observed values contains a
        single value, which happens when the user requests a reduced observation
        (e.g., min, max, or mean of an observed quantity). If it finds a single
        value, it will return only that value (i.e., not the array) in order to
        force Plotly to use the same color for all markers. Otherwise, it will
        return the full array, which will cause Plotly to map array values to
        marker colors.
        """
        return self.values[0] if len(self.values) <= 1 else self.values

    @property
    def text(self) -> list:
        """An informational string for each node."""
        _coords = super().text
        if len(self.values) > 1:
            _values = [f"value: {float(v):.4E}" for v in self.values]
            self._text = [f"{c}<br>{v}" for c, v in zip(_coords, _values)]
        else:
            self._text = _coords
        return self._text

    def render(self) -> None:
        """Render this stream as a 3-D scatter trace."""
        self._marker['color'] = self.color
        self._marker['line']['width'] = 0
        return super().render()


class HighlightedStream(Stream):
    """A class to manage single-color highlighted streams."""
    def __init__(
        self,
        *args,
        color: str='blue',
        **kwargs
    ) -> None:
        self._marker['color'] = color
        super().__init__(*args, **kwargs)


class Sun(PanelElement):
    """A class to render the solar surface."""
    def __init__(
        self,
        name: str=None,
        surface_color: str='rgb(255, 255, 0)',
        background_color: str='darkgray',
        distance_unit: str=None,
        ntheta: int=51,
        nphi: int=51,
    ) -> None:
        self._name = name
        self.surface_color = surface_color
        self.background_color = background_color
        self._distance_unit = distance_unit
        self.ntheta = ntheta
        self.nphi = nphi

    @property
    def distance_unit(self) -> str:
        """Units in which to express distances."""
        if self._distance_unit is None:
            self._distance_unit = 'Rs'
        return self._distance_unit

    @property
    def radius(self) -> float:
        """The radius at which to render the solar surface."""
        return (
            1.0
            if self.distance_unit.lower() == 'rs'
            else eprem.BASETYPES['RSAU']['value']
        )

    @property
    def shell(self) -> typing.List[numpy.ndarray]:
        """The Cartesian coordinates of a spherical shell."""
        phi, theta = numpy.meshgrid(
            numpy.linspace(0, numpy.pi, 51),
            numpy.linspace(0, 2*numpy.pi, 51),
        )
        x = self.radius * numpy.sin(phi) * numpy.cos(theta)
        y = self.radius * numpy.sin(phi) * numpy.sin(theta)
        z = self.radius * numpy.cos(phi)
        return SimpleNamespace(x=x.flatten(), y=y.flatten(), z=z.flatten())

    @property
    def hoverlabel(self) -> dict:
        return {'bgcolor': self.background_color}

    @property
    def display_name(self) -> str:
        if self._name is None:
            self._name = 'solar surface'
        return self._name

    def render(self) -> go.Mesh3d:
        """Render a spherical surface to represent the Sun."""
        return go.Mesh3d(
            x=self.shell.x,
            y=self.shell.y,
            z=self.shell.z,
            alphahull=0,
            opacity=0.5,
            color=self.surface_color,
            name=self.display_name,
            hoverlabel=self.hoverlabel,
        )


class PanelPropertyError(Exception):
    """The named property is not a panel property."""

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"{self.name} is not a valid panel property"


class PanelProperties:
    """A class to manage a panel's graphics properties.
    
    The strategy of this class is to maintain a dict of known valid
    panel parameters which are effectively implied properties. When
    some part of the graphics code requests a property, this class
    will first search the properties explicitly defined here. If it
    doesn't find the named property, it will check the dictionary of
    implicit properties. If that also fails, it will raise
    ``PanelPropertyError``.
    """
    def __init__(self, **user):
        """Initialize user values and implied property names"""
        self.user = user.copy()
        self._default = {
            'axis_fontsize': 14,
            'axis_unit': None,
            'hide_axes': False,
            'eye_in_rtp': None,
        }
        self._all = {k: None for k in [*self._default, *self.user]}
        self.title = ''
        """The title to use for the associated panel."""

    def __getattribute__(self, name):
        return super(PanelProperties, self).__getattribute__(name)

    def __getattr__(self, name):
        if name not in self._all:
            raise PanelPropertyError(name)
        if self._all[name] is None:
            self._all[name] = self._find(name)
        return self._all[name]

    def __setattr__(self, name: str, value: typing.Any) -> None:
        super().__setattr__(name, value)

    def _find(self, name: str) -> typing.Any:
        user_value = self.user.get(name)
        if user_value is not None:
            return user_value
        default_value = self._default.get(name)
        if default_value is not None:
            return default_value

    @property
    def default_values(self) -> dict:
        return self._default.copy()

    @property
    def user_values(self) -> dict:
        return self.user

    @property
    def xaxis(self) -> dict:
        """Dictionary of x-axis parameters."""
        if self._all.get('xaxis_kws') is None:
            self._all['xaxis_kws'] = self._build_axis_kws('x')
        return self._all['xaxis_kws']

    @property
    def yaxis(self) -> dict:
        """Dictionary of y-axis parameters."""
        if self._all.get('yaxis_kws') is None:
            self._all['yaxis_kws'] = self._build_axis_kws('y')
        return self._all['yaxis_kws']

    @property
    def zaxis(self) -> dict:
        """Dictionary of z-axis parameters."""
        if self._all.get('zaxis_kws') is None:
            self._all['zaxis_kws'] = self._build_axis_kws('z')
        return self._all['zaxis_kws']

    def _build_axis_kws(self, symbol: str) -> dict:
        found = self.user.get(f'{symbol}axis_range') # may be None
        _range = found or self.user.get('axis_range')
        if self.user.get('hide_axes'):
            _title = ''
            showticklabels = False
        else:
            _title = (
                f'{symbol} [{self.axis_unit}]' if self.axis_unit
                else f'{symbol}'
            )
            showticklabels = True
        _ticksize = self.user.get(f'{symbol}axis_ticksize')
        return {
            'range': _range,
            'title': _title,
            'tickfont': {'size': _ticksize},
            'visible': True,
            'showticklabels': showticklabels,
            'ticks': 'outside',
            'backgroundcolor': "rgb(150, 150, 150)",
            'gridcolor': "white",
            'showbackground': True,
            'zerolinecolor': "white",
        }

    @property
    def camera(self) -> dict:
        """Dictionary of camera-view parameters."""
        if self._all.get('camera') is None:
            center = self.user.get('camera_center')
            if center is None:
                center = [0.0, 0.0, 0.0]
            eye = self.user.get('camera_eye')
            if eye is None:
                eye = [1.25, 1.25, 1.25]
            if self.user.get('eye_in_rtp'):
                eye = numerics.rtp2xyz(
                    eye[0], numpy.radians(eye[1]), numpy.radians(eye[2])
                )
            up = self.user.get('camera_up')
            if up is None:
                up = [0.0, 0.0, 1.0]
            xyz = ['x', 'y', 'z']
            self._all['camera'] = dict(
                center=dict(zip(xyz, center)),
                eye=dict(zip(xyz, eye)),
                up=dict(zip(xyz, up)),
            )
        return self._all['camera']


class Panel:
    """A class to render a figure panel."""
    def __init__(
        self,
        properties: typing.Union[dict, PanelProperties]=None,
    ) -> None:
        if isinstance(properties, PanelProperties):
            self.properties = properties
        elif properties is None:
            self.properties = PanelProperties()
        else:
            self.properties = PanelProperties(**properties)
        self._elements = None
        self._cmin = None
        self._cmid = None
        self._cmax = None
        self._traces = []

    def add_one(self, element) -> None:
        """Add a single element to this panel."""
        self.elements.append(element)

    def add_many(self, elements: typing.Iterable) -> None:
        """Add multiple elements to this panel at once."""
        self.elements.extend(elements)

    @property
    def elements(self) -> typing.List[PanelElement]:
        """The current list of this panel's elements."""
        if self._elements is None:
            self._elements = []
        return self._elements

    @property
    def traces(self) -> typing.List[BaseTraceType]:
        """A list of traces rendered from panel elements."""
        if self.observer_elements:
            self.set_global_colorscale()
        for element in self.elements:
            self._traces.append(element.render())
        return self._traces

    @property
    def observer_elements(self):
        """The elements to which the colorscale applies."""
        return [e for e in self.elements if isinstance(e, ObserverStream)]

    def global_value(self, name: str):
        """Return a global value for a named property if possible."""
        values = [e.marker.get(name) for e in self.observer_elements]
        unique = list(Counter(values))
        if len(unique) == 1:
            return unique[0]

    @property
    def cmin(self) -> float:
        """The global colorscale minimum, if any."""
        if self._cmin is None:
            self._cmin = self.global_value('cmin')
        return self._cmin

    @cmin.setter
    def cmin(self, value: float) -> None:
        """Set the global colorscale minimum."""
        self._cmin = value

    @property
    def cmid(self) -> float:
        """The global colorscale midpoint, if any."""
        if self._cmid is None:
            self._cmid = self.global_value('cmid')
        return self._cmid

    @cmid.setter
    def cmid(self, value: float) -> None:
        """Set the global colorscale midpoint."""
        self._cmid = value

    @property
    def cmax(self) -> float:
        """The global colorscale maximum, if any."""
        if self._cmax is None:
            self._cmax = self.global_value('cmax')
        return self._cmax

    @cmax.setter
    def cmax(self, value: float) -> None:
        """Set the global colorscale maximum, if any."""
        self._cmax = value

    def set_cmin_cmax(self) -> None:
        """Set the global colorscale minimum and maximum."""
        if self.cmin is None:
            self.cmin = numpy.min([e.values for e in self.observer_elements])
        if self.cmax is None:
            self.cmax = numpy.max([e.values for e in self.observer_elements])

    def set_markers(self) -> None:
        """Set global colorscale marker properties."""

    def set_global_colorscale(self) -> None:
        """Set this panel's colorscale.

        This occurs at the panel level because some display modes require
        coloring elements relative to each other.
        """
        if self.cmid is None:
            self.set_cmin_cmax()
        for element in self.observer_elements:
            element.marker['cmin'] = self.cmin
            element.marker['cmid'] = self.cmid
            element.marker['cmax'] = self.cmax


class _FigurePanel:
    """Internal interface to a single figure panel."""

    def __init__(self, panel: Panel, row: int, col: int) -> None:
        self._panel = panel
        self._row = row
        self._col = col

    @property
    def traces(self):
        """The traces in this panel."""
        return self._panel.traces

    @property
    def properties(self):
        """The properties on this panel."""
        return self._panel.properties

    @property
    def row(self):
        """This panel's row in the figure."""
        return self._row

    @property
    def col(self):
        """This panel's column in the figure."""
        return self._col


class Figure:
    """A class to render and save a streams figure."""
    def __init__(self) -> None:
        self._panels = None
        self.fig = None

    @property
    def panels(self) -> typing.List[_FigurePanel]:
        """The current list of panels to include in this figure."""
        if self._panels is None:
            self._panels = []
        return self._panels

    def add_panel(self, panel: Panel, row: int=1, col: int=1) -> None:
        """Add a single panel to this figure."""
        self.panels.append(_FigurePanel(panel, row, col))

    @property
    def nrows(self) -> int:
        """The current number of rows in this figure."""
        return len([panel.row for panel in self.panels])

    @property
    def ncols(self) -> int:
        """The current number of cols in this figure."""
        return len([panel.col for panel in self.panels])

    @property
    def titles(self) -> typing.List[str]:
        """The current list of user-supplied panel titles."""
        return [panel.properties.title for panel in self.panels]

    def _setup(self) -> go.Figure:
        """Set up the figure object."""
        return make_subplots(
            rows=self.nrows,
            cols=self.ncols,
            specs=[[{'is_3d': True}] * self.ncols] * self.nrows,
            subplot_titles=self.titles,
        )

    def _draw_panel_traces(self, panel: _FigurePanel) -> None:
        """Draw a panel's traces on the figure."""
        self.fig.add_traces(panel.traces, rows=panel.row, cols=panel.col)

    def _update_properties(self, panel: _FigurePanel, index: int=0) -> None:
        """Update the figure with this panel's properties."""
        scene = 'scene' if index == 0 else f'scene{index+1}'
        self.fig.layout[scene].xaxis = panel.properties.xaxis
        self.fig.layout[scene].yaxis = panel.properties.yaxis
        self.fig.layout[scene].zaxis = panel.properties.zaxis
        self.fig.layout[f'{scene}_camera'] = panel.properties.camera
        self.fig.layout[f'{scene}_aspectmode'] = 'cube'
        self.fig.update_layout(
            {'showlegend': False},
            font={'size': panel.properties.axis_fontsize},
        )

    def render(self) -> None:
        """Render all figure panels."""
        self.fig = self._setup()
        for index, panel in enumerate(self.panels):
            self._draw_panel_traces(panel)
            self._update_properties(panel, index)

    def save(
        self,
        path: pathlib.Path=None,
        show: bool=False,
        verbosity: int=0,
        **kwargs
    ) -> None:
        """Save and show this figure."""
        if show:
            self.fig.show()
        figpath = pathlib.Path(path or '.').expanduser().resolve()
        figpath.parent.mkdir(parents=True, exist_ok=True)
        _type = figpath.suffix
        if verbosity > 0:
            print(f"Saving {figpath}")
        if _type == '.html':
            self.fig.write_html(str(figpath), **kwargs)
        else:
            self.fig.write_image(str(figpath), **kwargs)


def single_panel_figure(**user):
    """Currently just an alias for ``main()``."""
    main(**user)


def main(**cli):
    """Create a figure of 3-D EPREM streams.

    This function uses input from the CLI to set up 3-D objects for the Sun,
    background streams (showing only stream position), and observer streams
    (showing position and a physical quantity). It adds those objects to
    individual figure panels, then combines those panels into a figure.
    """
    sun = Sun(
        surface_color=cli.get('sun_color'),
        distance_unit=cli.get('axis_unit'),
    )
    background_streams = create_background_streams(cli)
    mode = cli.get('mode')
    if not mode:
        foreground_streams = []
    elif mode == 'highlight':
        foreground_streams = create_highlighted_streams(cli)
    else:
        foreground_streams = create_observer_streams(cli)
    figure = Figure()
    properties = get_panel_properties(cli, background_streams[0].interface)
    panel = Panel(properties=properties)
    panel.add_one(sun)
    panel.add_many(background_streams)
    panel.add_many(foreground_streams)
    figure.add_panel(panel)
    figure.render()
    figure.save(
        path=build_figpath(cli),
        show=cli.get('show'),
        verbosity=cli.get('verbosity', 0),
    )


def build_figpath(cli: dict):
    """Get or create the destination path from user arguments."""
    # TODO: Handle
    # - figure name only
    # - figure directory only
    # - no `figpath` given
    if found := cli.get('figpath'):
        return pathlib.Path(found)
    datadir = pathlib.Path(cli['source'])
    now = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
    return datadir / f"streams3D_{now}.html"


def get_panel_properties(
    cli: dict,
    reference: eprem.Stream,
) -> PanelProperties:
    """Build a dictionary of user-specified panel properties."""
    properties = PanelProperties(**cli)
    properties.title = build_panel_title(cli, reference)
    return properties


def build_panel_title(
    cli: dict,
    reference: eprem.Stream,
) -> typing.Optional[str]:
    """Build a user-specified title."""
    if cli.get('hide_title'):
        return
    time_stamp = get_time_stamp(cli, reference)
    title = f"t = {time_stamp}"
    name = cli.get('mode')
    if not name:
        return title
    if energy := get_energy(cli):
        title += f"    E = {float(energy):.2f} MeV"
    unit = cli.get('unit') or reference[name].unit
    title += rf"    {name} [{unit}]"
    if cli.get('datascale') == 'log':
        title += " (log-scaled)"
    return title


def get_time_stamp(cli: dict, reference: eprem.Stream) -> str:
    """Get the time stamp of the user-requested time step."""
    time = labels.Time(
        reference['time'][:],
        start=cli.get('time_start'),
        offset=cli.get('time_offset'),
    )
    return time.stamps[cli.get('time_step', 0)]


def get_energy(cli: dict) -> float:
    """Get the energy closest to the user-requested value."""
    energy = cli.get('target_energy')
    # TODO: Allow user to include unit via CLI.
    if energy is None:
        return quantity.measurement(0.0, unit='MeV')
    return quantity.measure(float(energy), unit='MeV')


def create_background_streams(cli: dict):
    """Create a list of Stream elements for background streams."""
    source = cli.get('source')
    config = cli.get('config')
    time_step=cli.get('time_step')
    distance_unit=cli.get('axis_unit')
    marker=build_marker(cli, 'background')
    dataset = eprem.dataset(source=source, config=config)
    nstreams = len(dataset.streams)
    ids = parse_stream_ids(cli.get('stream_ids'), nstreams)
    return [
        Stream(
            i,
            config,
            source,
            time_step=time_step,
            distance_unit=distance_unit,
            marker=marker,
        ) for i in ids
    ]

def create_highlighted_streams(cli: dict):
    """Create a list of single-color Stream elements."""
    source = cli.get('source')
    config = cli.get('config')
    time_step=cli.get('time_step')
    distance_unit=cli.get('axis_unit')
    marker=build_marker(cli, 'highlighted')
    dataset = eprem.dataset(source=source, config=config)
    nstreams = len(dataset.streams)
    ids = parse_stream_ids(cli.get('active_ids'), nstreams)
    return [
        Stream(
            i,
            config,
            source,
            time_step=time_step,
            distance_unit=distance_unit,
            marker=marker,
        ) for i in ids
    ]


def create_observer_streams(cli: dict):
    """Create a list of Stream elements for active streams."""
    source = cli.get('source')
    config = cli.get('config')
    mode=cli.get('mode')
    time_step=cli.get('time_step', 0)
    distance_unit=cli.get('axis_unit')
    physics={
        'energy': [cli.get('target_energy', 0.0), 'MeV'],
    }
    data_scale=cli.get('datascale', 'linear')
    data_unit=cli.get('unit')
    marker=build_marker(cli, 'observer')
    dataset = eprem.dataset(source=source, config=config)
    nstreams = len(dataset.streams)
    user = cli.get('active_ids')
    if 'streams' in (user or {}):
        ids = parse_stream_ids(cli.get('stream_ids'), nstreams)
        ids.extend(parse_stream_ids(list(set(user) - {'streams'}), nstreams))
    else:
        ids = parse_stream_ids(user, nstreams)
    return [
        ObserverStream(
            i,
            config,
            source,
            mode=mode,
            time_step=time_step,
            distance_unit=distance_unit,
            physics=physics,
            data_scale=data_scale,
            data_unit=data_unit,
            marker=marker,
        ) for i in ids
    ]


def parse_stream_ids(ids: typing.Optional[typing.List[str]], maxlen: int):
    """Compute a list of stream-observer IDs from input."""
    if not ids:
        return []
    if len(ids) == 1:
        arg = ids[0]
        if isinstance(arg, str):
            if arg == 'all':
                return list(range(maxlen))
            if ':' in arg:
                if arg.startswith('::'):
                    start = 0
                    step = int(arg.lstrip('::'))
                    return list(range(int(start), maxlen, int(step)))
                start, rest = arg.split(':', 1)
                if ':' in rest:
                    stop, step = rest.split(':')
                    return list(range(int(start), int(stop), int(step)))
                return list(range(int(start), int(rest)))
    return [int(i) for i in ids]


def build_marker(cli: dict, style: str=None):
    """Build a dictionary of properties for the named marker style."""
    base = define_base_marker(cli)
    resize = {
        'cadence': cli.get('resize_every', 1),
        'scale': cli.get('resize_by', 2.0),
        'power': cli.get('resize_power', 0.0),
    }
    if style in {'background', 'observer', 'highlighted'}:
        category = (
            'active' if style in {'observer', 'highlighted'}
            else 'background'
        )
        resize_this = cli.get('resize') in ['all', category]
        updater = {
            'background': update_background_marker,
            'highlighted': update_highlighted_marker,
            'observer': update_observer_marker,
        }
        update = updater[style]
        return {
            **base,
            **update(cli),
            'resize': resize if resize_this else {},
        }
    return base


def define_base_marker(cli: dict):
    """Define the set of common marker attributes."""
    return {
        'size': cli.get('marker_size'),
        'color': 'black',
        'opacity': 0.2,
        'line': {},
    }


def update_background_marker(cli: dict):
    """Declare the set of attributes specific to background markers."""
    return {}


def update_highlighted_marker(cli: dict):
    """Declare the set of attributes specific to highlighted markers."""
    return {
        'color': cli.get('highlight_color'),
        'opacity': 1.0,
    }


def update_observer_marker(cli: dict):
    """Declare the set of attributes specific to observer markers."""
    return {
        'cmin': cli.get('cmin'),
        'cmax': cli.get('cmax'),
        'cmid': cli.get('cmid'),
        'colorscale': cli.get('colorscale'),
        'opacity': 1.0,
        'colorbar': {
            'len': 1.0,
            'lenmode': 'fraction',
            'exponentformat': 'power',
            'tickfont': {'size': cli.get('colorbar_fontsize')},
        },
        'showscale': bool(
            cli.get('colorscale') and not cli.get('no_colorbar')
        ),
    }


# TODO: Consider moving this to support/interfaces.py
class Parser(argparse.ArgumentParser):
    """An argument parser with custom file-line parsing."""

    def __init__(
        self,
        *args,
        wrap: int=0,
        ignore_missing_file: bool=False,
        **kwargs,
    ) -> None:
        """
        Parameters
        ----------
        *args
            Any positional arguments accepted by `argparse.ArgumentParser`.

        wrap : int, default=0
            The column at which to wrap lines of text. Setting `wrap` <= 0
            suppresses line wrapping.

        ignore_missing_file : bool, default=false
            If true, this will silently ignore a missing file name associated
            with the `fromfile_prefix_char` option. For example, this allows
            users to set the default name of a config file to "" in scripts. If
            false (the default), passing an empty file name will cause an error.

        **kwargs
            Any keyword arguments accepted by `argparse.ArgumentParser`.
        """
        self.wrap = max(wrap, 0)
        self.ignore_missing_file = ignore_missing_file
        kwargs['epilog'] = self._update_text(kwargs['epilog'])
        super().__init__(*args, **kwargs)

    def add_argument(self, *args, **kwargs):
        kwargs['help'] = self._update_text(kwargs['help'])
        return super().add_argument(*args, **kwargs)

    def _update_text(self, text: str) -> str:
        """Update a string of text based on state attributes."""
        if self.wrap:
            wrapped = textwrap.wrap(text, width=self.wrap)
            return '\n'.join(wrapped)
        return text

    def _read_args_from_files(
        self,
        arg_strings: typing.List[str],
    ) -> typing.List[str]:
        """Expand arguments referencing files.

        This overloads the argparse.ArgumentParser method to support the
        `ignore_missing_file` option (cf. `__init__`).
        """
        if self._removable_file(arg_strings):
            arg_strings = [
                s for s in arg_strings
                if s != self.fromfile_prefix_chars
            ]
        return super()._read_args_from_files(arg_strings)

    def _removable_file(self, arg_strings):
        return (
            self.fromfile_prefix_chars in arg_strings
            and self.ignore_missing_file
        )

    def convert_arg_line_to_args(self, arg_line: str):
        return arg_line.split()


if __name__ == "__main__":
    from support import interfaces
    p = Parser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
        fromfile_prefix_chars='@',
        epilog=(
            "You may also specify a file from which to read "
            "additional arguments by passing '@<filename>' "
            "(e.g., @config.ini). "
            "The parser will treat each line as if it had been "
            "directly passed via the command line."
        ),
        wrap=70,
        ignore_missing_file=True,
    )
    p.add_argument(
        '--source',
        help="directory containing EPREM output",
        default=pathlib.Path().cwd(),
    )
    p.add_argument(
        '--config',
        help="name of the EPREM configuration file",
    )
    p.add_argument(
        '--streams',
        dest='stream_ids',
        help="ID(s) of stream(s) to show",
        nargs='+',
        metavar=('ID0', 'ID1'),
        default=['all'],
    )
    p.add_argument(
        '--active-streams',
        dest='active_ids',
        help="stream(s) on which to show data",
        nargs='+',
        metavar=('ID0', 'ID1'),
    )
    p.add_argument(
        '--mode',
        help="analysis mode to run",
    )
    p.add_argument(
        '--energy',
        dest='target_energy',
        help="which energy in MeV (or closest value) to show",
        type=float,
        default=0.0,
    )
    p.add_argument(
        '--time-step',
        help="time step at which to plot data",
        type=int,
        default=0,
    )
    p.add_argument(
        '--time-start',
        help="UTC start date and time for time label",
        metavar=('YYYY-mm-dd HH:MM:SS'),
    )
    p.add_argument(
        '--time-offset',
        help="signed offset from 0.0 (in days) of simulation times",
        type=float,
        default=0.0,
    )
    p.add_argument(
        '--data-scale',
        dest="datascale",
        help="show the physical quantity on a linear or log scale",
        choices=('linear', 'log'),
        default='linear',
    )
    p.add_argument(
        '--unit',
        help="metric unit in which to show data",
    )
    p.add_argument(
        '--data-unit',
        dest="unit",
        help="alias for --unit",
    )
    p.add_argument(
        '--sun-color',
        help=( # TODO: Replace URL with something more concise
            "color of the sphere representing the Sun"
            ";\nsee https://plotly.github.io/plotly.py-docs/generated/plotly.graph_objects.scatter3d.html#plotly.graph_objects.scatter3d.Marker for examples of allowed colors"
        ),
        default='yellow',
    )
    p.add_argument(
        '--color-scale',
        dest="colorscale",
        help=(
            "name of a Plotly-supported color scale"
            ";\nsee https://plotly.com/python/builtin-colorscales/"
        ),
        default='viridis',
    )
    p.add_argument(
        '--no-colorbar',
        help="do not show the colorbar",
        action='store_true',
    )
    p.add_argument(
        '--colorbar-fontsize',
        help="font size of colorbar tick labels",
        type=float,
        default=14,
    )
    p.add_argument(
        '--min',
        dest="cmin",
        help="minimum data value on color scale",
        type=float,
    )
    p.add_argument(
        '--mid',
        dest="cmid",
        help="midpoint data value on color scale",
        type=float,
    )
    p.add_argument(
        '--max',
        dest="cmax",
        help="maximum data value on color scale",
        type=float,
    )
    p.add_argument(
        '--highlight-color',
        help="highlight active streams in the named color",
    )
    p.add_argument(
        '--xaxis-range',
        help=(
            "range spanned by the x axis"
            ";\nsee also: --axis-unit"
        ),
        nargs=2,
        type=float,
        metavar=('MIN', 'MAX'),
    )
    p.add_argument(
        '--yaxis-range',
        help=(
            "range spanned by the y axis"
            ";\nsee also: --axis-unit"
        ),
        nargs=2,
        type=float,
        metavar=('MIN', 'MAX'),
    )
    p.add_argument(
        '--zaxis-range',
        help=(
            "range spanned by the z axis"
            ";\nsee also: --axis-unit"
        ),
        nargs=2,
        type=float,
        metavar=('MIN', 'MAX'),
    )
    p.add_argument(
        '--axis-range',
        help=(
            "range spanned by the x, y, and z axes"
            ";\nsee also: --axis-unit, --{x,y,z}axis-range"
        ),
        nargs=2,
        type=float,
        metavar=('MIN', 'MAX'),
    )
    p.add_argument(
        '--axis-unit',
        help=(
            "show axes in solar radii (rs/RS/Rs)"
            " or astronomical units (au/AU/Au)"
            ";\ndefault: Rs"
        ),
        default='Rs',
    )
    p.add_argument(
        '--axis-fontsize',
        help="font size for all axes",
        type=float,
    )
    p.add_argument(
        '--hide-axes',
        help="hide titles and tick labels on all axes",
        action='store_true',
    )
    p.add_argument(
        '--hide-title',
        help="hide the panel title(s)",
        action='store_true',
    )
    p.add_argument(
        '--camera-center',
        help=(
            "point at the center of the view"
            ";\nsee https://plotly.com/python/3d-camera-controls/"
        ),
        nargs=3,
        type=float,
        metavar=('x', 'y', 'z'),
    )
    p.add_argument(
        '--camera-eye',
        help=(
            "position of the camera"
            ";\nmay be either Cartesian or spherical coordinates"
            ";\nenter spherical angles in degrees"
            ";\nsee https://plotly.com/python/3d-camera-controls/"
        ),
        nargs=3,
        type=float,
        metavar=('x (or r)', 'y (or θ)', 'z (or φ)'),
    )
    p.add_argument(
        '--camera-up',
        help=(
            "direction to consider 'up' for camera positioning"
            ";\nsee https://plotly.com/python/3d-camera-controls/"
        ),
        nargs=3,
        type=float,
        metavar=('x', 'y', 'z'),
    )
    p.add_argument(
        '--eye-in-rtp',
        help="coordinates of CAMERA_EYE are in (r, θ, φ)",
        action='store_true',
    )
    p.add_argument(
        '--marker-size',
        help="size of all node markers in pixels",
        type=float,
        default=1.0,
    )
    p.add_argument(
        '--resize',
        help=(
            "which marker types to resize ('none' to suppress)"
            "; see also RESIZE_EVERY and RESIZE_BY"
        ),
        choices=('background', 'active', 'all', 'none'),
        default='none',
    )
    p.add_argument(
        '--resize-every',
        help=(
            "cadence at which to resize active markers"
            "; use with RESIZE"
        ),
        type=int,
        default=1,
    )
    p.add_argument(
        '--resize-by',
        help=(
            "amount by which to resize markers, relative to marker_size"
            "; use with RESIZE"
        ),
        type=float,
        default=2.0,
    )
    p.add_argument(
        '--resize-power',
        help="power-law index for radially resizing markers",
        type=float,
        default=0.0,
    )
    p.add_argument(
        '--show',
        help="show the figure",
        action='store_true',
    )
    p.add_argument(
        '--figpath',
        help=(
            "full path to which to save figure"
            ";\nfile types other than html require orca: "
            "https://github.com/plotly/orca"
        ),
    )
    p.add_argument(
        '--write-image-kw',
        help=(
            "keyword(s) to pass to Plotly write_image()"
            ";\nsee manual entry for plotly.io.write_image"
        ),
        nargs='*',
        action=interfaces.StoreKeyValuePair,
    )
    p.add_argument(
        '-v',
        '--verbose',
        dest='verbosity',
        help=(
            "print runtime messages"
            ";\npass multiple times to increase verbosity"
        ),
        action='count',
    )
    args = p.parse_args()
    main(**vars(args))
