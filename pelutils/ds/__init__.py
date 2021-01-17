import functools

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

def no_grad(fun):
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


from . import plot
