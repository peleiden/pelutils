# pelutils

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![basedpyright](https://img.shields.io/endpoint?url=https://docs.basedpyright.com/latest/badge.json)](https://docs.basedpyright.com)
[![checks](https://github.com/peleiden/pelutils/actions/workflows/checks.yml/badge.svg?branch=master)](https://github.com/peleiden/pelutils/actions/workflows/checks.yml)
[![Coverage Status](https://coveralls.io/repos/github/peleiden/pelutils/badge.svg?branch=master)](https://coveralls.io/github/peleiden/pelutils?branch=master)
[![PyPi](https://img.shields.io/pypi/v/pelutils.svg)](https://pypi.org/project/pelutils/)
[![Python versions](https://img.shields.io/pypi/pyversions/pelutils)](https://img.shields.io/pypi/pyversions/pelutils)
[![image](https://img.shields.io/pypi/l/pelutils.svg)](https://github.com/peleiden/pelutils/blob/master/LICENSE.txt)

The Swiss army knife of Python projects.

- A simple and powerful logger with colourful printing, stacktraces, and log file rotation.
- Parsing for combining config files and command-line arguments - especially useful developing algorithms with many parameters.
- A timer inspired by Matlab's `tic` and `toc`.
- Simple, near-zero cost performance profiler.
- An extension to the built-in `dataclass` for saving and loading data.
- Table formatting with built-in LaTeX support.
- Miscellaneous standalone functions - see `pelutils/__init__.py`.
- Data-science submodule with extra utilities for statistics, plotting with `matplotlib`, and machine learning using `PyTorch`.
- `unique` function in the style of `numpy.unique` which runs in linear time, making it significantly.

`pelutils` supports Python 3.9+.

To install, simply run `pip install pelutils`.
A small subset of the functionality requires `PyTorch`, which has to be installed separately.

## Timing and Code Profiling

Simple time taker inspired by Matlab Tic, Toc, which also has profiling tooling.

```py
from pelutils import TT, TickTock

# Time a task
TT.tick()
<some task>
seconds_used = TT.tock()

# Profile a for loop
for i in range(100):
    with TT.profile("Repeated code"):
    <some task>
    with TT.profile("Subtask"):
        <some subtask>
print(TT)  # Print a table view of profiled code sections

# When using multiprocessing, it can be useful to simulate multiple hits of the same profile
with mp.Pool() as p, TT.profile("Processing 100 items on multiple threads", hits=100):
    p.map(100 items)
# Similar for very quick loops
a = 0
with TT.profile("Adding 1 to a", hits=100):
    for _ in range(100):
        a += 1

# To use the TickTock instance as a timer to trigger events, do
while True:
    if TT.do_at_interval(60, "task1"):  # Do task 1 every 60 seconds
        <task 1>
    if TT.do_at_interval(30, "task2"):  # Do task 2 every 30 seconds
        <task 2>
    time.sleep(0.01)
```

## Data Serialisation

The `DataStorage2` class is an extension of `pydantic.BaseModel` that incluces save and load functionality.
It supports any data type, storing all data to a pretty JSON file. A class should simply inherit from
`DataStorage2`. The stored JSON will be a dictionary-like structure with the whole nested structure.
Any nested `BaseModel` is automatically converted to a dictionary. If a data type is reached which is not
JSON serialisable (e.g. normal classes, pandas DataFramas, numpy arrays), they are encoded with `pickle`
and `base64`. Inside the JSON file, a record is kept of the original type.

Very long lists utilise the full allowed line length before splitting, preventing the common JSON issue of
having either very long lines (no indents) or excessively many lines with a single element on each.

Because the class inherits from `pydantic.BaseModel`, type checking is built directly into it.

```py
class BasederClass(BaseModel):
    based_string: str

# Define the structure
class BasedClass(DataStorage2):
    nice: float
    long_tuple_of_ints: tuple[int, ...]
    array: FloatArray
    baseder: BasederClass

# Create an instance
based = BasedClass(
    nice=69.69,
    long_tuple_of_ints=tuple(range(500)),
    array=np.arange(5, dtype=np.float16),
    baseder=BasederClass(based_string="Hello there")
)
# Save it to a file
based.save(".")
# Save it to a file
based.save("directory/to/save/in")

# Load it again
based = BasedClass.load("directory/to/save/in")
```
This will produce `directory/to/save/in/BasedClass.json` with the following contents:
```json
{
  "nice": 69.69,
  "long_tuple_of_ints": [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36,
    37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70,
    71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103,
    104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130,
    131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157,
    158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184,
    185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211,
    212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238,
    239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265,
    266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292,
    293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319,
    320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346,
    347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373,
    374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400,
    401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427,
    428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454,
    455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481,
    482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499
  ],
  "array": "__pickled_b64__:numpy.ndarray:gAWVfQAAAAAAAACMEm51bXB5LmNvcmUubnVtZXJpY5SMC19mcm9tYnVmZmVylJOUKJYKAAAAAAAAAAAAADwAQABCAESUjAVudW1weZSMBWR0eXBllJOUjAJmMpSJiIeUUpQoSwOMATyUTk5OSv////9K/////0sAdJRiSwWFlIwBQ5R0lFKULg==",
  "baseder": {"based_string": "Hello there"}
}
```
The class is built on top of the also provided `pretty_json` which does the exact same as the built-in `json.dumps` but with prettier formatting of the JSON string.

## Config and Command-line Argument Parsing

Python has built-in support for both config files (the `ArgumentParser` and `ConfigParser`, respectively), but nothing for parsing both.
The Pelutils `Parser` supports both, while also allowing for much stricter checking of types and presence of arguments.
It is useful for any application relying on config files where one may want to overwrite certain arguments from the command-line.
It's prime usecase, though, is for development of parametric algorithms, such as machine learning engineering.

Consider the execution of a file `main.py` with the command line call
```
python main.py path/to/output -c path/to/config/file.ini --data-path path/to/data
```
The config file could contain
```ini
[DEFAULT]
learning-rate=1e-4
fp16

[LOWLR]
learning-rate=1e-5

[NOFP16]
fp16=False
```
where `main.py` contains
```py
options = [
    # Mandatory argument with set abbreviation -p
    Argument("data-path", help="Path to where data is located", abbrv"-p"),
    # Optional argument with auto-generated abbreviation -l
    Option("learning-rate", default=1e-5, help="Learning rate to use for gradient descent steps"),
    # Boolean flag with auto-generated abbreviation -f
    Flag("fp16", help="Use mixed precision for training"),
]
parser = Parser(*options, multiple_jobs=True)  # Two jobs are specified in the config file, so multiple_jobs=True
location = parser.location  # Experiments are stored here. In this case path/to/output
job_descriptions = parser.parse_args()
# Run each experiment
for job in job_descriptions:
    # Get the job as a dictionary
    job_dict = job.todict()
    # Clear directory where job is located and put a documentation file there
    job.prepare_directory()
    # Get location of this job as job.location
    run_experiment(job)
```

This could then by run by
`python main.py data/my-big-experiment --learning-rate 1e-5`
or by
`python main.py data/my-big-experiment --config cfg.ini`
or using a combination where CLI args takes precedence:
`python main.py data/my-big-experiment --config cfg.ini --learning-rate 1e-5`
where `cfg.ini` could contain

# Logging

The logging submodule contains a simple yet feature-rich logger which fits common needs. Can be imported from `pelutils` directly, e.g. `from pelutils import log`.

```py
from pelutils import log, Logger

# Configure logger for the script
log.configure("path/to/save/log.log")

# Start logging
for i in range(70):  # Nice
    log("Execution %i" % i)

# Sections
log.section("New section in the logfile")

# Adjust logging levels
log.warning("Will be logged")
with log.level(LogLevels.ERROR):  # Only log at ERROR level or above
    log.warning("Will not be logged")
with log.no_log:
    log.section("I will not be logged")

# Rotation
# Start a new log file every hour (or day, month, or year)
log.configure("path/to/save/log.log", rotation="hour")
# Start a new log file when the current one reaches a certain size
log.configure("path/to/save/log.log", rotation="5 MB")

# Error handling
# The zero-division error and stacktrace is logged
with log.log_errors:
    0 / 0
# Entire chained stacktrace is logged
with log.log_errors:
    try:
        0 / 0
    except ZeroDivisionError as e:
        raise ValueError("Denominator must be non-zero") from e

# User input - acts like built-in input but logs both prompt and user input
inp = log.input("Continue [Y/n]? ")
# Parse yes/no user input
cont = log.parse_bool_input(inp, default=True)

# Log all logs from a function at the same time
# This is especially useful when using multiple threads so logging does not get mixed up
def fun():
    with log.collect:
        log("Hello there")
        log("General Kenobi!")
with mp.Pool() as p:
    p.map(fun, args)

# It is also possible to create multiple loggers by importing the Logger class, e.g.
log2 = Logger()
log2.configure("path/to/save/log2.log")
```

# Types

A few different numpy types are defined for the convenience of not having to remember what data types your arrays are - and also to satisfy your nasty type checkers.
```py
from pelutils.types import AnyArray, FloatArray, IntArray


def function_which_takes_np_types(
    any_array: AnyArray,  # np.ndarray with arbitrary data type
    float_array: FloatArray,  # np.ndarray with any floating point data type (e.g. float, np.float16, and np.float64)
    int_array: IntArray,  # np.ndarray with any integer data type (e.g. int, np.uint8, and np.int32)
):
    ...
```

# Data Science

This submodule contains various utility functions for data science, statistics, plotting, and machine learning.

## Statistics

Includes various commonly used statistical functions.
There are also wrappers around a number of scipy distributions reparametrized as in Jim Pitman's "Probability", instead of using scale and loc, which can be quite unintuitive for many distributions.

```py
from pelutils.ds.stats import z, corr_zi
from pelutils.ds.distributions import expon

# Get one sided z value for exponential(lambda=2) distribution with a significance level of 1 %
zval = z(alpha=0.01, two_sided=False, distribution=expon(2))

# Get correlation, confidence interval, and p value for two vectors
a, b = np.random.randn(100), np.random.randn(100)
r, lower_r, upper_r, p = corr_ci(a, b, alpha=0.01)
```

## Plotting

`pelutils` provides plotting utilities based on `matplotlib`.
Most notable is the `Figure` context class, which attempts to remedy some of the common grievances with `matplotlib`,
e.g. having to remember the correct `kwargs` and `rcParams` for setting font sizes, legend edge colour etc.
```py
from pelutils.ds.plots import Figure

# The following makes a plot and saves it to `plot.png`.
# The seaborn is style is used for demonstration, but if the `style` argument
# is not given, the default matplotlib style is used.
# The figure and font size are also given for demonstration, but their default
# values are increased compared to matplotlib's default, as these are generally
# too small for finished plots.
with Figure("plot.png", figsize=(20, 10), style="seaborn", fontsize=20):
    plt.scatter(x, y, label="Data")
    plt.grid()
    plt.title("Very nice plot")
# The figure is automatically saved to `plot.png` and closed, such that
# plt.plot can be used again from here.
# Figure changes `matplotlib.rcParams`, but these changes are also undone
# after the end of the `with statement`.
```

The plotting utilies also include binning functions for creating nice histograms.
The `histogram` function produces bins based on a binning function, of which three are provided:

- `linear_binning`: Bins are spaced evenly from the lowest to the largest value of the data.
- `log_binning`: Bins are log-spaced from the lowest to the largest value of the data, which is assumed to be positive.
- `normal_binning`: Bins are distributed according to the distribution of the data, such there are more bins closer to the center of the data. This is useful if the data somewhat resembles a normal distribution, as the resolution will be the greatest where there is the most data.

It is also possible to provide custom binning functions.

`histogram` provide both `x` and `y` coordinates, making it simple to use with argument unpacking:
```py
import matplotlib.pyplot as plt
import numpy as np
from pelutils.ds.plots import histogram, normal_binning

# Generate normally distributed data
x = np.random.randn(100)
# Plot distribution
plt.plot(*histogram(x, binning_fn=normal_binning))
```

Finally, different smoothing functions are provided.
The two most common are `moving_avg` and `exponential_avg` which smooth the data using a moving average and exponential smoothing, respectively.

The `double_moving_avg` is special in that the number of smoothed data points do not depend on the number of given data points but is instead based on a given number of samples, which allows the resulting smoothed curve to not by jagged as happens with the other smoothing functions.
It also has two smoothness parameters, which allows a large degree of smoothness control.

Apart from smoothness parameters, all smoothness functions have the same call signature:
```py
from pelutils.ds.plots import double_moving_avg

# Generate noisy data
n = 100
x = np.linspace(-1, 1, n)
y = np.random.randn(n)

# Plot data along with smoothed curve
plt.plot(*double_moving_avg(x, y))
# If x is not given, it is assumed to go from 0 to n-1 in steps of 1
plt.plot(*double_moving_avg(y))
```

Examples of all the plotting utilities are shown in the `examples` directory.

# Supported platforms

Precompiled wheels are provided for most common platforms.
Notably, they are not provided for 32-bit systems.
If no wheel is provided, `pip` should attempt a source install.
If all else fails, it is possible to install from source by pointing `pip` to Github directly:
```
pip install git+https://github.com/peleiden/pelutils.git@release#egg=pelutils
```
It is also possible to install from source using `pip`'s `--no-binary` option.
