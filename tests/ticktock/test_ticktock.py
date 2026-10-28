import asyncio
import contextvars
import gc
import inspect
import pickle
import sys
import warnings
import weakref
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from copy import deepcopy
from threading import Barrier, Event, Thread, current_thread

import pytest

from pelutils.ticktock import TT, Profile, TickTock, TickTockException, get_active_ticktock
from pelutils.ticktock._ticktock import _get_smallest_suitable_unit


def active_profiles(tt: TickTock) -> list[Profile]:
    """Return the active profiles in the current context, outermost first."""
    profiles = list()
    frame = tt._top()
    while frame is not None:
        if not frame.closed:
            profiles.append(frame.profile)
        frame = frame.parent
    return profiles[::-1]


def test_ticktock():
    """Test base functionality."""
    tt = TickTock()
    tt.tick()
    assert isinstance(tt.tock(), float)


def test_ticktock_id():
    tt = TickTock()

    # Test that different ids behave as expected
    tt.tick()
    tt.tick("inner")
    time_inner = tt.tock("inner")
    time_outer = tt.tock()
    time_inner2 = tt.tock("inner")

    assert time_inner < time_outer
    assert time_inner < time_inner2

    # Test that swapping ids still leads to expected behaviour
    tt.tick("inner")
    tt.tick()
    time_inner = tt.tock()
    time_outer = tt.tock("inner")
    time_inner2 = tt.tock()

    assert time_inner < time_outer
    assert time_inner < time_inner2

    # Test that unknown and unhashable ids cause correct exceptions
    with pytest.raises(TickTockException):
        tt.tock("outer")
    with pytest.raises(TypeError):
        tt.tick([1])
    with pytest.raises(TypeError):
        tt.tock([1])
    tt.reset()
    assert len(tt._tick_starts) == 0


def test_profiling():
    """Test profiling"""
    tt = TickTock()
    with tt.profile("p"):
        pass

    with tt.profile("pp"):
        pass

    with tt.profile("p"):
        with tt.profile("pp"):
            with tt.profile("ppp"):
                pass
            assert len(active_profiles(tt)) == 2


def test_context_profiling():
    """Test profiling with context"""
    tt = TickTock()

    with tt.profile("Hello there"):
        assert len(active_profiles(tt)) == 1
        with tt.profile("General Kenobi!"):
            assert len(active_profiles(tt)) == 2
    assert not active_profiles(tt)


def test_fuse():
    tt1 = TickTock()
    tt2 = TickTock()

    with tt1.profile("p"):
        with tt2.profile("p"):
            with tt2.profile("pp"):
                pass
        with pytest.raises(TickTockException):
            tt1.fuse(tt2)
    # The profile trees do not need to match
    tt1.fuse(tt2)

    assert len(tt1._root_profiles) == 1

    with pytest.raises(ValueError):
        TickTock.fuse_multiple((tt1, tt1))

    tt1 = deepcopy(tt2)
    tt1 = TickTock.fuse_multiple((tt1, tt2))
    for p1, p2 in zip(tt1.iter_profiles(), tt2.iter_profiles(), strict=True):
        assert p1.total_runtime == pytest.approx(2 * p2.total_runtime)

    tt = TickTock.fuse_multiple([])
    assert len(list(tt.iter_profiles())) == 0


def test_fuse_different_trees():
    def make(*paths: tuple[str, ...]) -> TickTock:
        tt = TickTock()
        for path in paths:
            with ExitStack() as stack:
                for name in path:
                    stack.enter_context(tt.profile(name))
        return tt

    def tree(tt: TickTock) -> list[tuple[str, int, int]]:
        return [(profile.name, profile.depth, profile.nhits) for profile in tt.iter_profiles()]

    # Other is a superset of self, so its new profiles are added after the existing ones at the same level
    small = make(("a", "b"))
    small.fuse(make(("c",), ("a", "d"), ("a", "b", "e")))
    assert tree(small) == [("a", 0, 3), ("b", 1, 2), ("e", 2, 1), ("d", 1, 1), ("c", 0, 1)]

    # Other is a subset of self
    large = make(("a", "b"), ("c",))
    large.fuse(make(("c",)))
    assert tree(large) == [("a", 0, 1), ("b", 1, 1), ("c", 0, 2)]

    # Neither is a subset of the other
    disjoint = make(("a",))
    disjoint.fuse(make(("b",)))
    assert tree(disjoint) == [("a", 0, 1), ("b", 0, 1)]

    # Profiles with the same name at different paths are different profiles
    overlapping = make(("a", "b"), ("d",))
    overlapping.fuse(make(("b",), ("a", "c"), ("d", "b")))
    assert tree(overlapping) == [("a", 0, 2), ("b", 1, 1), ("c", 1, 1), ("d", 0, 2), ("b", 1, 1), ("b", 0, 1)]

    fused = TickTock.fuse_multiple([make(("a",)), make(("a", "b")), make(("c",))])
    assert tree(fused) == [("a", 0, 2), ("b", 1, 1), ("c", 0, 1)]

    # Profiles without hits remain hidden after fusing
    with_disabled = make(("x",))
    with with_disabled.profile("z", disable=True):
        pass
    with_disabled.fuse(make(("x",), ("y",)))
    assert tree(with_disabled) == [("x", 0, 2), ("y", 0, 1)]
    other_disabled = TickTock()
    with other_disabled.profile("w", disable=True):
        pass
    with_disabled.fuse(other_disabled)
    assert tree(with_disabled) == [("x", 0, 2), ("y", 0, 1)]

    # Fusing with self doubles all measurements
    tt = make(("a", "b"))
    tt.fuse(tt)
    assert tree(tt) == [("a", 0, 2), ("b", 1, 2)]


def test_fuse_adds_completed_hits_of_new_profiles():
    tt = TickTock()
    with tt.profile("a"):
        pass
    started = Event()
    release = Event()

    def work():
        with tt.profile("b"):
            pass
        with tt.profile("b"):
            started.set()
            release.wait()

    thread = Thread(target=work)
    thread.start()
    assert started.wait(timeout=1)
    target = TickTock()
    with target.profile("a"):
        pass
    try:
        target.fuse(tt)
    finally:
        release.set()
        thread.join()
    # "b" is created in target by fusing, and only its completed hit is added
    profiles = {profile.name: profile for profile in target.iter_profiles()}
    assert (profiles["b"].nhits, profiles["b"]._active_hits) == (1, 0)
    assert profiles["b"].mean() == pytest.approx(profiles["b"].total_runtime)


def test_same_name_in_nested_tree():
    tt = TickTock()
    for _ in range(2):
        with tt.profile("a"):
            with tt.profile("b"):
                with tt.profile("a"):
                    pass
    profiles = list(tt.iter_profiles())
    assert [(profile.name, profile.depth, profile.nhits) for profile in profiles] == [("a", 0, 2), ("b", 1, 2), ("a", 2, 2)]
    assert profiles[0] is not profiles[2]
    assert profiles[2].parent is profiles[1]


def test_profile_while_lock_is_held():
    """Profiling from e.g. a signal handler that interrupts the thread holding the lock must not deadlock."""
    tt = TickTock()

    def profile_with_lock_held():
        with tt._lock, tt.profile("reentrant"):
            pass

    thread = Thread(target=profile_with_lock_held, daemon=True)
    thread.start()
    thread.join(timeout=1)
    assert not thread.is_alive()
    assert next(tt.iter_profiles()).nhits == 1


def test_global_tt():
    assert isinstance(TT, TickTock)


def test_throw():
    tt = TickTock()
    with tt.profile("Hello there"), pytest.raises(ValueError):
        str(tt)


def test_smallest_suitable_unit():
    assert _get_smallest_suitable_unit(1e-10) == ("ns", 1e-9)
    assert _get_smallest_suitable_unit(1e-8) == ("ns", 1e-9)
    assert _get_smallest_suitable_unit(1e-6) == ("us", 1e-6)
    assert _get_smallest_suitable_unit(2e-6) == ("us", 1e-6)
    assert _get_smallest_suitable_unit(1e-3) == ("ms", 1e-3)
    assert _get_smallest_suitable_unit(2e-3) == ("ms", 1e-3)
    assert _get_smallest_suitable_unit(1) == ("s", 1)
    assert _get_smallest_suitable_unit(2) == ("s", 1)
    assert _get_smallest_suitable_unit(3600) == ("h", 3600)
    assert _get_smallest_suitable_unit(1e10) == ("h", 3600)


def test_reset():
    tt = TickTock()
    assert len(tt._tick_starts) == 0
    tt.tick()
    tt.reset()
    assert len(tt._tick_starts) == 0
    with pytest.raises(TickTockException):
        tt.tock()

    with tt.profile("p"):
        assert len(active_profiles(tt)) == 1
    assert len(tt._root_profiles) == 1
    tt.reset()
    assert len(tt._root_profiles) == 0
    assert not active_profiles(tt)

    tt.tick("active reset guard")
    with tt.profile("pp"):
        with pytest.raises(TickTockException):
            tt.reset()
        with pytest.raises(TickTockException):
            tt.reset_profiles()
    assert [profile.name for profile in tt.iter_profiles()] == ["pp"]
    tt.tock("active reset guard")

    tt.tick("abc")
    tt.tick("abc2")
    tt.reset_profiles()
    tt.tock("abc")
    tt.tock("abc2")
    with pytest.raises(TickTockException):
        tt.tock("abc3")


def test_reset_while_as_active():
    tt = TickTock()
    with tt.as_active():
        with tt.profile("before reset"):
            pass
        with tt.profile("reset rejected during profile"):
            with pytest.raises(TickTockException):
                tt.reset()
            with pytest.raises(TickTockException):
                tt.reset_profiles()
            assert get_active_ticktock() is tt

        tt.tick("timer")
        tt.reset()

        assert get_active_ticktock() is tt
        assert not tt.has_profiles
        with pytest.raises(TickTockException):
            tt.tock("timer")

        with tt.profile("after reset"):
            pass
        assert [profile.name for profile in tt.iter_profiles()] == ["after reset"]

    assert get_active_ticktock() is not tt


def test_reset_profiles_while_as_active():
    tt = TickTock()
    tt.tick("timer")
    with tt.profile("before reset"):
        pass

    with tt.as_active():
        tt.reset_profiles()

        assert get_active_ticktock() is tt
        assert not tt.has_profiles
        assert tt.tock("timer") >= 0

        with tt.profile("after reset"):
            pass
        assert [profile.name for profile in tt.iter_profiles()] == ["after reset"]

    assert get_active_ticktock() is not tt


def test_profiles_with_same_name():
    tt = TickTock()

    with tt.profile("a"):
        pass
    with tt.profile("a"):
        pass

    with tt.profile("b"):
        with tt.profile("a"):
            pass
        with tt.profile("a"):
            pass
        with tt.profile("a"):
            pass

    with tt.profile("b"):
        with tt.profile("a"):
            pass

    with tt.profile("a"):
        pass

    root_profiles = list(tt.iter_profiles())
    assert root_profiles[0].name == "a"
    assert root_profiles[0].depth == 0
    assert root_profiles[0].nhits == 3

    assert root_profiles[1].name == "b"
    assert root_profiles[1].depth == 0
    assert root_profiles[1].nhits == 2

    assert root_profiles[2].name == "a"
    assert root_profiles[2].depth == 1
    assert root_profiles[2].nhits == 4


def test_disable():
    tt = TickTock()
    with tt.profile("111"):
        with tt.profile("222", disable=True):
            with tt.profile("333"):
                pass
            with tt.profile("444"):
                pass
            with tt.profile("555"):
                pass

    with tt.profile("111"):
        with tt.profile("222"):
            with tt.profile("333"):
                pass
            with tt.profile("444"):
                pass
            with tt.profile("666", disable=True):
                pass

    pname_depth_to_profile = {(profile.name, profile.depth): profile for profile in tt.iter_profiles()}
    assert pname_depth_to_profile["111", 0].nhits == 2
    assert pname_depth_to_profile["222", 1].nhits == 1
    assert pname_depth_to_profile["333", 2].nhits == 1
    assert pname_depth_to_profile["444", 2].nhits == 1
    with pytest.raises(KeyError):
        # This has zero hits due to disabled parent, so it shouldn't be present here
        pname_depth_to_profile["555", 2]
    with pytest.raises(KeyError):
        # This has zero hits due to being disabled, so it shouldn't be present here
        assert pname_depth_to_profile["666", 2].nhits == 0


def test_profile_loop():
    tt = TickTock()
    for _i in tt.profile_loop("outer", range(5), hits_per_element=3):
        for _ in tt.profile_loop("inner", range(4), hits_per_element=2):
            pass

    profiles = {profile.name: profile for profile in tt.iter_profiles()}
    assert profiles["outer"].nhits == 15
    assert profiles["inner"].nhits == 40
    assert not active_profiles(tt)


def test_profile_loop_generator_close():
    tt = TickTock()
    profiled = tt.profile_loop("loop", range(5))
    assert next(profiled) == 0
    assert len(active_profiles(tt)) == 1

    profiled.close()
    assert not active_profiles(tt)


def test_profile_next():
    tt = TickTock()
    assert list(tt.profile_next("fetch", iter(range(5)), hits_per_element=3)) == list(range(5))

    profile = next(tt.iter_profiles())
    assert profile.nhits == 15
    assert profile.total_runtime > 0
    assert not active_profiles(tt)


def test_profile_next_empty_and_nested_iterator():
    tt = TickTock()
    assert list(tt.profile_next("empty", iter(()))) == []
    assert not tt.has_profiles

    with tt.profile("parent"):
        assert list(tt.profile_next("child", iter(()))) == []

    parent = next(tt.iter_profiles())
    assert parent.children == []


def test_profile_next_disabled_exhaustion_does_not_change_profile():
    tt = TickTock()
    with tt.profile("fetch"):
        pass
    profile = next(tt.iter_profiles())
    nhits = profile.nhits
    total_runtime = profile.total_runtime

    assert list(tt.profile_next("fetch", iter(()), disable=True)) == []
    assert profile.nhits == nhits
    assert profile.total_runtime == total_runtime

    disabled = TickTock()
    assert list(disabled.profile_next("fetch", iter(()), disable=True)) == []
    assert not disabled.has_profiles


def test_profile_next_iterator_exception():
    class ExplodingIterator:
        def __next__(self):
            raise RuntimeError("iterator failed")

    tt = TickTock()
    with pytest.raises(RuntimeError, match="iterator failed"):
        list(tt.profile_next("fetch", ExplodingIterator()))
    assert not active_profiles(tt)


def test_do_at_interval():
    tt = TickTock()
    tt.tick()
    num_a = 0
    num_b = 0
    while tt.tock() < 0.1:
        if tt.do_at_interval(0.03, "a"):
            num_a += 1
        if tt.do_at_interval(0.07, "b"):
            num_b += 1
    assert num_a >= 2
    assert num_b == 1

    tt.reset()
    tt.tick()
    num_a = 0
    num_b = 0
    while tt.tock() < 0.1:
        if tt.do_at_interval(0.03, "a", also_first=True):
            num_a += 1
        if tt.do_at_interval(0.07, "b", also_first=True):
            num_b += 1
    assert num_a >= 3
    assert num_b == 2


def test_profile_in_other_thread():
    tt = None

    def set_tt():
        nonlocal tt
        tt = TickTock()

    thread = Thread(target=set_tt)
    thread.start()
    thread.join()

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with tt.profile("abc"):
            pass
    assert next(tt.iter_profiles()).nhits == 1


def test_print(capfd: pytest.CaptureFixture):
    tt = TickTock()
    with tt.profile("a"):
        pass

    with tt.profile("b"):
        with tt.profile("a"):
            pass

    print(tt)
    stdout, _ = capfd.readouterr()
    conditions = [False] * 4
    for line in stdout.splitlines():
        if line.startswith("Profile"):
            conditions[0] = True
        elif line.startswith("a  "):
            conditions[1] = True
        elif line.startswith("b  "):
            conditions[2] = True
        elif line.startswith("  a"):
            conditions[3] = True

    assert all(conditions)


def test_exit_in_nested():
    tt = TickTock()
    with pytest.raises(ZeroDivisionError), tt.profile("aælkjdfæakdjsf"):
        0 / 0  # noqa: B018
    # with tt.profile construct was used, so expect no unclosed profiles
    assert not active_profiles(tt)

    tt = TickTock()
    with pytest.raises(ZeroDivisionError):
        with tt.profile("sada"):
            with tt.profile("adfsadlæfj"):
                0 / 0  # noqa: B018

    # with tt.profile construct was used, so expect no unclosed profiles
    assert not active_profiles(tt)

    tt = TickTock()
    with pytest.raises(ZeroDivisionError):
        with tt.profile("adsfad"):
            with tt.profile("asdasd"):
                with tt.profile("sada"):
                    with tt.profile("aæsldfjka"):
                        0 / 0  # noqa: B018

    # with tt.profile construct was used, so expect no unclosed profiles
    assert not active_profiles(tt)


def test_profile(capfd: pytest.CaptureFixture):
    profile = Profile("tester", 0, None)
    assert profile.nhits == 0
    assert profile.mean() == 0

    print(profile)
    stdout, _ = capfd.readouterr()
    assert stdout.strip() == "tester"

    # Profiles are equal when their name and path are equal
    parent = Profile("parent", 0, None)
    same_parent = Profile("parent", 0, None)
    assert parent == same_parent and hash(parent) == hash(same_parent)
    assert Profile("tester", 1, parent) == Profile("tester", 1, same_parent)
    assert profile != Profile("tester", 1, parent)
    assert profile != "tester"


def test_active():
    tt = TickTock()
    assert not tt.has_profiles
    with tt.profile("test"):
        pass
    assert tt.has_profiles


def test_active_ticktock():
    first = get_active_ticktock()
    second = get_active_ticktock()
    assert isinstance(first, TickTock)
    assert first is not second

    tt = TickTock()
    other = TickTock()
    with tt.as_active():
        assert get_active_ticktock() is tt
        with pytest.raises(TickTockException):
            with other.as_active():
                pass
        assert get_active_ticktock() is tt
    assert get_active_ticktock() is not tt


def test_active_ticktock_cleanup_on_exception():
    tt = TickTock()
    with pytest.raises(RuntimeError, match="failed"):
        with tt.as_active():
            raise RuntimeError("failed")

    assert get_active_ticktock() is not tt
    with tt.as_active():
        assert get_active_ticktock() is tt


def test_active_ticktock_is_task_local():
    async def task(tt: TickTock, results: list[bool]):
        with tt.as_active():
            await asyncio.sleep(0.01)
            results.append(get_active_ticktock() is tt)

    async def main():
        results = list()
        await asyncio.gather(*(task(TickTock(), results) for _ in range(3)))
        return results

    assert asyncio.run(main()) == [True] * 3

    tt = TickTock()

    async def inherit():
        return get_active_ticktock() is tt

    async def parent():
        with tt.as_active():
            return await asyncio.create_task(inherit())

    assert asyncio.run(parent())


def test_active_ticktock_nesting_in_propagated_context():
    tt = TickTock()
    other = TickTock()

    async def nested():
        with pytest.raises(TickTockException, match="current context"):
            with other.as_active():
                pass

    async def main():
        with tt.as_active():
            await asyncio.create_task(nested())
            await asyncio.to_thread(contextvars.copy_context().run, lambda: None)

    asyncio.run(main())
    assert get_active_ticktock() is not tt


def test_active_ticktock_exited_in_other_context():
    tt = TickTock()

    def active():
        with tt.as_active():
            yield

    def scenario():
        generator = active()
        next(generator)

        def close_and_check():
            generator.close()
            return get_active_ticktock() is not tt

        assert contextvars.copy_context().run(close_and_check)

    # Run in a copy, as the instance stays active in the context that entered
    contextvars.copy_context().run(scenario)


def test_active_ticktock_is_thread_local():
    active = Event()
    release = Event()
    tt = TickTock()

    def activate():
        with tt.as_active():
            active.set()
            release.wait()

    thread = Thread(target=activate)
    thread.start()
    assert active.wait(timeout=1)
    assert get_active_ticktock() is not tt
    release.set()
    thread.join(timeout=1)
    assert not thread.is_alive()


def _run_threads(target, n: int):
    threads = [Thread(target=target) for _ in range(n)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def test_threads_share_profiles():
    tt = TickTock()
    nthreads, nhits = 8, 2000

    def work():
        for _ in range(nhits):
            with tt.profile("outer"):
                with tt.profile("inner", hits=2):
                    pass

    _run_threads(work, nthreads)

    profiles = list(tt.iter_profiles())
    assert [(profile.name, profile.depth) for profile in profiles] == [("outer", 0), ("inner", 1)]
    assert len(list(tt.iter_profiles())) == 2
    assert profiles[0].nhits == nthreads * nhits
    assert profiles[1].nhits == 2 * nthreads * nhits
    assert all(profile._active_hits == 0 for profile in profiles)
    assert profiles[0].total_runtime >= profiles[1].total_runtime > 0
    assert not active_profiles(tt)


def test_threads_create_profile_once():
    tt = TickTock()
    nthreads = 16
    barrier = Barrier(nthreads)

    def work():
        barrier.wait()
        with tt.profile("racing"):
            pass

    _run_threads(work, nthreads)
    assert len(tt._root_profiles) == 1
    assert tt._root_profiles[0].nhits == nthreads


def test_thread_profile_is_root():
    tt = TickTock()

    def work():
        with tt.profile("worker"):
            pass

    with tt.profile("main"):
        thread = Thread(target=work)
        thread.start()
        thread.join()
        with ThreadPoolExecutor(1) as executor:
            executor.submit(work).result()

    # Threads inherit the context of the starting thread when enabled, which is the default on free-threaded builds
    worker_depth = 1 if getattr(sys.flags, "thread_inherit_context", False) else 0
    assert [(profile.name, profile.depth, profile.nhits) for profile in tt.iter_profiles()] == [("main", 0, 1), ("worker", worker_depth, 2)]


def test_context_propagation_nests():
    tt = TickTock()

    def work():
        with tt.profile("worker"):
            assert [profile.name for profile in active_profiles(tt)] == ["main", "worker"]

    async def main():
        with tt.profile("main"):
            await asyncio.to_thread(work)
            contextvars.copy_context().run(work)

    asyncio.run(main())
    assert [(profile.name, profile.depth, profile.nhits) for profile in tt.iter_profiles()] == [("main", 0, 1), ("worker", 1, 2)]


def test_asyncio_tasks():
    tt = TickTock()
    ntasks, nhits = 10, 20

    async def task(i: int):
        for _ in range(nhits):
            with tt.profile(f"task {i}"):
                await asyncio.sleep(0)
                with tt.profile("child"):
                    await asyncio.sleep(0)
                    assert [profile.name for profile in active_profiles(tt)] == [f"task {i}", "child"]

    async def main():
        await asyncio.gather(*(task(i) for i in range(ntasks)))

    asyncio.run(main())
    expected = list()
    for i in range(ntasks):
        expected += [(f"task {i}", 0, nhits), ("child", 1, nhits)]
    assert [(profile.name, profile.depth, profile.nhits) for profile in tt.iter_profiles()] == expected


def test_interleaved_generators():
    tt = TickTock()
    for _ in zip(tt.profile_loop("a", range(3)), tt.profile_loop("b", range(3)), strict=True):
        pass

    hits = {"a": 0, "b": 0}
    for profile in tt.iter_profiles():
        hits[profile.name] += profile.nhits
        assert profile._active_hits == 0
    assert hits == {"a": 3, "b": 3}
    assert not active_profiles(tt)

    # The tree must stay bounded no matter how long the generators run
    tt = TickTock()
    for _ in zip(tt.profile_loop("a", range(1000)), tt.profile_loop("b", range(1000)), strict=True):
        pass
    assert max(profile.depth for profile in tt.iter_profiles()) <= 1
    assert sum(profile.nhits for profile in tt.iter_profiles()) == 2000


def test_out_of_order_exit():
    tt = TickTock()
    a = tt.profile("a")
    b = tt.profile("b")
    a.__enter__()
    b.__enter__()
    a.__exit__(None, None, None)
    # Profiles started after an out-of-order exit no longer nest under the dropped profiles
    assert not active_profiles(tt)
    with tt.profile("c"):
        assert [profile.name for profile in active_profiles(tt)] == ["c"]
    b.__exit__(None, None, None)
    assert not active_profiles(tt)
    profiles = {profile.name: profile for profile in tt.iter_profiles()}
    assert [(profile.name, profile.depth) for profile in tt.iter_profiles()] == [("a", 0), ("b", 1), ("c", 0)]
    assert profiles["b"].nhits == 1 and profiles["b"]._active_hits == 0 and profiles["b"].total_runtime > 0


def test_generator_resumed_in_other_context():
    tt = TickTock()
    profiled = tt.profile_loop("a", range(2))
    next(profiled)
    context = contextvars.copy_context()
    # Ends the first hit, which was started in the original context, and starts the second hit in the copied context
    context.run(next, profiled)
    assert not active_profiles(tt)
    assert [profile.name for profile in context.run(active_profiles, tt)] == ["a"]
    context.run(profiled.close)
    assert not context.run(active_profiles, tt)
    profile = next(tt.iter_profiles())
    assert (profile.nhits, profile._active_hits) == (2, 0)


def test_in_progress_hits_in_other_thread():
    tt = TickTock()
    started = Event()
    release = Event()

    def work():
        with tt.profile("parent"):
            started.set()
            release.wait()

    with tt.profile("parent"):
        with tt.profile("child"):
            pass
    thread = Thread(target=work)
    thread.start()
    assert started.wait(timeout=1)
    try:
        parent = next(tt.iter_profiles())
        assert parent.nhits == 2
        assert parent.mean() == pytest.approx(parent.total_runtime)
        lines = str(tt).splitlines()
        assert lines[2].split("|")[3].strip() == "1"

        # A parent profile without completed hits yet
        with tt.profile("new parent"):
            pass
        with tt.profile("new parent"):
            pass
        assert str(tt)
    finally:
        release.set()
        thread.join()
    assert next(tt.iter_profiles()).mean() == pytest.approx(parent.total_runtime / 2)


def test_print_with_parent_in_progress():
    tt = TickTock()
    started = Event()
    release = Event()

    def work():
        with tt.profile("parent"):
            with tt.profile("child"):
                pass
            started.set()
            release.wait()

    thread = Thread(target=work)
    thread.start()
    assert started.wait(timeout=1)
    try:
        lines = str(tt).splitlines()
        parent_row = [cell.strip() for cell in lines[2].split("|")]
        child_row = [cell.strip() for cell in lines[3].split("|")]
        assert parent_row[0] == "parent" and parent_row[3] == "0"
        assert child_row[0] == "child" and child_row[2].startswith("-") and child_row[3] == "1"
        with tt.profile("own"), pytest.raises(ValueError):
            str(tt)
    finally:
        release.set()
        thread.join()


def test_reset_while_other_thread_profiles():
    tt = TickTock()
    started = Event()
    release = Event()

    def work():
        with tt.profile("old"):
            started.set()
            release.wait()
            with tt.profile("old child"):
                pass

    thread = Thread(target=work)
    thread.start()
    assert started.wait(timeout=1)
    tt.reset()
    assert not tt.has_profiles
    release.set()
    thread.join()
    # The profile in progress is gone, and profiles started inside it afterwards are top-level in the new tree
    with tt.profile("new"):
        pass
    assert [(profile.name, profile.depth) for profile in tt.iter_profiles()] == [("old child", 0), ("new", 0)]


def _run_across_reset(tt: TickTock, reset_method: str, body, *, disable: bool = False):
    """Run ``body`` in a thread inside a profile that is in progress while ``tt`` is reset."""
    started = Event()
    release = Event()

    def work():
        with tt.profile("old", disable=disable):
            started.set()
            release.wait()
            body()

    thread = Thread(target=work)
    thread.start()
    assert started.wait(timeout=1)
    getattr(tt, reset_method)()
    release.set()
    thread.join()


@pytest.mark.parametrize("reset_method", ["reset", "reset_profiles"])
def test_stale_parent_after_reset(reset_method: str):
    tt = TickTock()
    iterated = list()

    def body():
        with tt.profile("child"):
            with tt.profile("grandchild"):
                pass
        iterated.extend(tt.profile_next("next", iter([1, 2])))
        iterated.extend(tt.profile_next("unused", iter([])))

    _run_across_reset(tt, reset_method, body)
    assert iterated == [1, 2]
    # Nothing remains of the unused profile, and the rest is top-level in the new tree
    assert [(profile.name, profile.depth, profile.nhits) for profile in tt.iter_profiles()] == [
        ("child", 0, 1),
        ("grandchild", 1, 1),
        ("next", 0, 2),
    ]


def test_stale_disabled_parent_after_reset():
    tt = TickTock()

    def body():
        with tt.profile("child"):
            pass

    _run_across_reset(tt, "reset", body, disable=True)
    assert not list(tt.iter_profiles())


def test_profile_next_exhaustion_keeps_profile_used_by_other_thread():
    tt = TickTock()
    started = Event()
    release = Event()

    class WaitingIterator:
        def __next__(self):
            started.set()
            release.wait()
            raise StopIteration

    def work():
        list(tt.profile_next("fetch", WaitingIterator()))

    thread = Thread(target=work)
    thread.start()
    assert started.wait(timeout=1)
    with tt.profile("fetch"):
        pass
    release.set()
    thread.join()
    assert [(profile.name, profile.nhits) for profile in tt.iter_profiles()] == [("fetch", 1)]


def test_profile_next_exhaustion_racing_lookup():
    """A profile found by one thread must not be removed by another thread exhausting profile_next."""
    tt = TickTock()
    lock = tt._lock
    y_at_lock = Event()
    release_y = Event()
    x_exhausting = Event()
    release_x = Event()

    class PausingLock:
        def __enter__(self):
            if current_thread().name == "Y":
                y_at_lock.set()
                release_y.wait()
            lock.acquire()

        def __exit__(self, *_):
            lock.release()

    class WaitingIterator:
        def __next__(self):
            x_exhausting.set()
            release_x.wait()
            raise StopIteration

    def profile_once():
        with tt.profile("fetch"):
            pass

    x = Thread(target=lambda: list(tt.profile_next("fetch", WaitingIterator())), name="X")
    x.start()
    assert x_exhausting.wait(timeout=1)
    tt._lock = PausingLock()
    y = Thread(target=profile_once, name="Y")
    y.start()
    assert y_at_lock.wait(timeout=1)
    release_x.set()
    x.join()
    release_y.set()
    y.join()
    assert [(profile.name, profile.nhits) for profile in tt.iter_profiles()] == [("fetch", 1)]


def test_fuse_with_other_thread_profiling():
    tt = TickTock()
    with tt.profile("a"):
        pass
    target = deepcopy(tt)
    started = Event()
    release = Event()

    def work():
        with tt.profile("a"):
            started.set()
            release.wait()

    thread = Thread(target=work)
    thread.start()
    assert started.wait(timeout=1)
    try:
        target.fuse(tt)
    finally:
        release.set()
        thread.join()
    # Only the completed hit of tt is fused
    assert next(target.iter_profiles()).nhits == 2


def test_load_old_pickle_state():
    """State pickled by versions before thread-safe profiling can still be loaded."""
    root = Profile("a", 0, None)
    child = Profile("b", 1, root)
    for profile in (root, child):
        profile.nhits = 2
        profile.total_runtime = 1.0
        del profile._active_hits, profile._child_index
    tt = TickTock.__new__(TickTock)
    tt.__setstate__({
        "_tick_starts": {"timer": 0.0},
        "_id_to_profile": {root: root, child: child},
        "_profile_stack": [],
        "_root_profiles": [root],
        "_thread_name": "MainThread",
        "_thread_id": 0,
    })
    assert tt.tock("timer") > 0
    with tt.profile("a"):
        with tt.profile("b"):
            pass
    assert [(profile.name, profile.nhits) for profile in tt.iter_profiles()] == [("a", 3), ("b", 3)]
    assert next(tt.iter_profiles()).mean() == pytest.approx(next(tt.iter_profiles()).total_runtime / 3)


def test_copy_while_other_thread_profiles():
    tt = TickTock()
    started = Event()
    release = Event()

    def work():
        with tt.profile("a"):
            started.set()
            release.wait()

    with tt.profile("a"):
        with tt.profile("b"):
            pass
    tt.tick("timer")
    tt.do_at_interval(1000, "interval")
    thread = Thread(target=work)
    thread.start()
    assert started.wait(timeout=1)
    try:
        copies = [deepcopy(tt), pickle.loads(pickle.dumps(tt))]
    finally:
        release.set()
        thread.join()

    for copy in copies:
        assert [(profile.name, profile.nhits, profile._active_hits) for profile in copy.iter_profiles()] == [("a", 1, 0), ("b", 1, 0)]
        assert not active_profiles(copy)
        assert copy.tock("timer") > 0
        assert not copy.do_at_interval(1000, "interval")
        with copy.profile("a"):
            with copy.profile("b"):
                pass
        assert [profile.nhits for profile in copy.iter_profiles()] == [2, 2]

    fused = TickTock.fuse_multiple(copies)
    assert [profile.nhits for profile in fused.iter_profiles()] == [4, 4]


def test_profile_decorator():
    tt = TickTock()

    @tt.profile("recursive")
    def recursive(n: int) -> int:
        return 0 if n == 0 else 1 + recursive(n - 1)

    assert recursive(3) == 3
    assert recursive(1) == 1
    assert [(profile.name, profile.depth, profile.nhits) for profile in tt.iter_profiles()] == [
        ("recursive", 0, 2),
        ("recursive", 1, 2),
        ("recursive", 2, 1),
        ("recursive", 3, 1),
    ]

    context = tt.profile("reentered")
    with context, pytest.raises(TickTockException), context:
        pass


def test_profile_decorator_async():
    tt = TickTock()

    @tt.profile("inner")
    async def inner(x: int, *, sleep: float) -> int:
        await asyncio.sleep(sleep)
        return 2 * x

    @tt.profile("outer")
    async def outer(i: int) -> int:
        assert [profile.name for profile in active_profiles(tt)] == ["outer"]
        return await inner(i, sleep=0.05)

    assert inspect.iscoroutinefunction(outer)
    assert outer.__name__ == "outer"

    async def main() -> list[int]:
        # Concurrent tasks must each nest their own inner call under their own outer call
        return await asyncio.gather(*(outer(i) for i in range(5)))

    assert asyncio.run(main()) == [0, 2, 4, 6, 8]
    profiles = list(tt.iter_profiles())
    assert [(profile.name, profile.depth, profile.nhits) for profile in profiles] == [("outer", 0, 5), ("inner", 1, 5)]
    # The profiles cover the awaited execution, not just creation of the coroutine
    # Timers may fire slightly early, so allow a margin
    assert profiles[1].total_runtime >= 5 * 0.04
    assert profiles[0].total_runtime >= profiles[1].total_runtime
    assert not active_profiles(tt)

    # A hit is only registered once the coroutine is run
    coroutine = inner(1, sleep=0)
    assert profiles[1].nhits == 5
    coroutine.close()
    assert profiles[1].nhits == 5


def test_profile_decorator_async_exception():
    tt = TickTock()

    @tt.profile("failing")
    async def failing():
        await asyncio.sleep(0)
        raise RuntimeError("failed")

    with pytest.raises(RuntimeError, match="failed"):
        asyncio.run(failing())
    profile = next(tt.iter_profiles())
    assert (profile.nhits, profile._active_hits) == (1, 0)
    assert profile.total_runtime > 0
    assert not active_profiles(tt)


def test_profile_decorator_async_cancelled():
    tt = TickTock()
    started = asyncio.Event()

    @tt.profile("cancelled")
    async def cancelled():
        started.set()
        await asyncio.sleep(10)

    async def main():
        task = asyncio.create_task(cancelled())
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(main())
    profile = next(tt.iter_profiles())
    assert (profile.nhits, profile._active_hits) == (1, 0)
    assert not active_profiles(tt)


def test_profile_decorator_async_disabled():
    tt = TickTock()

    @tt.profile("disabled", disable=True)
    async def disabled():
        with tt.profile("child"):
            await asyncio.sleep(0)

    asyncio.run(disabled())
    assert not list(tt.iter_profiles())


def test_do_at_interval_is_thread_specific():
    tt = TickTock()
    assert not tt.do_at_interval(1000, "key")
    results = list()

    def work():
        results.append(tt.do_at_interval(1000, "key", also_first=True))
        results.append(tt.do_at_interval(1000, "key", also_first=True))

    _run_threads(work, 2)
    assert results == [True, False, True, False]
    assert not tt.do_at_interval(1000, "key")


def test_bounded_memory():
    context_size = len(contextvars.copy_context())
    for _ in range(1000):
        with get_active_ticktock().profile("a"):
            pass
    assert len(contextvars.copy_context()) == context_size

    tt = TickTock()
    for _ in range(1000):
        with tt.profile("a"):
            with tt.profile("b"):
                pass
    assert len(list(tt.iter_profiles())) == 2

    class Key:
        pass

    keys = [Key()]
    key_ref = weakref.ref(keys[0])
    _run_threads(lambda: tt.do_at_interval(1, keys[0]), 1)
    keys.clear()
    gc.collect()
    # Interval timers of the finished thread are released
    assert key_ref() is None
