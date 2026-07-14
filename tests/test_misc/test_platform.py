import platform

import torch

from pelutils import OS, hardware_info


def test_is_windows():
    # What a dumb test
    assert OS.is_windows == platform.platform().startswith("Windows")


def test_is_mac():
    # What a dumb test
    assert OS.is_mac == (platform.platform().startswith("Darwin") or platform.platform().startswith("macOS"))


def test_is_linux():
    # What a dumb test
    assert OS.is_linux == platform.platform().startswith("Linux")


def test_hardware_info():
    assert isinstance(hardware_info.cpu, str) and len(hardware_info.cpu) > 0
    if OS.is_linux:
        assert isinstance(hardware_info.sockets, int)
    else:
        assert hardware_info.sockets is None
    assert isinstance(hardware_info.threads, int) and hardware_info.threads > 0
    assert isinstance(hardware_info.memory, int) and hardware_info.memory > 0
    if torch.cuda.is_available():
        assert isinstance(hardware_info.gpus, list)
        assert len(hardware_info.gpus) > 0
        for gpu in hardware_info.gpus:
            assert isinstance(gpu, str)
    else:
        assert hardware_info.gpus is None

    string = str(hardware_info)
    assert hardware_info.cpu in string
    if hardware_info.sockets:
        # This is a very shitty test
        assert str(hardware_info.sockets) in string
    if hardware_info.threads:
        # This is also a very shitty test
        assert f"{hardware_info.threads:,}" in string
    assert str(round(hardware_info.memory / 2**30, 2)) in string
    if hardware_info.gpus:
        for gpu in hardware_info.gpus:
            assert gpu in string
