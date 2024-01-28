# pelutils

[![pytest](https://github.com/peleiden/pelutils/actions/workflows/pytest.yml/badge.svg?branch=master)](https://github.com/peleiden/pelutils/actions/workflows/pytest.yml)
[![Coverage Status](https://coveralls.io/repos/github/peleiden/pelutils/badge.svg?branch=master)](https://coveralls.io/github/peleiden/pelutils?branch=master)

Various utilities useful for Python projects. Features include

- A simple and powerful logger with colourful printing and stacktrace logging
- Parsing for combining config files and command-line arguments - especially useful for algorithms with several parameters
- A timer inspired by Matlab's `tic` and `toc`
- Simple code profiler
- An extension to the built-in `dataclass` for saving and loading data
- Table formatting
- Miscellaneous standalone functions - see `pelutils/__init__.py`
- Data-science submodule with extra utilities for statistics, plotting with `matplotlib`, and machine learning using `PyTorch`
- Linear time `unique` function in the style of `numpy.unique`

`pelutils` supports Python 3.9+.

To install, simply run `pip install pelutils`.
A small subset of the functionality requires `PyTorch`, which has to be installed separately.

## Timing and Code Profiling

Simple time taker inspired by Matlab Tic, Toc, which also has profiling tooling.

```py
# Time a task
TT.tick()
<some task>
seconds_used = TT.tock()

# Profile a for loop
for i in range(100):
    TT.profile("Repeated code")
    <some task>
    TT.profile("Subtask")
    <some subtask>
    TT.end_profile()
    TT.end_profile()
print(TT)  # Prints a table view of profiled code sections

# Alternative syntax using with statement
with TT.profile("The best task"):
    <some task>

# When using multiprocessing, it can be useful to simulate multiple hits of the same profile
with mp.Pool() as p, TT.profile("Processing 100 items on multiple threads", hits=100):
    p.map(100 items)
# Similar for very quick loops
a = 0
with TT.profile("Adding 1 to a", hits=100):
    for _ in range(100):
        a += 1

# Examples so far use a global TickTock instance, which is convenient,
# but it can also be desirable to use for multiple different timers, e.g.
tt1 = TickTock()
tt2 = TickTock()
t1_interval = 1  # Do task 1 every second
t2_interval = 2  # Do task 2 every other second
tt1.tick()
tt2.tick()
while True:
    if tt1.tock() > t1_interval:
        <task 1>
        tt1.tick()
    if tt2.tock() > t2_interval:
        <task 2>
        tt2.tick()
    time.sleep(0.01)
```

## Data Storage

The DataStorage class is an augmentation of the dataclass that incluces save and load functionality.
This simplifies saving data, as only save command has to be issued for all data, and it keeps type
hinting when loading data compared to e.g. a dictionary.

Data is in general preserved exactly as-is when saved data is loaded into memory with few exceptions.
Notably, tuples are considered json-serializble, and so will be saved to the json file and will be
loaded as lists.

Usage example:

```py
@dataclass
class ResultData(DataStorage):
    shots: int
    goalscorers: list
    dists: np.ndarray

rdata = ResultData(shots=1, goalscorers=["Max Fenger"], dists=np.ones(22)*10)
rdata.save("max")
# Now shots and goalscorers are saved in <pwd>/max/ResultData.json and dists in <pwd>/max/ResultData.pkl

# Then to load
rdata = ResultData.load("max")
print(rdata.goalscorers)  # ["Max Fenger"]
```

## Parsing

A parsing tool for combining command-line and config file arguments.
Useful for parametric methods such as machine learning.
The first argument must always be a path. This can for instance be used to put log files, results, plots etc.

Consider the execution of a file `main.py` with the command line call
```
python main.py path/to/put/results -c path/to/config/file.ini --data-path path/to/data
```
The config file could contain
```
[DEFAULT]
fp16
learning-rate=1e-4

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
location = parser.location  # Experiments are stored here. In this case path/to/put/results
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

# Data Science

This submodule contains various utility functions for data science, statistics, plotting, and machine learning.

## Deep Learning

## Statistics

Includes various commonly used statistical functions.

```py
# Get one sided z value for exponential(lambda=2) distribution with a significance level of 1 %
zval = z(alpha=0.01, two_sided=False, distribution=scipy.stats.expon(loc=1/2))

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
