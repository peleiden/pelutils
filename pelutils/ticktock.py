from __future__ import annotations
from time import perf_counter

from pelutils import thousand_seps
from pelutils.format import Table


class TimeUnit:
    nanosecond  = ("ns",  1e9)
    microsecond = ("mus", 1e6)
    millisecond = ("ms",  1e3)
    second      = ("s",   1)
    minute      = ("min", 1/60)
    hour        = ("h",   1/3600)


class Profile:

    start: float

    def __init__(self, name: str, depth: int, parent: Profile):
        self._hits: list[float] = []
        self.name = name
        self.depth = depth
        self.parent = parent

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
    _start = 0
    profiles: dict[str, Profile] = {}
    _profile_stack: list[Profile] = list()

    def tick(self) -> float:
        self._start = perf_counter()
        return self._start

    def tock(self) -> float:
        end = perf_counter()
        return end - self._start

    def profile(self, name: str):
        """ Begin profile with given name """
        if name not in self.profiles:
            self.profiles[name] = Profile(
                name,
                len(self._profile_stack),
                self._profile_stack[-1] if self._profile_stack else None
            )
        self._profile_stack.append(self.profiles[name])
        self.profiles[name].start = perf_counter()

    def end_profile(self, name: str=None) -> float:
        """ End profile. If name given, it is checked that it matches latest started profile
        Return time passed since .profile was called """
        end = perf_counter()
        dt = end - self._profile_stack[-1].start
        self._profile_stack[-1].hits.append(dt)
        profile = self._profile_stack.pop()
        if name is not None:
            assert name == profile.name, f"Expected to pop profile '{profile.name}', received '{name}'"
        return dt

    def fuse(self, tt):
        """Fuses a TickTock instance into self"""
        for profile in tt.profiles.values():
            if profile.name in self.profiles.keys():
                self.profiles[profile.name]._hits += profile.hits
            else:
                self.profiles[profile.name] = profile

    def remove_outliers(self, threshold=2):
        # For all profiles, remove hits longer than threshold * average hit
        for profile in self.profiles.values():
            profile.remove_outliers(threshold)

    def reset(self):
        self.profiles = {}

    @staticmethod
    def stringify_time(dt: float, unit: tuple[str, float]=TimeUnit.millisecond) -> str:
        str_ = f"{dt*unit[1]:.3f} {unit[0]}"
        return thousand_seps(str_)

    def stringify_sections(self, unit: tuple[str, float]=TimeUnit.second) -> str:
        """ Returns a pretty print of profiles """
        table = Table()
        table.add_header(["Profile", "Total time", "Percentage", "Hits", "Average"])
        total_time = sum(p.sum() for p in self.profiles.values() if p.depth == 0)
        for kw, v in self.profiles.items():
            table.add_row([
                "  " * v.depth + kw,
                self.stringify_time(v.sum(), unit),
                "%.3f %%" % (100 * v.sum() / (v.parent.sum() if v.parent else total_time)),
                thousand_seps(len(v)),
                self.stringify_time(v.mean(), TimeUnit.millisecond)
            ], [True, False, False, False, False])

        return str(table)

    def __str__(self) -> str:
        return self.stringify_sections(TimeUnit.second)

