import warnings
from collections.abc import Hashable, Iterator, Sequence
from contextlib import contextmanager
from copy import deepcopy
from threading import current_thread
from time import perf_counter

from typing_extensions import override

from pelutils.misc import Table

_TimeUnit = tuple[str, float]  # Unit suffix, unit value in seconds
# Time units available for formatting
# These must be sorted by time
_time_units = (
    ("ns", 1e-9),
    ("us", 1e-6),
    ("ms", 1e-3),
    ("s", 1),
    ("h", 3600),
)


def _get_smallest_suitable_unit(duration_s: float) -> tuple[str, float]:
    """Return the smallest unit for which the duration is at least the same size as the unit."""
    for unit, unit_duration in _time_units[::-1]:
        if duration_s >= unit_duration:
            return unit, unit_duration
    return _time_units[0]  # No unit is small enough, so return the smallest unit


class Profile:
    def __init__(self, name: str, depth: int, parent: "Profile | None"):
        """Contains data for a profiled code section.

        Parameters
        ----------
        name : str
            Name, or brief description, or the profiled code section.
        depth : int
            Number of ancestor profiles.
        parent : Profile | None
            Direct ancestor. Can be None if the profile is top-level, in which case depth must also be 0.
        """
        # Number of times the profile has been hit
        self.nhits: int = 0
        # Total runtime across all hits
        self.total_runtime: float = 0
        # Name of the profile
        self.name = name
        # Depth in the profile tree - 0 means that it is available at the root
        self.depth = depth
        # Parent profile of the profile
        self.parent = parent
        # Whether or not to disable profile
        # This is set to True when entering a profiling section that is disabled, or if the parent is disabled
        # It is always set back to False after leaving the profiling context
        self._disable = False
        if self.parent is not None:
            assert depth > 0
            self.parent.children.append(self)
        else:
            assert depth == 0
        self.children = list()
        self.start: float = 0  # Timestamp of when the profile was started, initialised to 0

    def sum(self) -> float:
        """Return total runtime, the sum of all registered hits."""
        return self.total_runtime

    def mean(self) -> float:
        """Return mean runtime lengths. Returns 0 if no hits have been registered."""
        if self.nhits == 0:
            return 0
        return self.total_runtime / self.nhits

    @override
    def __str__(self) -> str:
        return self.name

    def __iter__(self) -> "Iterator[Profile]":
        """Return a recursive iterator over this profile followed by all its children."""
        if not self.nhits:
            # If the profile has had zero hits, which happens when it has run in disabled mode, pretend it is Nikolai Yezhov
            return
        yield self
        for child in self.children:
            yield from child

    @property
    def _hashable(self) -> Hashable:
        return (self.name, self.depth, self.parent)

    @override
    def __hash__(self) -> int:
        return hash(self._hashable)

    @override
    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, Profile) and self._hashable == __value._hashable


class TickTockException(RuntimeError):  # noqa: N818
    """Raised when an exception occurs when using the TickTock class."""


class TickTock:
    """Simple time taker inspired by Matlab Tic, Toc, which also has profiling tooling.

    It is possible to import ``TT`` directly as a global instance for convenience, or import ``TickTock`` and create a new instance.
    For most use cases, importing ``TT`` is recommended, but when using threads (or async), creating a ticktock instance per thread
    is recommended.

    Basic use is as follows.

    .. code-block:: python

        TT.tick()
        # Some task
        seconds_used = TT.tock()

        for _ in range(100):
            with TT.profile("Repeated code"):
                # Some task
                with TT.profile("Subtask"):
                    # Some subtask
                    pass
        print(TT)  # Print a table view of profiled code sections

        # When using multiprocessing, it can be useful to simulate multiple hits of the same profile.
        with mp.Pool() as pool, TT.profile("Processing 100 items on multiple threads", hits=100):
            pool.map(process_item, items)

        # Similar for very quick loops.
        a = 0
        with TT.profile("Adding 1 to a", hits=100):
            for _ in range(100):
                a += 1

        # To use the TickTock instance as a timer to trigger events:
        while True:
            if TT.do_at_interval(60, "task1"):  # Do task 1 every 60 seconds.
                run_task_1()
            if TT.do_at_interval(30, "task2"):  # Do task 2 every 30 seconds.
                run_task_2()
            time.sleep(0.01)
    """

    def __init__(self):
        self._tick_starts: dict[Hashable, float] = dict()
        # All created profiles are stored in this dictionary
        # Profiles are used as keys for themselves
        # This allows lookup for when identical profiles are created and should be appended to an existing profile
        self._id_to_profile: dict[Hashable, Profile] = dict()
        self._profile_stack: list[Profile] = list()  # LIFO stack of active profiles
        self._root_profiles: list[Profile] = list()  # Top level profiles

        self._thread_name = current_thread().name
        self._thread_id = id(current_thread())

    def tick(self, key: Hashable = None):
        """Start a timer identified by an optional hashable key."""
        self._tick_starts[key] = perf_counter()

    def tock(self, key: Hashable = None) -> float:
        """End the timer identified by ``key`` and return the elapsed time in seconds."""
        end = perf_counter()
        if key not in self._tick_starts:
            raise TickTockException(f"A timer for the given key ({key}) has not been started with .tick()")
        return end - self._tick_starts[key]

    def _start_profile(self, name: str, *, hits: int, disable: bool):
        """Start a profile and add it to relevant attributes that keep track of profiles."""
        profile = Profile(
            name,
            len(self._profile_stack),
            self._profile_stack[-1] if len(self._profile_stack) > 0 else None,
        )

        if profile in self._id_to_profile:
            profile = self._id_to_profile[profile]
            if profile.parent is not None:
                profile.parent.children.pop()
        else:
            self._id_to_profile[profile] = profile
            if not self._profile_stack:
                self._root_profiles.append(profile)

        profile._disable = disable or (self._profile_stack[-1]._disable if len(self._profile_stack) > 0 else False)  # pyright: ignore[reportPrivateUsage]
        if not profile._disable:  # pyright: ignore[reportPrivateUsage]
            profile.nhits += hits

        self._profile_stack.append(profile)
        profile.start = perf_counter()

    def _end_profile(self):
        """End the inner-most active profile."""
        end = perf_counter()
        dt = end - self._profile_stack[-1].start
        if not self._profile_stack[-1]._disable:  # pyright: ignore[reportPrivateUsage]
            self._profile_stack[-1].total_runtime += dt
        self._profile_stack[-1]._disable = False  # pyright: ignore[reportPrivateUsage]
        self._profile_stack.pop()

    @contextmanager
    def profile(self, name: str, *, hits: int = 1, disable: bool = False):
        """Begin a profile with given name.

        Optionally it is possible to register this as several hits that sum to the total time.
        This is useful when profiling a very large number of quick operations.
        The following two snippets are functionally identical:

        .. code-block:: python

            with TT.profile("Op", hits=5):
                for i in range(5):
                    ...

            for i in range(5):
                with TT.profile("Op"):
                    ...

        If ``disable`` is True, the profile, as well as all child profiles will not be counted.
        """
        if self._thread_id != id(current_thread()):
            warnings.warn(
                f"This TickTock instance was created in the {self._thread_name} thread but profiling was started in "
                + f"{current_thread().name}. Profiling is NOT designed to deal with multiple threads. Instead, create a "
                + "TickTock instance for each thread requiring profiling.",
                stacklevel=2,
            )

        started_profile = False
        try:
            self._start_profile(name, hits=hits, disable=disable)
            started_profile = True
            yield
        finally:
            # Only end the newly started profile if one was succesfully started
            # If _start_profile fails and _end_profile then runs, that can give some nasty error messages
            if started_profile:
                self._end_profile()

    def reset(self):
        """Stop all timing and profiling and clear all profiles and measurements."""
        if self._profile_stack:
            raise TickTockException("Cannot reset TickTock while profiling is active")
        self.__init__()

    def reset_profiles(self):
        """Similar to ``reset`` but only reset profiles, leaving ``tick``/``tock`` timers intact."""
        tick_starts = self._tick_starts
        self.reset()
        self._tick_starts = tick_starts

    def do_at_interval(self, interval: float, key: Hashable = None, *, also_first: bool = False) -> bool:
        """Return true if it is at least `interval` since this method was called with the same key previously.

        A common pattern is to run a piece of code at fixed intervals inside a loop. In the example below, a loop is continuously doing
        some computation which results in some telemetry. This is collected every 60 seconds.

        .. code-block:: python

            while True:
                if TT.do_at_interval(60, "telemetry"):
                    collect_telemetry()
                ...

        If ``also_first`` is True, ``do_at_interval`` will return True the first time it is called with a given ``key``.
        Otherwise, the interval has to elapse before True is returned the first time.
        """
        key = ("__interval__", key)
        if key not in self._tick_starts:
            self.tick(key)
            return also_first
        if self.tock(key) >= interval:
            self.tick(key)
            return True
        return False

    def fuse(self, tt: "TickTock"):
        """Fuse a TickTock instance into self."""
        if len(self._profile_stack) or len(tt._profile_stack):
            raise TickTockException("Unable to fuse while some profiles are still unfinished")
        # TODO allow one of them to be a subset of the other
        if self._id_to_profile.keys() != tt._id_to_profile.keys():
            raise TickTockException("Ticktocks to be fused do not match")

        for key, profile in tt._id_to_profile.items():
            existing = self._id_to_profile[key]
            existing.nhits += profile.nhits
            existing.total_runtime += profile.total_runtime

    @staticmethod
    def fuse_multiple(tts: "Sequence[TickTock]") -> "TickTock":
        """Combine the profiles of multiple TickTock instances."""
        if len(tts) == 0:
            return TickTock()

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
    def _stringify_time_with_alignment(dt: float, unit: tuple[str, float]) -> str:
        return f"{dt / unit[1]:,.2f} {unit[0]:>2}"

    @override
    def __str__(self) -> str:
        """Return a pretty table representation of the profile tree.

        The table lists each profile with its total time, its percentage of the parent's
        time (or of the overall time for root profiles), the number of hits, and the average
        time per hit. Profiles are shown depth-first and indented by depth. Suitable time
        units are detected automatically per value. Raises if profiling is still ongoing.
        """
        if self._profile_stack:
            raise ValueError("TickTock instance cannot be stringified while profiling is still ongoing. Please end all profiles first")

        table = Table()
        h = ["Profile", "Total time", "Percentage", "Hits", "Average"]
        table.add_header(h)
        total_time = sum(p.sum() for p in self._root_profiles)
        for profile in self.iter_profiles():
            psum = profile.sum()
            pmean = profile.mean()
            row = [
                "  " * profile.depth + profile.name,
                self._stringify_time_with_alignment(psum, _get_smallest_suitable_unit(psum)),
                "%.2f" % (100 * psum / (profile.parent.sum() if profile.parent else total_time))
                + (" <" if profile.depth else "")
                + "--" * (profile.depth - 1),
                f"{profile.nhits:,}",
                self._stringify_time_with_alignment(pmean, _get_smallest_suitable_unit(pmean)),
            ]
            table.add_row(row, [True] + [False] * (len(row) - 1))

        return str(table)

    def iter_profiles(self) -> Iterator[Profile]:
        """Recursively returns all profiles in the tree.

        They are ordered in a depth-first manner rather than breadth-first.
        """
        for profile in self._root_profiles:
            yield from profile

    @property
    def has_profiles(self) -> bool:
        """Return True if any profiling has been performed."""
        return len(self._root_profiles) > 0


TT = TickTock()
