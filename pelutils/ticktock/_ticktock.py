# Profiles and frames are internal to this module, so private access between them is expected
# pyright: reportPrivateUsage=false
import inspect
import threading
from collections.abc import Callable, Hashable, Iterable, Iterator, Sequence
from contextlib import ContextDecorator, contextmanager
from contextvars import ContextVar, Token
from copy import deepcopy
from functools import wraps
from time import perf_counter
from typing import Any, TypeAlias, TypeVar

from typing_extensions import override

from pelutils.misc import Table

_TimeUnit: TypeAlias = tuple[str, float]  # Unit suffix, unit value in seconds
# Time units available for formatting
# These must be sorted by time
_time_units: tuple[_TimeUnit, ...] = (
    ("ns", 1e-9),
    ("us", 1e-6),
    ("ms", 1e-3),
    ("s", 1),
    ("h", 3600),
)

T = TypeVar("T")
_F = TypeVar("_F", bound=Callable[..., Any])  # pyright: ignore[reportExplicitAny]

_active_ticktock: "ContextVar[TickTock | None]" = ContextVar("active_ticktock", default=None)


def _get_smallest_suitable_unit(duration_s: float) -> _TimeUnit:
    """Return the smallest unit for which the duration is at least the same size as the unit."""
    for unit, unit_duration in _time_units[::-1]:
        if duration_s >= unit_duration:
            return unit, unit_duration
    return _time_units[0]  # No unit is small enough, so return the smallest unit


class Profile:
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

    def __init__(self, name: str, depth: int, parent: "Profile | None"):
        # Number of times the profile has been hit, including hits that are still in progress
        # Hits in progress have no runtime yet, so use sum() and mean() rather than dividing by this
        self.nhits: int = 0
        # Total runtime across all completed hits
        self.total_runtime: float = 0
        # Name of the profile
        self.name = name
        # Depth in the profile tree - 0 means that it is available at the root
        self.depth = depth
        # Parent profile of the profile
        self.parent = parent
        if self.parent is not None:
            assert depth > 0
            self.parent.children.append(self)
        else:
            assert depth == 0
        self.children: list[Profile] = list()
        # Number of hits that have started but not yet finished
        self._active_hits = 0
        # Children by name for fast lookup
        self._child_index: dict[str, Profile] = dict()

    def _completed_hits(self) -> int:
        return self.nhits - self._active_hits

    def _walk(self) -> "Iterator[Profile]":
        """Like iterating over the profile, but also includes profiles without hits."""
        yield self
        for child in self.children:
            yield from child._walk()

    def sum(self) -> float:
        """Return total runtime, the sum of all completed hits."""
        return self.total_runtime

    def mean(self) -> float:
        """Return mean runtime of completed hits. Returns 0 if no hits have been completed."""
        completed = self._completed_hits()
        if completed == 0:
            return 0
        return self.total_runtime / completed

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


class _Tree:
    """Containers for a profile tree. Replaced as a whole when profiles are reset."""

    __slots__ = ("root_index", "root_profiles")

    def __init__(self):
        self.root_profiles: list[Profile] = list()  # Top level profiles
        self.root_index: dict[str, Profile] = dict()  # Top level profiles by name


class _Intervals(threading.local):
    """Start times for ``do_at_interval``, separate for each thread."""

    def __init__(self):
        self.starts: dict[Hashable, float] = dict()


class _Frame:
    """A single active hit of a profile within one context."""

    __slots__ = ("closed", "disabled", "hits", "parent", "profile", "start", "token", "tree")

    def __init__(self, profile: Profile, parent: "_Frame | None", tree: _Tree, disabled: bool, hits: int):
        self.profile = profile
        self.parent = parent
        self.tree = tree
        self.disabled = disabled
        self.hits = hits
        # Set when the profile ends. Closed frames left behind by out-of-order exits are skipped
        self.closed = False
        self.start = 0.0
        self.token: Token[_Frame | None] | None = None


def _create_profile(tree: _Tree, name: str, parent: Profile | None) -> Profile:
    """Create a profile and add it to ``tree``. The caller must hold the lock of the owning TickTock."""
    profile = Profile(name, 0 if parent is None else parent.depth + 1, parent)
    (tree.root_index if parent is None else parent._child_index)[name] = profile
    if parent is None:
        tree.root_profiles.append(profile)
    return profile


def _skip_closed(frame: _Frame | None) -> _Frame | None:
    """Return the innermost frame in the chain starting at ``frame`` that has not been closed."""
    while frame is not None and frame.closed:
        frame = frame.parent
    return frame


class _ProfileContext(ContextDecorator):
    """Context manager and decorator returned by :meth:`TickTock.profile`."""

    def __init__(self, tt: "TickTock", name: str, hits: int, disable: bool):
        self._tt = tt
        self._name = name
        self._hits = hits
        self._disable = disable
        self._frame: _Frame | None = None

    @override
    def _recreate_cm(self) -> "_ProfileContext":
        return _ProfileContext(self._tt, self._name, self._hits, self._disable)

    @override
    def __call__(self, func: _F) -> _F:
        if not inspect.iscoroutinefunction(func):
            return super().__call__(func)

        # Calling a coroutine function only creates the coroutine, so the profile must cover awaiting it instead
        @wraps(func)
        async def inner(*args: object, **kwargs: object) -> object:
            with self._recreate_cm():
                return await func(*args, **kwargs)

        return inner  # pyright: ignore[reportReturnType]

    def __enter__(self) -> None:
        if self._frame is not None:
            raise TickTockException("A profile context cannot be entered while it is already active")
        self._frame, _ = self._tt._start_profile(self._name, hits=self._hits, disable=self._disable)

    def __exit__(self, *_: object) -> None:
        frame = self._frame
        assert frame is not None
        self._frame = None
        self._tt._end_profile(frame)


class TickTock:
    """Simple time taker inspired by Matlab Tic, Toc, which also comes with powerful, easy-to-use profiling tooling.

    It is possible to import ``TT`` directly as a global instance for convenience, or import ``TickTock`` and create a new instance.

    Profiling is safe to use from multiple threads and asyncio tasks. Each thread or task keeps its own stack of active
    profiles, and profiles with the same name and parent are merged into one, summing hits and runtimes across threads.
    A profile started in a new thread is therefore a top-level profile, unless the context of the starting code is
    propagated to it, as is done by ``asyncio`` tasks, ``asyncio.to_thread``, and ``contextvars.copy_context().run``.
    New threads also inherit the context when ``sys.flags.thread_inherit_context`` is set, which is the default on
    free-threaded builds of Python 3.14 and later.
    As runtimes are summed across threads, the time of child profiles can exceed that of their parent.

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

        # The same goes for very quick loops.
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
        self._intervals = _Intervals()
        self._tree = _Tree()
        # Guards creation and removal of profiles and updates of their measurements
        # Reentrant, so profiling from a signal handler or garbage collection callback in the thread holding the lock
        # cannot deadlock. Such a nested profile may still see a profile that is only partially created
        self._lock = threading.RLock()
        # Innermost active profile in the current context
        self._stack: ContextVar[_Frame | None] = ContextVar("ticktock_stack", default=None)

    @property
    def _root_profiles(self) -> list[Profile]:
        return self._tree.root_profiles

    def _top(self) -> _Frame | None:
        """Return the innermost active frame in the current context."""
        return _skip_closed(self._stack.get())

    def tick(self, key: Hashable = None):
        """Start a timer identified by an optional hashable key."""
        self._tick_starts[key] = perf_counter()

    def tock(self, key: Hashable = None) -> float:
        """End the timer identified by ``key`` and return the elapsed time in seconds."""
        end = perf_counter()
        if key not in self._tick_starts:
            raise TickTockException(f"A timer for the given key ({key}) has not been started with .tick()")
        return end - self._tick_starts[key]

    def _start_profile(self, name: str, *, hits: int, disable: bool) -> tuple[_Frame, bool]:
        """Start a profile in the current context and return its frame and whether the profile was new."""
        top = self._top()
        tree = self._tree
        # A profile that was started before the tree was reset is no longer part of it, so new profiles start from the root
        parent = top if top is not None and top.tree is tree else None
        index = tree.root_index if parent is None else parent.profile._child_index
        disabled = disable or (top is not None and top.disabled)
        profile_was_new = False
        # Lookup and counting happen together, so a profile cannot be removed by profile_next in between
        with self._lock:
            profile = index.get(name)
            if profile is None:
                profile_was_new = True
                profile = _create_profile(tree, name, None if parent is None else parent.profile)
            if not disabled:
                profile.nhits += hits
                profile._active_hits += hits

        frame = _Frame(profile, top, tree, disabled, hits)
        frame.token = self._stack.set(frame)
        frame.start = perf_counter()
        return frame, profile_was_new

    def _end_profile(self, frame: _Frame, *, completed: bool = True):
        """End the hit represented by ``frame``. If not ``completed``, the hit is undone instead of measured."""
        end = perf_counter()
        if not frame.disabled:
            profile = frame.profile
            with self._lock:
                profile._active_hits -= frame.hits
                if completed:
                    profile.total_runtime += end - frame.start
                else:
                    profile.nhits -= frame.hits

        frame.closed = True
        top = self._stack.get()
        if top is frame:
            assert frame.token is not None
            try:
                self._stack.reset(frame.token)
            except ValueError:
                # The frame was started in a different context
                self._stack.set(frame.parent)
            return
        # Ended out of order, e.g. by interleaved generators. Profiles started after this one are dropped from the
        # stack, so new profiles do not nest ever deeper. Dropped profiles are still measured when they end
        while top is not None and top is not frame:
            top = top.parent
        if top is not None:
            self._stack.set(_skip_closed(frame.parent))

    def profile(self, name: str, *, hits: int = 1, disable: bool = False) -> _ProfileContext:
        """Start a profile with given name.

        Optionally it is possible to register this as several hits that sum to the total time.
        This is useful when profiling a very large number of quick operations.
        The following two snippets are functionally identical:

        .. code-block:: python

            for i in range(5):
                with TT.profile("Operation"):
                    ...

            with TT.profile("Operation", hits=5):
                for i in range(5):
                    ...

        If ``disable`` is True, the profile, as well as all child profiles will not be counted.

        The returned context manager can also be used as a function decorator, in which case each call is a hit.
        For ``async`` functions, the profile covers awaiting the call:

        .. code-block:: python

            @TT.profile("Operation")
            def operation():
                ...

            @TT.profile("Async operation")
            async def async_operation():
                ...

        Calling a generator function only creates the generator, so decorating one profiles nothing useful.
        Use :meth:`profile_loop` or :meth:`profile_next` for generators instead.

        The new profile is nested under the innermost active profile of the current thread or asyncio task.
        If a profile ends while profiles started inside it are still active, as can happen with interleaved generators,
        those profiles are still measured when they end, but new profiles are no longer nested under them.
        """
        return _ProfileContext(self, name, hits, disable)

    def profile_loop(self, name: str, iterable: Iterable[T], *, hits_per_element: int = 1, disable: bool = False) -> Iterator[T]:
        """Wrap an iterable and profile the time spent processing each yielded element.

        The profile remains active while the caller processes the yielded element.
        Conceptually, this method is quite similar to ``tqdm``, just with elementwise profiling instead of a progress bar.
        It allows the example in :meth:`profile` to be replaced with

        .. code-block:: python

            for i in TT.profile_loop("Operation", range(5)):
                ...
        """
        for element in iterable:
            with self.profile(name, hits=hits_per_element, disable=disable):
                yield element

    def profile_next(self, name: str, iterator: Iterator[T], *, hits_per_element: int = 1, disable: bool = False) -> Iterator[T]:
        """Wrap an iterator and profile the time it takes to retrieve each element.

        The profile covers each call to ``next(iterator)`` and ends before the element
        is yielded to the caller. The call that raises ``StopIteration`` is not counted.
        Pass an iterator explicitly, for example with ``iter(iterable)``.

        This method makes profiling lazy iterators much more convenient. Instead of

        .. code-block:: python

            while True:
                try:
                    with TT.profile("Get element"):
                        element = next(dataloader)
                except StopIteration:
                    break
                ...

        it is possible to instead write

        .. code-block:: python

            for element in TT.profile_next("Get element", iter(dataloader)):
                ...
        """
        while True:
            frame, profile_was_new = self._start_profile(name, hits=hits_per_element, disable=disable)
            try:
                element = next(iterator)
            except StopIteration:
                # The exhaustion check starts a profile but does not produce an element, so undo that hit
                self._end_profile(frame, completed=False)
                if profile_was_new:
                    self._remove_unused_profile(frame)
                return
            except BaseException:
                self._end_profile(frame)
                raise
            self._end_profile(frame)
            yield element

    def _remove_unused_profile(self, frame: _Frame):
        """Remove the profile of ``frame`` from its tree if it has no hits and no children."""
        profile = frame.profile
        with self._lock:
            if profile.nhits or profile.children:
                return
            if profile.parent is None:
                del frame.tree.root_index[profile.name]
                frame.tree.root_profiles.remove(profile)
            else:
                del profile.parent._child_index[profile.name]
                profile.parent.children.remove(profile)

    def reset(self):
        """Stop all timing and profiling and clear all profiles and measurements.

        Resetting is allowed while this instance is registered by :meth:`as_active`; the
        active registration remains until that context exits. Resetting while a profile
        context is in progress in the current thread or task raises :class:`TickTockException`
        without changing state. Profiles in progress in other threads or tasks are not
        included in the new, empty profile tree, and profiles started inside them
        afterwards become top-level profiles.
        """
        self.reset_profiles()
        self._tick_starts = dict()
        self._intervals = _Intervals()

    def reset_profiles(self):
        """Reset profiles while leaving ``tick``/``tock`` and ``do_at_interval`` timers intact.

        The same restrictions as :meth:`reset` apply: this is allowed while registered
        by :meth:`as_active`, but raises :class:`TickTockException` during a profile
        context.
        """
        if self._top() is not None:
            raise TickTockException("Cannot reset TickTock while profiling is active")
        self._tree = _Tree()

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

        Intervals are tracked separately for each thread, so calls with the same key in different threads do not affect each other.
        Asyncio tasks running in the same thread, and thus the same event loop, share intervals.
        This differs from :meth:`tick` and :meth:`tock`, whose timers are shared by all threads.
        """
        starts = self._intervals.starts
        now = perf_counter()
        if key not in starts:
            starts[key] = now
            return also_first
        if now - starts[key] >= interval:
            starts[key] = now
            return True
        return False

    def fuse(self, tt: "TickTock"):
        """Fuse a TickTock instance into self.

        The profile trees do not need to match. Profiles only in ``tt`` are added to self after existing profiles at
        the same level. Only completed hits of ``tt`` are added.
        """
        if self._top() is not None or tt._top() is not None:
            raise TickTockException("Unable to fuse while some profiles are still unfinished")

        with tt._lock:
            # Unlike iter_profiles, this includes profiles without hits, so that parents always precede their children
            other = [(p, p._completed_hits(), p.total_runtime) for root in tt._root_profiles for p in root._walk()]
        with self._lock:
            fused: dict[int, Profile] = dict()  # Profiles in tt by id to the corresponding profiles in self
            for profile, nhits, total_runtime in other:
                parent = None if profile.parent is None else fused[id(profile.parent)]
                existing = (self._tree.root_index if parent is None else parent._child_index).get(profile.name)
                if existing is None:
                    existing = _create_profile(self._tree, profile.name, parent)
                existing.nhits += nhits
                existing.total_runtime += total_runtime
                fused[id(profile)] = existing

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
        return ticktock

    @override
    def __getstate__(self) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
        # Locks, context variables, and thread-locals cannot be copied, so only measurements are kept.
        # That means hits in progress and the do_at_interval timers of other threads are not included
        with self._lock:
            root_profiles = deepcopy(self._tree.root_profiles)
        return {
            "_tick_starts": dict(self._tick_starts),
            "_interval_starts": dict(self._intervals.starts),
            "_root_profiles": root_profiles,
        }

    def __setstate__(self, state: dict[str, Any]):  # pyright: ignore[reportExplicitAny]
        self.__init__()
        self._tick_starts = state["_tick_starts"]
        self._intervals.starts.update(state.get("_interval_starts", dict()))
        self._tree.root_profiles = state["_root_profiles"]
        self._tree.root_index = {profile.name: profile for profile in self._tree.root_profiles}
        for root in self._tree.root_profiles:
            for profile in root._walk():
                # The copy has no active profiles, so hits in progress are discarded
                profile.nhits -= getattr(profile, "_active_hits", 0)
                profile._active_hits = 0
                profile._child_index = {child.name: child for child in profile.children}

    @staticmethod
    def _stringify_time_with_alignment(dt: float, unit: tuple[str, float]) -> str:
        return f"{dt / unit[1]:,.2f} {unit[0]:>2}"

    @override
    def __str__(self) -> str:
        """Return a pretty table representation of the profile tree.

        The table lists each profile with its total time, its percentage of the parent's
        time (or of the overall time for root profiles), the number of hits, and the average
        time per hit. Profiles are shown depth-first and indented by depth. Suitable time
        units are detected automatically per value. Raises if profiling is still ongoing in
        the current thread or task.

        Profiles in progress in other threads are included, but only their completed hits
        are counted in the hits and average columns. When a parent has no completed time
        yet, the percentage of its children is shown as "-".
        """
        if self._top() is not None:
            raise ValueError("TickTock instance cannot be stringified while profiling is still ongoing. Please end all profiles first")

        with self._lock:
            measurements = [(profile, profile.sum(), profile._completed_hits()) for profile in self.iter_profiles()]
        sums = {id(profile): psum for profile, psum, _ in measurements}
        total_time = sum(psum for profile, psum, _ in measurements if profile.parent is None)

        table = Table()
        h = ["Profile", "Total time", "Percentage", "Hits", "Average"]
        table.add_header(h)
        for profile, psum, nhits in measurements:
            pmean = psum / nhits if nhits else 0
            reference = sums[id(profile.parent)] if profile.parent else total_time
            row = [
                "  " * profile.depth + profile.name,
                self._stringify_time_with_alignment(psum, _get_smallest_suitable_unit(psum)),
                ("%.2f" % (100 * psum / reference) if reference else "-") + (" <" if profile.depth else "") + "--" * (profile.depth - 1),
                f"{nhits:,}",
                self._stringify_time_with_alignment(pmean, _get_smallest_suitable_unit(pmean)),
            ]
            table.add_row(row, [True] + [False] * (len(row) - 1))

        return str(table)

    def iter_profiles(self) -> Iterator[Profile]:
        """Recursively return all profiles in the tree.

        They are ordered in a depth-first manner rather than breadth-first.
        The profiles are not locked, so this is not a consistent snapshot while other threads are profiling.
        """
        for profile in self._root_profiles:
            yield from profile

    @property
    def has_profiles(self) -> bool:
        """Return True if any profiling has been performed."""
        return len(self._root_profiles) > 0

    @contextmanager
    def as_active(self):
        """Set the ``TickTock`` instance as the active instance in the current thread or asyncio task.

        It can then be retrieved with :func:`get_active_ticktock`.
        Calling :meth:`reset` or :meth:`reset_profiles` inside this context does not
        unset the active instance. Those methods still raise if a profile context is
        currently in progress.
        The active instance is propagated to code running in a copy of the current context,
        such as asyncio tasks and ``asyncio.to_thread``, but not to plain new threads.
        Such code cannot set another active instance while the propagated one is active.
        """
        if _active_ticktock.get() is not None:
            raise TickTockException(
                f"An active TickTock instance has already been set in the current context (thread {threading.current_thread().name})"
            )
        token = _active_ticktock.set(self)
        try:
            yield
        finally:
            try:
                _active_ticktock.reset(token)
            except ValueError:
                # Exited in a different context than entered, e.g. by closing a generator or async fixture elsewhere
                _active_ticktock.set(None)


def get_active_ticktock() -> TickTock:
    """Return the active ``TickTock`` instance in the current thread or asyncio task (as set by :meth:`TickTock.as_active`).

    If no active ``TickTock`` is set, a new ``TickTock`` instance is returned.
    This allows normal profiling usage without having to care if it's actually used or not.
    """
    ticktock = _active_ticktock.get()
    return ticktock if ticktock is not None else TickTock()


# Globally accessible default instance
# It suffices to use this for most cases
TT = TickTock()
