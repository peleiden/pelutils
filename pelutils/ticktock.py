from __future__ import annotations
from copy import deepcopy
from time import perf_counter
from typing import Generator, Optional

from pelutils import thousands_seperators
from pelutils.format import Table


class TimeUnits:
    """ Enum-like list of out-of-the-box available units. Format: (suffix, length) """
    nanosecond  = ("ns",  1e-9)
    microsecond = ("us",  1e-6)
    millisecond = ("ms",  1e-3)
    second      = ("s",   1)
    minute      = ("min", 60)
    hour        = ("h",   3600)

    @classmethod
    def units(cls) -> list[tuple[str, float]]:
        """ List all time units """
        return [unit for name, unit in cls.__dict__.items() if not callable(getattr(cls, name)) and not name.startswith("__")]

    @classmethod
    def next_bigger(cls, unit: tuple[str, float]) -> tuple[str, float]:
        """ Get smallest available time unit bigger than given """
        return min((u for u in cls.units() if u[1] > unit[1]), key=lambda x: x[1])

    @classmethod
    def next_smaller(cls, unit: tuple[str, float]) -> tuple[str, float]:
        """ Get largest available time unit smaller than given """
        return max((u for u in cls.units() if u[1] < unit[1]), key=lambda x: x[1])

class Profile:

    def __init__(self, name: str, depth: int, parent: Profile):
        self._hits: list[float] = []
        self.name = name
        self.depth = depth
        self.parent = parent
        if self.parent is not None:
            self.parent.children.append(self)
        self.children = list()

    @property
    def hits(self):
        return self._hits

    def sum(self) -> float:
        """ Returns total runtime """
        return sum(self._hits)

    def mean(self) -> float:
        """ Returns mean runtime lengths """
        return self.sum() / len(self) if self._hits else 0

    def std(self) -> float:
        """ Returns empirical standard deviation of runtime
        Be aware that this is highly sensitive to outliers and often a bad estimate """
        s = self.mean()
        return (1 / (len(self)+1) * sum(map(lambda x: (x-s)**2, self._hits))) ** 0.5

    def __str__(self) -> str:
        return self.name

    def __len__(self) -> int:
        return len(self._hits)

    def __iter__(self) -> Generator[Profile, None, None]:
        """ Yields a generator that is first self and then all descendants """
        yield self
        for child in self.children:
            yield from child

    def __hash__(self) -> int:
        return hash((self.name, self.depth, self.parent))

class _ProfileContext:

    def __init__(self, tt, profile_name: str):
        self.tt = tt
        self.profile_name = profile_name

    def __enter__(self):
        pass

    def __exit__(self, et, _, __):
        if et == KeyboardInterrupt:
            return
        if et is not None:
            # If an exception occured in deeper profiling sections, make sure to end them
            # before continuing, as a NameError otherwise will be raised due to unclosed profilings.
            while self.tt._profile_stack[-1].name != self.profile_name:
                self.tt.end_profile()
        self.tt.end_profile(self.profile_name)

class TickTockException(RuntimeError):
    pass

class TickTock:
    """ Simple time taker inspired by Matlab Tic, Toc, which also has profiling tooling.

    ```py
    TT.tick()
    <some task>
    seconds_used = TT.tock()

    for i in range(100):
        TT.profile("Repeated code")
        <some task>
        TT.profile("Subtask")
        <some subtask>
        TT.end_profile()
        TT.end_profile()
    print(TT)  # Prints a table view of profiled code sections

    # Alternative syntax using with statement
    with TT.profile("The best task"):
        <some task>

    # When using multiprocessing, it can be useful to simulate multiple hits of the same profile
    with mp.Pool() as p, TT.profile("Processing 100 items on multiple threads", hits=100):
        p.map(100 items)
    # Similar for very quick loops
    a = 0
    with TT.profile("Adding 1 to a", hits=100):
        for _ in range(100):
            a += 1

    # Examples so far use a global TickTock instance, which is convenient,
    # but it can also be desirable to use for multiple different timers, e.g.
    tt1 = TickTock()
    tt2 = TickTock()
    t1_interval = 1  # Do task 1 every second
    t2_interval = 2  # Do task 2 every other second
    tt1.tick()
    tt2.tick()
    while True:
        if tt1.tock() > t1_interval:
            <task 1>
        if tt2.tock() > t2_interval:
            <task 2>
        time.sleep(0.01)
    ``` """

    def __init__(self):
        self._start:         float | None = None
        self._id_to_profile: dict[int, Profile] = dict()
        self.profiles:       list[Profile] = list()
        self._profile_stack: list[Profile] = list()
        self._nhits:         list[int] = list()

    def tick(self):
        """ Start a timer """
        self._start = perf_counter()

    def tock(self) -> float:
        """ End current timer """
        end = perf_counter()
        if self._start is None:
            raise TickTockException("You must start the timer by calling .tick()")
        return end - self._start

    def profile(self, name: str, *, hits=1) -> _ProfileContext:
        """ Begin profile with given name. Optionally it is possible to
        register this as several hits that sum to the total time.
        This is usual when executing a multiprocessing mapping operation. """
        profile = Profile(
            name,
            len(self._profile_stack),
            self._profile_stack[-1] if self._profile_stack else None,
        )

        if hash(profile) in self._id_to_profile:
            profile = self._id_to_profile[hash(profile)]
            if profile.parent is not None:
                profile.parent.children.pop()
        else:
            self._id_to_profile[hash(profile)] = profile
            if not self._profile_stack:
                self.profiles.append(profile)

        self._profile_stack.append(profile)
        self._nhits.append(hits)
        pc = _ProfileContext(self, name)
        profile.start = perf_counter()
        return pc

    def end_profile(self, name: str=None) -> float:
        """ End profile. If name given, it is checked that it matches latest
        started profile. Return time passed since .profile was called. """
        end = perf_counter()
        dt = end - self._profile_stack[-1].start
        if name is not None and name != self._profile_stack[-1].name:
            raise NameError(f"Expected to pop profile '{self._profile_stack[-1].name}', received '{name}'")
        nhits = self._nhits.pop()
        self._profile_stack[-1]._hits += [dt/nhits] * nhits
        self._profile_stack.pop()
        return dt

    def reset(self):
        """ Stops all timing and profiling. """
        if self._profile_stack:
            raise TickTockException("Cannot reset TickTock while profiling is active")
        self.__init__()

    def add_external_measurements(self, name: Optional[str], time: float, *, hits=1):
        """ Allows adding data to a (new) profile with given time spread over given hits.
        If name is a string, it will act like .profile(name). If it is none, the current
        active profile will be used. """
        measurements = [time / hits] * hits
        if name is not None:
            self.profile(name, hits=hits)
            profile = self._profile_stack[-1]
            self.end_profile()
            profile._hits[-hits:] = measurements
        else:
            self._profile_stack[-1]._hits += measurements

    def fuse(self, tt: TickTock):
        """ Fuses a TickTock instance into self """
        if len(self._profile_stack) or len(tt._profile_stack):
            raise TickTockException("Unable to fuse while some profiles are still unfinished")
        # TODO allow one of them to be a subset of the other
        if tuple(self._id_to_profile) != tuple(tt._id_to_profile):
            raise TickTockException("Ticktocks to be fused do not match")

        for key, profile in tt._id_to_profile.items():
            existing = self._id_to_profile[key]
            existing._hits += profile._hits

    @staticmethod
    def fuse_multiple(*tts: TickTock) -> TickTock:
        """ Combine multiple TickTocks """
        ticktock = deepcopy(tts[0])
        ids = set(id(tt) for tt in tts)
        if len(ids) < len(tts):
            raise ValueError("Some TickTocks are the same instance, which is not allowed")
        for tt in tts[1:]:
            ticktock.fuse(tt)
        return ticktock

    @staticmethod
    def stringify_time(dt: float, unit: tuple[str, float]=TimeUnits.millisecond) -> str:
        """ Stringify a time given in seconds with a given unit """
        str_ = f"{dt/unit[1]:.3f} {unit[0]}"
        return thousands_seperators(str_)

    def stringify_sections(self, unit: tuple[str, float]=TimeUnits.second, with_std=False) -> str:
        """ Returns a pretty print of profiles """
        if self._profile_stack:
            raise ValueError("TickTock instance cannot be stringified while profiling is still ongoing. "\
                "Please end all profiles first")

        table = Table()
        h = ["Profile", "Total time", "Percentage", "Hits", "Average"]
        if with_std:
            h.append("Std.")
        table.add_header(h)
        total_time = sum(p.sum() for p in self.profiles)
        for profile in self:
            row = [
                "  " * profile.depth + profile.name,
                self.stringify_time(profile.sum(), unit),
                "%.3f" % (100 * profile.sum() / (profile.parent.sum() if profile.parent else total_time))
                    + (" <" if profile.depth else "") + "--" * (profile.depth-1),
                thousands_seperators(len(profile)),
                self.stringify_time(profile.mean(), TimeUnits.next_smaller(unit))
            ]
            if with_std:
                row.append(self.stringify_time(profile.std(), TimeUnits.next_smaller(unit)))
            table.add_row(row, [True] + [False] * (len(row)-1))

        return str(table)

    def __str__(self) -> str:
        return self.stringify_sections(TimeUnits.second)

    def __len__(self) -> int:
        """ Returns number of profiles """
        return len(self.profiles)

    def __iter__(self) -> Generator[Profile, None, None]:
        """ Recursively returns all profiles in the tree """
        for profile in self.profiles:
            yield from profile


TT = TickTock()
