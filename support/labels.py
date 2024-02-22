import datetime
import typing

import numpy

from eprempy import eprem


class Date:
    """A class to handle dates."""
    def __init__(self, string: str) -> None:
        self.string = string
        self._date = None

    @property
    def date(self) -> str:
        """The date in YYYY-MM-DD format."""
        if self._date is None:
            self._date = datetime.datetime.strptime(
                self.string, '%Y-%m-%d %H:%M:%S'
            ).strftime('%Y-%m-%d')
        return self._date

    def __str__(self) -> str:
        return self.string


class Time:
    """A class to manage operations on simulation time."""
    def __init__(
        self,
        reference: eprem.Stream,
        start: str=None,
        offset: float=0.0,
    ) -> None:
        self.reference = reference
        self._start = start
        self.offset = offset
        self._date = None
        self._days = None
        self._hours = None
        self._minutes = None
        self._seconds = None
        self._stamps = None

    @property
    def date(self) -> str:
        """The starting date, if available, in YYYY-MM-DD format."""
        if self._date is None:
            self._date = datetime.datetime.strptime(
                self.start, '%Y-%m-%d %H:%M:%S'
            ).strftime('%Y-%m-%d')
        return self._date

    @property
    def start(self) -> Date:
        """The simulation event start, if available."""
        if self._start is not None:
            return Date(self._start)

    @property
    def days(self) -> numpy.ndarray:
        """An array of floating-point days for this simulation run."""
        if self._days is None:
            self._days = self.reference['time'][:].withunit('day').squeezed
        return self._days

    @property
    def stamps(self) -> typing.List[str]:
        """The UTC time stamp of each time step."""
        if self._stamps is None:
            self._stamps = [
                self._get_time_stamp(float(day))
                for day in self.days
            ]
        return self._stamps

    def _get_time_stamp(self, day: float) -> str:
        """Get the single time stamp for a given simulation time."""
        if self.start is not None:
            return self._get_full_time_stamp(day)
        return self._get_partial_time_stamp(day)

    def _get_full_time_stamp(self, day: float) -> str:
        """Build the full UTC time stamp for this day."""
        start = datetime.datetime.strptime(str(self.start), '%Y-%m-%d %H:%M:%S')
        start_day = datetime.datetime(
            year=start.year,
            month=start.month,
            day=start.day,
        )
        delta = (start - start_day) / datetime.timedelta(days=1)
        dhms = self._get_hhmmss(day + delta)
        d, h, m ,s = split_dhms(dhms)
        result = start_day + datetime.timedelta(
            days=d, hours=h, minutes=m, seconds=s
        )
        return str(result)

    def _get_partial_time_stamp(self, day: float) -> str:
        """Build the HH:MM:SS time stamp for this day."""
        _hhmmss = self._get_hhmmss(day)
        hhmmss = format_elapsed_time(_hhmmss)
        return f'{hhmmss}'

    def _get_hhmmss(self, day: float) -> str:
        """Convert a simulation time into an HH:MM:SS time stamp."""
        current = datetime.timedelta(days=day)
        delta = current + datetime.timedelta(days=self.offset)
        return str(delta)


def format_elapsed_time(time: str) -> str:
    """Convert a string time to HH:MM:SS format.

    This function will account for full days by adding 24 hours before
    converting to HH:MM:SS format.
    """
    d, h, m, s = split_dhms(time)
    h += 24 * d
    hh = f'{int(h):02}'
    mm = f'{int(m):02}'
    ss = f'{round(float(s)):02}'
    return f'{hh}:{mm}:{ss}'


def split_dhms(time: str):
    """Extract days, hours, minutes, and seconds from a string time."""
    if 'day' in time:
        d, hms = time.split(',')
        h, m, s = hms.split(':')
        return int(d[0]), int(h), int(m), round(float(s))
    h, m, s = time.split(':')
    return 0, int(h), int(m), round(float(s))

