import functools
from typing import Callable, Type

_import_error = ModuleNotFoundError("To use the ds submodule, you must install pelutils[ds]")

try:
    import torch
except ModuleNotFoundError as e:
    raise _import_error from e


def reset_cuda():
    """ Clear cache and synchronize cuda """
    torch.cuda.empty_cache()
    if torch.cuda.is_available():
        torch.cuda.synchronize()

def no_grad(fun: Callable) -> Callable:
    """
    Decorator for running functions without pytorch tracking gradients, e.g.
    ```
    @no_grad
    def feed_forward(x):
        return net(x)
    ```
    """
    functools.wraps(fun)
    def wrapper(*args, **kwargs):
        with torch.no_grad():
            return fun(*args, **kwargs)
    return wrapper


class BatchFeedForward:
    """
    This class handles feedforwarding large batches that would otherwise cause memory overflow
    It works by splitting it into smaller batches, if it encounters a memory error
    Only works when gradient should not be tracked
    """

    def __init__(self, net: Type[torch.nn.Module], data_points: int, increase_factor=2):
        """
        net: torch network
        data_points: Number of data points in each feed forward
        increase_factor: Multiply number of batches with this each time a memory error occurs
        """
        self.net = net
        self.data_points = data_points
        self.increase_factor = increase_factor
        self.batches = 1

    @no_grad
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        while True:
            try:
                output_parts = [self.net(x[slice_]) for slice_ in self._get_slices()]
                output = torch.cat(output_parts)
                break
            # Usually caused by running out of vram. If not, the error is still raised, else batch size is reduced
            except RuntimeError as e:
                if "alloc" not in str(e):
                    raise e
                self._more_batches()
        return output

    def __call__(self, x: torch.Tensor) -> torch.Tensor:
        return self.forward(x)

    def update_net(self, net: Type[torch.nn.Module]):
        self.net = net

    def _more_batches(self):
        self.batches *= self.increase_factor

    def _get_slices(self):
        slice_size = self.data_points // self.batches + 1
        # Final slice may have overflow, however this is simply ignored when indexing
        slices = [slice(i*slice_size, (i+1)*slice_size) for i in range(self.batches)]
        return slices
