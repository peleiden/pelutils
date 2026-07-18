from copy import deepcopy
from threading import Thread

import pytest

from pelutils.ticktock import TT, Profile, TickTock, TickTockException
from pelutils.ticktock._ticktock import _get_smallest_suitable_unit


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
            assert len(tt._profile_stack) == 2


def test_context_profiling():
    """Test profiling with context"""
    tt = TickTock()

    with tt.profile("Hello there"):
        assert len(tt._profile_stack) == 1
        with tt.profile("General Kenobi!"):
            assert len(tt._profile_stack) == 2
    assert len(tt._profile_stack) == 0


def test_fuse():
    tt1 = TickTock()
    tt2 = TickTock()

    with tt1.profile("p"):
        with tt2.profile("p"):
            with tt2.profile("pp"):
                pass
        with pytest.raises(TickTockException):
            tt1.fuse(tt2)
    with pytest.raises(TickTockException):
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
        assert len(tt._profile_stack) == 1
    assert len(tt._root_profiles) == 1
    tt.reset()
    assert len(tt._root_profiles) == 0
    assert len(tt._profile_stack) == 0

    with tt.profile("pp"):
        with pytest.raises(TickTockException):
            tt.reset()

    tt.tick("abc")
    tt.tick("abc2")
    tt.reset_profiles()
    tt.tock("abc")
    tt.tock("abc2")
    with pytest.raises(TickTockException):
        tt.tock("abc3")


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


def test_thread_assert():
    tt = TickTock()

    tt = None

    def set_tt():
        nonlocal tt
        tt = TickTock()

    thread = Thread(target=set_tt)
    thread.start()
    thread.join()

    with pytest.warns(), tt.profile("abc"):
        pass


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
    assert len(tt._profile_stack) == 0

    tt = TickTock()
    with pytest.raises(ZeroDivisionError):
        with tt.profile("sada"):
            with tt.profile("adfsadlæfj"):
                0 / 0  # noqa: B018

    # with tt.profile construct was used, so expect no unclosed profiles
    assert len(tt._profile_stack) == 0

    tt = TickTock()
    with pytest.raises(ZeroDivisionError):
        with tt.profile("adsfad"):
            with tt.profile("asdasd"):
                with tt.profile("sada"):
                    with tt.profile("aæsldfjka"):
                        0 / 0  # noqa: B018

    # with tt.profile construct was used, so expect no unclosed profiles
    assert len(tt._profile_stack) == 0


def test_profile(capfd: pytest.CaptureFixture):
    profile = Profile("tester", 0, None)
    assert profile.nhits == 0
    assert profile.mean() == 0

    print(profile)
    stdout, _ = capfd.readouterr()
    assert stdout.strip() == "tester"


def test_active():
    tt = TickTock()
    assert not tt.has_profiles
    with tt.profile("test"):
        pass
    assert tt.has_profiles
