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

## Logging

Easy to use logger which fits common needs.

```py
# Configure logger for the script
log.configure("path/to/save/log.log", "Title of log")

# Start logging
for i in range(70):  # Nice
    log("Execution %i" % i)

# Sections
log.section("New section in the logfile")

# Verbose logging for less important things
log.verbose("Will be logged")
with log.unverbose:
    log.verbose("Will not be logged")

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

# Disable printing if using tqdm
# Do not do this if the loop may be ended by a break statement!
for elem in log.tqdm(tqdm(range(5))):
    log(elem)  # Will be logged, but not printed

# User input
inp = log.input("WHAT... is your favourite colour? ")

# Log all logs from a function at the same time
# This is especially useful when using multiple threads so logging does not get mixed up
def fun():
    log("Hello there")
    log("General Kenobi!")
with mp.Pool() as p:
    p.map(collect_logs(fun), args)

# Disable printing when using tqdm so as to not print a million progress bars
for i in log.tqdm(tqdm(range(100))):
    log(i)  # i will be logged to logfile but not printed
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

# Profile a loop
# Do not do this if the loop may be ended by a break statement!
for elem in TT.profile_iter(range(100), "The second best task"):
    <some task>

# When using multiprocessing, it can be useful to simulate multiple hits of the same profile
with mp.Pool() as p, tt.profile("Processing 100 items on multiple threads", hits=100):
    p.map(100 items)
```

## Data Storage

A data class that saves/loads its fields from disk.
Anything that can be saved to a `json` file will be.
Other data types will be saved to relevant file formats.

```py
@dataclass
class Person(DataStorage):
    name: str
    age: int
    numbers: np.ndarray
    subfolder = "older"
    json_name = "yoda.json"

yoda = Person(name="Yoda", age=900, numbers=np.array([69, 420]))
yoda.save("old")
# Saved data at old/older/yoda.json
# {
#     "name": "Yoda",
#     "age": 900
# }
# There will also be a file named numbers.npy
yoda = Person.load("old")
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
```

This could then by run by
`python main.py data/my-big-experiment --learning_rate 1e-5`
or by
`python main.py data/my-big-experiment --config cfg.ini`
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
# Clear CUDA cache and synchronize
reset_cuda()

# Inference only: No gradients should be tracked in the following function
# Same as putting entire function body inside with torch.no_grad()
@no_grad
def infer():
    <code that includes feedforwarding>

# Feed forward in batches to prevent using too much memory
# Every time a memory allocation error is encountered, the number of batches is doubled
# Same as using y = net(x), but without risk of running out of memory
bff = BatchFeedForward(net, len(x))
y = bff(x)
# Change to another network
bff.update_net(net2)
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

