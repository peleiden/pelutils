import pytest

from pelutils import TickTock, TT

def test_ticktock():
    """ Test base functionality """
    tt = TickTock()
    tt.tick()
    assert isinstance(tt.tock(), float)

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

def test_iter_profiling():
    tt = TickTock()
    for _ in tt.profile_iter(range(5), "I'll try looping, that's a good trick!"):
        pass
    assert len(tt._profile_stack) == 0
    assert "I'll try looping, that's a good trick!" in tt.profiles
    assert len(tt.profiles["I'll try looping, that's a good trick!"]._hits) == 5

def test_fuse():
    tt1 = TickTock()
    tt2 = TickTock()
    tt3 = TickTock()

    tt1.profile("p")
    tt2.profile("p")
    tt2.profile("pp")
    tt2.end_profile()
    tt2.end_profile()
    with pytest.raises(ValueError):
        tt1.fuse(tt2)
    tt1.end_profile()
    tt1.fuse(tt2)
    assert len(tt1.profiles) == 2

    with pytest.raises(ValueError):
        TickTock.fuse_multiple([tt1, tt2, tt1])
    tt = TickTock.fuse_multiple([tt2, tt3])
    assert len(tt.profiles) == 2

def test_global_tt():
    assert isinstance(TT, TickTock)

def test_throw():
    tt = TickTock()
    with tt.profile("Hello there"), pytest.raises(ValueError):
        str(tt)
