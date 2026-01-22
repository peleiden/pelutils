from __future__ import annotations

import warnings
from collections.abc import Generator, Hashable
from copy import deepcopy
from threading import current_thread
from time import perf_counter

from deprecated import deprecated

from pelutils.format import Table


class TimeUnits:
    """Enum-like list of out-of-the-box available units.

    Each element is a tuple of the unit suffix and its length in seconds.
    """

    nanosecond  = ("ns",  1e-9)
    microsecond = ("us",  1e-6)
    millisecond = ("ms",  1e-3)
    second      = ("s",   1)
    hour        = ("h",   3600)

    @classmethod
    def units(cls, reverse=False) -> list[tuple[str, float]]:
        """List all time units in order of increasing duration, unless reverse is True."""
        units = (unit for name, unit in cls.__dict__.items() if not callable(getattr(cls, name)) and not name.startswith("__"))
        units = sorted(units, key=lambda unit: unit[1], reverse=reverse)
        return units

    @classmethod
    def next_bigger(cls, unit: tuple[str, float]) -> tuple[str, float]:
        """Get smallest available time unit bigger than given."""
        return min((u for u in cls.units() if u[1] > unit[1]), key=lambda x: x[1])

    @classmethod
    def next_smaller(cls, unit: tuple[str, float]) -> tuple[str, float]:
        """Get largest available time unit smaller than given."""
        return max((u for u in cls.units() if u[1] < unit[1]), key=lambda x: x[1])

def _get_smallest_suitable_unit(duration_s: float) -> tuple[str, float]:
    """Return the smallest unit for which the duration is at least the same size as the unit."""
    units = TimeUnits.units(reverse=True)
    for unit, unit_duration in units:
        if duration_s >= unit_duration:
            return unit, unit_duration
    return units[-1]  # No unit is small enough, so return the smallest unit

class Profile:  # noqa: D101

    def __init__(self, name: str, depth: int, parent: Profile | None):
        """Data for a profiled code section.

        Parameters
        ----------
        name : str
            Name, or brief description, or the profiled code section.
        depth : int
            Number of ancestor profiles.
        parent : Profile | None
            Direct ancestor. Can be None if the profile is top-level, in which case depth must also be 0.
        """  # noqa: D401
        self._n: int = 0
        self._total_time: float = 0
        self.name = name
        self.depth = depth
        self.parent = parent
        self._disable_in_context = False
        if self.parent is not None:
            assert depth > 0
            self.parent.children.append(self)
        else:
            assert depth == 0
        self.children = list()

    @property
    @deprecated(version="3.1.0",
        reason="Length of individual hits are no longer saved, only aggregated statistics. This will return hits of average length.")
    def hits(self):
        return [self.mean()] * self._n

    def sum(self) -> float:
        """Return total runtime, the sum of all registered hits."""
        return self._total_time

    def mean(self) -> float:
        """Return mean runtime lengths. Returns 0 if no hits have been registered."""
        if self._n == 0:
            return 0
        return self._total_time / self._n

    def __str__(self) -> str:
        return self.name

    def __len__(self) -> int:
        return self._n

    def __iter__(self) -> Generator[Profile, None, None]:
        """Return a over this profile followed by all its children, recursively."""
        yield self
        for child in self.children:
            yield from child

    @property
    def _hashable(self) -> Hashable:
        return (self.name, self.depth, self.parent)

    def __hash__(self) -> int:
        return hash(self._hashable)

    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, Profile) and self._hashable == __value._hashable

class _ProfileContext:

    def __init__(self, tt: "TickTock", profile: Profile):  # noqa: UP037
        self._tt = tt
        self._profile = profile

    def __enter__(self):
        pass

    def __exit__(self, et, _, __):
        if et is not None:
            # If an exception occured in deeper profiling sections, make sure to end them
            # before continuing, as a NameError otherwise will be raised due to unclosed profilings.
            while self._tt._profile_stack and self._tt._profile_stack[-1] != self._profile:
                self._tt.end_profile()
        self._tt.end_profile(self._profile.name)

class TickTockException(RuntimeError):
    """Raised when an exception occurs when using the TickTock class."""

class TickTock:
    """Simple time taker inspired by Matlab Tic, Toc, which also has profiling tooling.

    It is possible to import `TT` directly as a global instance for convenience, or import `TickTock` and create a new instance.
    For most use cases, importing `TT` is recommended, but when using threads (or async), creating a ticktock instance per thread
    is recommended.

    Basic use is as follows.
    ```py
    TT.tick()
    <some task>
    seconds_used = TT.tock()

    for i in range(100):
        with TT.profile("Repeated code"):
        <some task>
        with TT.profile("Subtask"):
            <some subtask>
    print(TT)  # Print a table view of profiled code sections

    # When using multiprocessing, it can be useful to simulate multiple hits of the same profile
    with mp.Pool() as p, TT.profile("Processing 100 items on multiple threads", hits=100):
        p.map(100 items)
    # Similar for very quick loops
    a = 0
    with TT.profile("Adding 1 to a", hits=100):
        for _ in range(100):
            a += 1

    # To use the TickTock instance as a timer to trigger events, do
    while True:
        if TT.do_at_interval(60, "task1"):  # Do task 1 every 60 seconds
            <task 1>
        if TT.do_at_interval(30, "task2"):  # Do task 2 every 30 seconds
            <task 2>
        time.sleep(0.01)
    ```
    """

    def __init__(self):
        self._tick_starts:   dict[Hashable, float] = dict()
        self._id_to_profile: dict[int, Profile] = dict()
        self.profiles:       list[Profile] = list()  # Top level profiles
        self._profile_stack: list[Profile] = list()
        self._nhits:         list[int] = list()

        self._thread_name = current_thread().name
        self._thread_id = id(current_thread())

    def tick(self, id: Hashable = None):
        """Start a timer. Set id to any hashable value (e.g. string or int) to time multiple things once."""
        self._tick_starts[id] = perf_counter()

    def tock(self, id: Hashable = None) -> float:
        """End current the timer."""
        end = perf_counter()
        if id not in self._tick_starts:
            raise TickTockException(f"A timer for the given ID ({id}) has not been started with .tick()")
        return end - self._tick_starts[id]

    def profile(self, name: str, *, hits=1, disable=False) -> _ProfileContext:
        """Begin a profile with given name.

        Optionally it is possible to register this as several hits that sum to the total time.
        This is useful when profiling a very large number of quick operations.
        The following two snippets are functionally identical:
        ```py
        with TT.profile("Op", hits=5):
            for i in range(5):
                ...

        for i in range(5):
            with TT.profile("Op"):
                ...
        ```
        If `disable` is True, the profile, as well as all child profiles will not be counted.
        """
        if self._thread_id != id(current_thread()):
            warnings.warn(f"This TickTock instance was created in the {self._thread_name} thread but profiling was started in "
                          f"{current_thread().name}. Profiling is NOT designed to deal with multiple threads. Instead, create a "
                          "TickTock instance for each thread requiring profiling.", stacklevel=2)

        profile = Profile(
            name,
            len(self._profile_stack),
            self._profile_stack[-1] if self._profile_stack else None,
        )

        if profile in self._id_to_profile:
            profile = self._id_to_profile[profile]
            if profile.parent is not None:
                profile.parent.children.pop()
        else:
            self._id_to_profile[profile] = profile
            if not self._profile_stack:
                self.profiles.append(profile)
        profile._disable_in_context = disable or (self._profile_stack[-1]._disable_in_context if self._profile_stack else False)

        self._profile_stack.append(profile)
        self._nhits.append(hits)
        pc = _ProfileContext(self, profile)
        profile.start = perf_counter()
        return pc

    def end_profile(self, name: str | None = None) -> float:
        """End the active profile.

        If name is given, it is should match the profile start last.

        The time passed since the stopped profile was started is returned.
        """
        end = perf_counter()
        dt = end - self._profile_stack[-1].start
        if name is not None and name != self._profile_stack[-1].name:
            raise NameError(f"Expected to pop profile '{self._profile_stack[-1].name}', received '{name}'")
        nhits = self._nhits.pop()
        if not self._profile_stack[-1]._disable_in_context:
            self._profile_stack[-1]._n += nhits
            self._profile_stack[-1]._total_time += dt
        self._profile_stack[-1]._disable_in_context = False
        self._profile_stack.pop()
        return dt

    def reset(self):
        """Stop all timing and profiling and clear all profiles and measurements."""
        if self._profile_stack:
            raise TickTockException("Cannot reset TickTock while profiling is active")
        self.__init__()

    def reset_profiles(self):
        """Similar to `reset` but only reset profiles."""
        tick_starts = self._tick_starts
        self.reset()
        self._tick_starts = tick_starts

    def do_at_interval(self, interval: float, id: Hashable = None, *, also_first=False) -> True:
        """Return true if it is at least `interval` since this method was called with the same id previously.

        A common pattern is to run a piece of code at fixed intervals inside a loop. In the example below, a loop is continuously doing
        some computation which results in some telemetry. This is collected every 60 seconds.
        ```py
        while True:
            <stuff which produces some telemetry>

            if TT.do_at_interval(60, "telemetry"):
                <collect telemetry>
        ```
        If `also_first` is True, `do_at_interval` will return True the first time it is called with a given `id`.
        Otherwise, the interval has to elapse before True is returned the first time.
        """
        id = ("__interval__", id)
        if id not in self._tick_starts:
            self.tick(id)
            return also_first
        if self.tock(id) >= interval:
            self.tick(id)
            return True
        return False

    def add_external_measurements(self, name: str | None, time: float, *, hits=1):
        """Add data to a (new) profile with given time spread over given hits.

        If `name` is a string, it will act like `.profile(name)`. If it is `None`, the current active profile will be used.
        """
        if name is not None:
            self.profile(name, hits=hits)
            profile = self._profile_stack[-1]
            self.end_profile()
            profile._total_time += time
        else:
            self._profile_stack[-1]._n += hits
            self._profile_stack[-1]._total_time += time

    def fuse(self, tt: TickTock):
        """Fuse a TickTock instance into self."""
        if len(self._profile_stack) or len(tt._profile_stack):
            raise TickTockException("Unable to fuse while some profiles are still unfinished")
        # TODO allow one of them to be a subset of the other
        if tuple(self._id_to_profile) != tuple(tt._id_to_profile):
            raise TickTockException("Ticktocks to be fused do not match")

        for key, profile in tt._id_to_profile.items():
            existing = self._id_to_profile[key]
            existing._n += profile._n
            existing._total_time += profile._total_time

    @staticmethod
    def fuse_multiple(*tts: TickTock) -> TickTock:
        """Combine multiple TickTock instances."""
        ticktock = deepcopy(tts[0])
        ids = set(id(tt) for tt in tts)
        if len(ids) < len(tts):
            raise ValueError("Some TickTocks are the same instance, which is not allowed")
        for tt in tts[1:]:
            ticktock.fuse(tt)
        ticktock._thread_name = current_thread().name
        ticktock._thread_id = id(current_thread())
        return ticktock

    @staticmethod
    @deprecated(version="3.5.0")
    def stringify_time(dt: float, unit: tuple[str, float]=TimeUnits.millisecond) -> str:
        """Stringify a time given in seconds with a given unit."""
        return f"{dt/unit[1]:,.2f} {unit[0]}"

    @staticmethod
    def _stringify_time_with_alignment(dt: float, unit: tuple[str, float]) -> str:
        return f"{dt/unit[1]:,.2f} {unit[0]:>2}"

    def stringify_sections(self, unit: tuple[str, float] | None = TimeUnits.second) -> str:
        """Return a pretty string representation of the profile tree.

        If unit is None, suitable units will be automatically detected.
        """
        if self._profile_stack:
            raise ValueError("TickTock instance cannot be stringified while profiling is still ongoing. "\
                "Please end all profiles first")

        table = Table()
        h = ["Profile", "Total time", "Percentage", "Hits", "Average"]
        table.add_header(h)
        total_time = sum(p.sum() for p in self.profiles)
        for profile in self:
            psum = profile.sum()
            pmean = profile.mean()
            row = [
                "  " * profile.depth + profile.name,
                self._stringify_time_with_alignment(psum, unit if unit is not None else _get_smallest_suitable_unit(psum)),
                "%.2f" % (100 * psum / (profile.parent.sum() if profile.parent else total_time))
                    + (" <" if profile.depth else "") + "--" * (profile.depth-1),
                f"{len(profile):,}",
                self._stringify_time_with_alignment(pmean, TimeUnits.next_smaller(unit) if unit is not None else _get_smallest_suitable_unit(pmean))
            ]
            table.add_row(row, [True] + [False] * (len(row)-1))

        return str(table)

    @deprecated(version="3.1.0", reason="Individual hits are no longer recorded, only aggregated statistics. Use stats_by_profile_name instead.")
    def measurements_by_profile_name(self, name: str) -> list[float]:
        """Return the time measurement distribution for a profile with a given name.

        Warning: Since the name does not uniquely identify a profile, this function
        simply returns the first profile with this name, so be careful to check that
        you get the correct one if you have multiple profiles with the same name.
        """
        try:
            profile = next(profile for profile in self._id_to_profile.values() if profile.name == name)
        except StopIteration as e:
            raise KeyError(f"No profile with name {name}") from e

        return profile.hits

    def stats_by_profile_name(self, name: str) -> tuple[int, float]:
        """Return the number of hits and sum of measurement lengths for a profile with a given name.

        Warning: Since the name does not uniquely identify a profile, this function
        simply returns the first profile with this name, so be careful to check that
        you get the correct one if you have multiple profiles with the same name.
        """
        try:
            profile = next(profile for profile in self._id_to_profile.values() if profile.name == name)
        except StopIteration as e:
            raise KeyError(f"No profile with name {name}") from e

        return len(profile), profile.sum()

    def __str__(self) -> str:
        return self.stringify_sections(None)

    @deprecated(version="3.2.0", reason="Profiler length does not have a reasonable meaning.")
    def __len__(self) -> int:
        """Return the number of top-level profiles."""
        return len(self.profiles)

    def __bool__(self) -> bool:
        """Return True if any profiling has been performed."""
        return len(self.profiles) > 0

    def __iter__(self) -> Generator[Profile, None, None]:
        """Recursively returns all profiles in the tree."""
        for profile in self.profiles:
            yield from profile


TT = TickTock()
