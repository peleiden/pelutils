from __future__ import annotations
from copy import deepcopy
from time import perf_counter
from typing import Generator, Iterable

from pelutils import thousand_seps
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

    start: float

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

    def remove_outliers(self, threshold=2) -> int:
        """ Remove all hits larger than threshold * average
        Returns number of removed outliers """
        mu = self.mean()
        original_length = len(self)
        self._hits = [x for x in self._hits if x <= threshold * mu]
        return original_length - len(self)

    def __str__(self) -> str:
        return self.name

    def __len__(self) -> int:
        return len(self._hits)

    def __iter__(self) -> Generator[Profile, None, None]:
        """ yields a generator that is first self and then all descendants """
        yield self
        for child in self.children:
            yield from child


class _ProfileContext:

    def __init__(self, tt, profile_name: str):
        self.tt = tt
        self.profile_name = profile_name

    def __enter__(self):
        ...

    def __exit__(self, et, ev, tb):
        if et == KeyboardInterrupt:
            return
        self.tt.end_profile(self.profile_name)


class TickTockException(RuntimeError):
    pass


class TickTock:
    """
    A taker that works like Matlab's Tic and Toc.
    Simples use case:
    ```
    tt = TickTorck()
    tt.tick()
    <some task>
    time = tt.tock()
    ```
    Profiling code sections is also supported
    ```
    tt.profile(<profile name>)
    <some task>
    tt.end_profile()
    ```
    """

    def __init__(self):
        self._start = 0
        self.profiles:       dict[str, Profile] = {}
        self._profile_stack: list[Profile] = list()
        self._nhits:         list[int] = list()

    def tick(self) -> float:
        self._start = perf_counter()
        return self._start

    def tock(self) -> float:
        end = perf_counter()
        return end - self._start

    def profile(self, name: str, *, hits=1) -> _ProfileContext:
        """
        Begin profile with given name
        Optionally it is possible to register this as several hits that sum to the total time
        This is usual when execution a multiprocessing mapping operation
        """
        if name not in self.profiles:
            self.profiles[name] = Profile(
                name,
                len(self._profile_stack),
                self._profile_stack[-1] if self._profile_stack else None
            )
        self._profile_stack.append(self.profiles[name])
        self._nhits.append(hits)
        pc = _ProfileContext(self, name)
        self.profiles[name].start = perf_counter()
        return pc

    def end_profile(self, name: str=None) -> float:
        """ End profile. If name given, it is checked that it matches latest started profile
        Return time passed since .profile was called """
        end = perf_counter()
        dt = end - self._profile_stack[-1].start
        if name is not None and name != self._profile_stack[-1].name:
            raise NameError(f"Expected to pop profile '{self._profile_stack[-1].name}', received '{name}'")
        nhits = self._nhits.pop()
        self._profile_stack[-1].hits.extend([dt/nhits] * nhits)
        self._profile_stack.pop()
        return dt

    def profile_iter(self, it: Iterable, name: str) -> Generator:
        """
        tqdm-like method for profiling a for loop
        Do not use this for for loops that are ended with break statements!
        """
        for elem in it:
            self.profile(name)
            yield elem
            self.end_profile(name)

    def fuse(self, tt: TickTock):
        """ Fuses a TickTock instance into self """
        if len(self._profile_stack) or len(tt._profile_stack):
            raise ValueError("Unable to fuse while some profiles are still unfinished")
        for profile in tt.profiles.values():
            existing = self.profiles.get(profile.name)
            if existing:
                existing._hits += profile.hits
            else:
                self.profiles[profile.name] = profile

    @staticmethod
    def fuse_multiple(tts: list[TickTock]) -> TickTock:
        """ Combine multiple TickTocks """
        ticktock = TickTock()
        ids = set(id(tt) for tt in tts)
        if len(ids) < len(tts):
            raise ValueError("Some TickTocks are the same instance, which is not allowed")
        for tt in tts:
            ticktock.fuse(tt)
        return ticktock

    def remove_outliers(self, threshold=2):
        """ For all profiles, remove hits longer than threshold * average hit """
        for profile in self:
            profile.remove_outliers(threshold)

    @staticmethod
    def stringify_time(dt: float, unit: tuple[str, float]=TimeUnits.millisecond) -> str:
        str_ = f"{dt/unit[1]:.3f} {unit[0]}"
        return thousand_seps(str_)

    def stringify_sections(self, unit: tuple[str, float]=TimeUnits.second, with_std=False) -> str:
        """ Returns a pretty print of profiles """
        if self._profile_stack:
            raise ValueError("TickTock instance cannot be stringified while profiling is still ongoing. Please end all profiles first")

        table = Table()
        h = ["Profile", "Total time", "Percentage", "Hits", "Average"]
        if with_std:
            h.append("Std.")
        table.add_header(h)
        total_time = sum(p.sum() for p in self.profiles.values() if p.depth == 0)
        for profile in self:
            row = [
                "  " * profile.depth + profile.name,
                self.stringify_time(profile.sum(), unit),
                "%.3f" % (100 * profile.sum() / (profile.parent.sum() if profile.parent else total_time))
                    + (" <" if profile.depth else "") + "--" * (profile.depth-1),
                thousand_seps(len(profile)),
                self.stringify_time(profile.mean(), TimeUnits.next_smaller(unit))
            ]
            if with_std:
                row.append(self.stringify_time(profile.std(), TimeUnits.next_smaller(unit)))
            table.add_row(row, [True] + [False] * (len(row)-1))

        return str(table)

    def __str__(self) -> str:
        return self.stringify_sections(TimeUnits.second)

    def __len__(self) -> int:
        return len(self.profiles)

    def __iter__(self) -> Generator[Profile, None, None]:
        for profile in (p for p in self.profiles.values() if p.depth == 0):
            yield from profile


TT = TickTock()
