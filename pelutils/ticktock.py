from time import perf_counter

from typing import List, Dict, Tuple
from pelutils import thousand_seps

class TimeUnit:
    nanosecond  = ("ns",  1e9)
    microsecond = ("mus", 1e6)
    millisecond = ("ms",  1e3)
    second      = ("s",   1)
    minute      = ("min", 1/60)
    hour        = ("h",   1/3600)


class Profile:

    start: float

    def __init__(self, name: str, depth: int):
        self.hits: List[float] = []
        self.name = name
        self.depth = depth

    def get_hits(self):
        return self.hits

    def sum(self):
        """ Returns total runtime """
        return sum(self.get_hits())

    def mean(self):
        """ Returns mean runtime lengths """
        return self.sum() / len(self) if self.get_hits() else 0

    def std(self):
        """ Returns empirical standard deviation of runtime
        Be aware that this is highly sensitive to outliers and often a bad estimate """
        s = self.mean()
        return (1 / (len(self)+1) * sum(map(lambda x: (x-s)**2, self.get_hits()))) ** 0.5

    def remove_outliers(self, threshold=2):
        """ Remove all hits larger than threshold * average
        Returns number of removed outliers """
        mu = self.mean()
        original_length = len(self)
        self.hits = [x for x in self.hits if x <= threshold * mu]
        return original_length - len(self)

    def __str__(self):
        return self.name

    def __len__(self):
        return len(self.hits)


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
    profiles: Dict[str, Profile] = {}
    _profile_stack: List[Profile] = list()

    def tick(self):
        self._start = perf_counter()
        return self._start

    def tock(self):
        end = perf_counter()
        return end - self._start

    def profile(self, name: str):
        if name not in self.profiles:
            self.profiles[name] = Profile(name, len(self._profile_stack))
        self._profile_stack.append(self.profiles[name])
        self.profiles[name].start = perf_counter()

    def end_profile(self, name: str=None):
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
                self.profiles[profile.name].hits += profile.hits
            else:
                self.profiles[profile.name] = profile

    def remove_outliers(self, threshold=2):
        # For all profiles, remove hits longer than threshold * average hit
        for profile in self.profiles.values():
            profile.remove_outliers(threshold)

    def reset(self):
        self.profiles = {}
        self._profile_depth = 0

    @classmethod
    def stringify_time(cls, dt: float, unit: Tuple[str, float]=TimeUnit.millisecond):
        str_ = f"{dt*unit[1]:.3f} {unit[0]}"
        return thousand_seps(str_)

    def stringify_sections(self, unit: Tuple[str, float]=TimeUnit.second):
        # TODO: Less mess here
        # TODO: Keep track of children/parent profiles to ensure correct printing
        # Returns pretty sections
        strs = [["Execution times", "Total time", "Hits", "Avg. time"]]
        # std_strs = []
        for kw, v in self.profiles.items():
            # std = self.stringify_time(2*np.std(v["hits"]), "ms")
            # std_strs.append(std)
            strs.append([
                "- " * v.depth + kw,
                self.stringify_time(v.sum(), unit),
                thousand_seps(len(v)),
                self.stringify_time(v.mean(), TimeUnit.millisecond)
            ])
        # longest_std = max(len(x) for x in std_strs)
        # std_strs = [" " * (longest_std-len(x)) + x for x in std_strs]
        # for i, str_ in enumerate(strs[1:]): str_[-1] += std_strs[i]
        for i in range(len(strs[0])):
            length = max(len(strs[j][i]) for j in range(len(strs)))
            for j in range(len(strs)):
                if i == 0:
                    strs[j][i] += " " * (length - len(strs[j][i]))
                else:
                    strs[j][i] = " " * (length - len(strs[j][i])) + strs[j][i]
        for i in range(len(strs)):
            strs[i] = " | ".join(strs[i])
        return "\n".join(strs)

    def __str__(self):
        return self.stringify_sections(TimeUnit.second)

