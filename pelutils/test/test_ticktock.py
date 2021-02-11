import pytest

from pelutils import TickTock

def test_ticktock():
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

