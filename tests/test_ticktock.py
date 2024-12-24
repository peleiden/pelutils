from copy import deepcopy

import pytest
from pelutils import TickTock, TT, TimeUnits, Profile
from pelutils.ticktock import TickTockException


def test_ticktock():
    """ Test base functionality. """
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
    """ Test profiling """
    tt = TickTock()
    tt.profile("p")
    tt.end_profile()

    tt.profile("pp")
    with pytest.raises(NameError):
        tt.end_profile("p")
    tt.end_profile("pp")

    tt.profile("p")
    tt.profile("pp")
    tt.profile("ppp")
    tt.end_profile("ppp")
    assert len(tt._profile_stack) == 2
    tt.end_profile()
    tt.end_profile()

def test_context_profiling():
    """ Test profiling with context """
    tt = TickTock()

    with tt.profile("Hello there"):
        assert len(tt._profile_stack) == 1
        with tt.profile("General Kenobi!"):
            assert len(tt._profile_stack) == 2
    assert len(tt._profile_stack) == 0

    with pytest.raises(NameError):
        with tt.profile("Hello there"):
            tt.profile("General Kenobi!")

def test_fuse():
    tt1 = TickTock()
    tt2 = TickTock()

    tt1.profile("p")
    tt2.profile("p")
    tt2.profile("pp")
    tt2.end_profile()
    tt2.end_profile()
    with pytest.raises(TickTockException):
        tt1.fuse(tt2)
    tt1.end_profile()
    with pytest.raises(TickTockException):
        tt1.fuse(tt2)
    assert len(tt1.profiles) == 1

    with pytest.raises(ValueError):
        TickTock.fuse_multiple(tt1, tt1)

    tt1 = deepcopy(tt2)
    tt1 = TickTock.fuse_multiple(tt1, tt2)
    for p1, p2 in zip(tt1, tt2):
        assert p1._n == 2 * p2._n
        assert p1._total_time == 2 * p2._total_time

def test_global_tt():
    assert isinstance(TT, TickTock)

def test_throw():
    tt = TickTock()
    with tt.profile("Hello there"), pytest.raises(ValueError):
        str(tt)

def test_timeunits():
    assert TimeUnits.next_bigger(("nice", 69)) == TimeUnits.hour
    assert TimeUnits.next_smaller(("nice", 69)) == TimeUnits.minute
    assert TimeUnits.next_bigger(TimeUnits.second) == TimeUnits.minute
    assert TimeUnits.next_smaller(TimeUnits.second) == TimeUnits.millisecond

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
        assert tt._nhits == [1]
    assert len(tt.profiles) == 1
    tt.reset()
    assert len(tt.profiles) == 0
    assert len(tt._profile_stack) == 0
    assert tt._nhits == list()

    with tt.profile("pp"):
        with pytest.raises(TickTockException):
            tt.reset()

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

    with pytest.warns(DeprecationWarning):
        profiles = list(tt)
    assert profiles[0].name == "a"
    assert profiles[0].depth == 0
    assert len(profiles[0]) == 3

    assert profiles[1].name == "b"
    assert profiles[1].depth == 0
    assert len(profiles[1]) == 2

    assert profiles[2].name == "a"
    assert profiles[2].depth == 1
    assert len(profiles[2]) == 4

    with pytest.warns(DeprecationWarning):
        assert len(tt.measurements_by_profile_name("b")) == 2
    b_n, b_sum = tt.stats_by_profile_name("b")
    assert b_n == 2
    assert isinstance(b_sum, float)
    assert b_sum > 0
    with pytest.warns(DeprecationWarning):
        assert all(isinstance(x, float) for x in tt.measurements_by_profile_name("b"))

    with pytest.warns(DeprecationWarning), pytest.raises(KeyError):
        tt.measurements_by_profile_name("c")
    with pytest.raises(KeyError):
        tt.stats_by_profile_name("c")

def test_add_external_measurements():
    tt = TickTock()
    with tt.profile("a"):
        tt.add_external_measurements("b", 5, hits=2)
        with tt.profile("b"):
            tt.add_external_measurements(None, 3, hits=4)
        tt.add_external_measurements(None, 5)
    tt.add_external_measurements("a", 5)

    for profile in tt.profiles:
        if profile.name == "a":
            with pytest.warns(DeprecationWarning):
                assert len(profile.hits) == 3
        elif profile.name == "b":
            with pytest.warns(DeprecationWarning):
                assert len(profile.hits) == 7

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
    with pytest.raises(ZeroDivisionError):
        tt.profile("adfsadlæfj")
        0 / 0
        tt.end_profile()
    # with tt.profile construct was not used, so expect an unclosed profile
    assert len(tt._profile_stack) == 1

    tt = TickTock()
    with pytest.raises(ZeroDivisionError):
        with tt.profile("sada"):
            tt.profile("adfsadlæfj")
            0 / 0
            tt.end_profile()
    # with tt.profile construct was used, so expect no unclosed profiles
    assert len(tt._profile_stack) == 0

    tt = TickTock()
    with pytest.raises(ZeroDivisionError):
        with tt.profile("adsfad"):
            tt.profile("asdasd")
            with tt.profile("sada"):
                tt.profile("adfsadlæfj")
                0 / 0
                tt.end_profile()
            tt.end_profile()
    # with tt.profile construct was used, so expect no unclosed profiles
    assert len(tt._profile_stack) == 0

    tt = TickTock()
    with pytest.raises(ZeroDivisionError):
        tt.profile("aslkd")
        tt.profile("alksjdasd")
        with tt.profile("adsfad"):
            tt.profile("asdasd")
            with tt.profile("sada"):
                tt.profile("adfsadlæfj")
                0 / 0
                tt.end_profile()
            tt.end_profile()
        tt.end_profile()
        tt.end_profile()
    # Two outermost did not using with construct, so expect two unclosed profiles
    assert len(tt._profile_stack) == 2

def test_profile(capfd: pytest.CaptureFixture):
    p = Profile("tester", 0, None)
    assert len(p) == 0
    assert p.mean() == 0

    print(p)
    stdout, _ = capfd.readouterr()
    assert stdout.strip() == "tester"

def test_active():
    tt = TickTock()
    assert not bool(tt)
    with tt.profile("test"):
        pass
    assert bool(tt)
    with pytest.warns(DeprecationWarning):
        len(tt)
