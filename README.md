# pelutils

Various utilities useful for Python projects. Features include

- Feature-rich logger using `Rich` for colourful printing
- Parsing for combining config files and command-line arguments - especially useful for parametric methods
- Time taking and profiling
- Easy to use data storage class for easy data saving and loading
- Table formatting
- Miscellaneous standalone functions providing various functionalities - see `pelutils/__init__.py`
- Data-science submodule with extra utilities for statistics, plotting, and machine learning using `PyTorch`
- `unique` function similar to `np.unique` but in linear time (currently Linux x86_64 only)

`pelutils` supports Python 3.7+.

[![pytest](https://github.com/peleiden/pelutils/actions/workflows/pytest.yml/badge.svg?branch=master)](https://github.com/peleiden/pelutils/actions/workflows/pytest.yml)
[![Coverage Status](https://coveralls.io/repos/github/peleiden/pelutils/badge.svg?branch=master)](https://coveralls.io/github/peleiden/pelutils?branch=master)

## Logging

Easy to use logger which fits common needs.

```py
log("This is printed but not saved to a log file as the logger has not been configured")

# Configure logger for the script
log.configure("path/to/save/log.log", "Optional title of log")

# Start logging
for i in range(70):  # Nice
    log("Execution %i" % i)

# Sections
log.section("New section in the logfile")

# Adjust logging levels
log.warning("Will be logged")
with log.level(LogLevels.ERROR):  # Only log at ERROR level or above
    log.warning("Will not be logged")
with log.no_log():
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
inp = log.input("WHAT... is your favourite colour? ")

# Log all logs from a function at the same time
# This is especially useful when using multiple threads so logging does not get mixed up
def fun():
    log("Hello there")
    log("General Kenobi!")
with mp.Pool() as p:
    p.map(collect_logs(fun), args)
```

## Time Taking and Profiling

Simple time taker inspired by Matlab Tic, Toc, which also has profiling tooling.

```py
TT.tick()
<some task>
seconds_used = TT.tock()

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
    if tt2.tock() > t2_interval:
        <task 2>
    time.sleep(0.01)
```

## Data Storage

The DataStorage class is an augmentation of the dataclass that incluces save and load functionality.

Currently works specifically with:
- Numpy arrays (`numpy.ndarray`)
- Torch tensors (`torch.Tensor`)
- Any json serializable type - that is, it should be savable by json.dump
All other data structures are pickled.

DataStorage classes must inherit from DataStorage and be annotated with `@dataclass`.
It is further possible to give arguments to the class definition:
- `json_name`: Name of the saved json file
- `indent`: How many spaces to use for indenting in the json file

Usage example:
```py
@dataclass
class ResultData(DataStorage, json_name="game.json", indent=4):
    shots: int
    goalscorers: list
    dists: np.ndarray

rdata = ResultData(shots=1, goalscorers=["Max Fenger"], dists=np.ones(22)*10)
rdata.save("max")
# Now shots and goalscorers are saved in <pwd>/max/game.json and dists in <pwd>/max/dists.npy

# Then to load
rdata = ResultData.load("max")
print(rdata.goalscorers)  # ["Max Fenger"]
```

## Parsing

A combination of parsing CLI and config file arguments which allows for a powerful, easy-to-use workflow.
Useful for parametric methods such as machine learning.

A file `main.py` could contain:
```py
options = {
    "learning-rate": { "default": 1.5e-3, "help": "Controls size of parameter update", "type": float },
    "gamma": { "default": 1, "help": "Use of generator network in updating", "type": float },
    "initialize-zeros": { "help": "Whether to initialize all parameters to 0", "action": "store_true" },
}
parser = Parser(options)
location = parser.location  # Experiments are stored here
experiments = parser.parse()
parser.document_settings()  # Save a config file to reproduce the experiment
# Run each experiment
for args in experiments:
    run_experiment(location, args)

# Alternatively, if there is only ever a single job
parser = Parser(options, multiple_jobs=False)
location = parser.location
args = parser.parse()
parser.document_settings()
run_experiment(location, args)

# Check if an argument has been given explictly, either from cli or config file, or if default value is used
parser.is_explicit("learning-rate")
```

This could then by run by
`python main.py data/my-big-experiment --learning-rate 1e-5`
or by
`python main.py data/my-big-experiment --config cfg.ini`
or using a combination where CLI args takes precedence:
`python main.py data/my-big-experiment --config cfg.ini --learning-rate 1e-5`
where `cfg.ini` could contain

```
[DEFAULT]
gamma = 0.95

[RUN1]
learning-rate = 1e-4
initialize-zeros

[RUN2]
learning-rate = 1e-5
gamma = 0.9
```

# pelutils.ds

This submodule contains various utility functions for data science and machine learning. To make sure the necessary requirements are installed, install using
```
pip install pelutils[ds]
```
Note that in some terminals, you will instead have to write
```
pip install pelutils\[ds\]
```

## PyTorch

All PyTorch functions work independently of whether CUDA is available or not.

```py
# Inference only: No gradients should be tracked in the following function
# Same as putting entire function body inside with torch.no_grad()
@no_grad
def infer():
    <code that includes feedforwarding>

# Feed forward in batches to prevent using too much memory
# Every time a memory allocation error is encountered, the number of batches is doubled
# Same as using y = net(x), but without risk of running out of memory
# Gradients are not tracked
bff = BatchFeedForward(net)
y = bff(x)
```

## Statistics

Includes various commonly used statistical functions.

```py
# Get one sided z value for exponential(lambda=2) distribution with a significance level of 1 %
zval = z(alpha=0.01, two_sided=False, distribution=scipy.stats.expon(loc=1/2))

# Get correlation, confidence interval, and p value for two vectors
a, b = np.random.randn(100), np.random.randn(100)
r, lower_r, upper_r, p = corr_ci(a, b, alpha=0.01)
```

## Matplotlib

Contains predefined rc params, colours, and figure sizes.

```py
# Set wide figure size
plt.figure(figsize=figsize_wide)

# Use larger font for larger figures - works well with predefined figure sizes
update_rc_params(rc_params)

# 15 different, unique colours
c = iter(colours)
for i in range(15):
    plt.plot(x[i], y[i], color=next(c))
```

# Installing on unsupported platforms

Mostly, `pelutils` can be install with `pip install pelutils`, but some platforms and Python versions are not supported.
These limitations are due to what dependencies, notably PyTorch, support.
Most importantly, wheels for 32-bit platforms are not provided, meaning that the normal install method will not work on a Raspberry Pi.
If your platform is not supported, but you do not requires the `ds` submodule, and thus PyTorch as a dependency, you can try installing `pelutils` directly from GitHub with
```
pip install git+https://github.com/peleiden/pelutils.git#egg=pelutils
```
