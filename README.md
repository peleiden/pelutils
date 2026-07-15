# pelutils

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![basedpyright](https://img.shields.io/endpoint?url=https://docs.basedpyright.com/latest/badge.json)](https://docs.basedpyright.com)
[![checks](https://github.com/peleiden/pelutils/actions/workflows/checks.yml/badge.svg?branch=master)](https://github.com/peleiden/pelutils/actions/workflows/checks.yml)
[![Coverage Status](https://coveralls.io/repos/github/peleiden/pelutils/badge.svg?branch=master)](https://coveralls.io/github/peleiden/pelutils?branch=master)
[![PyPi](https://img.shields.io/pypi/v/pelutils.svg)](https://pypi.org/project/pelutils/)
[![Python versions](https://img.shields.io/pypi/pyversions/pelutils)](https://img.shields.io/pypi/pyversions/pelutils)
[![image](https://img.shields.io/pypi/l/pelutils.svg)](https://github.com/peleiden/pelutils/blob/master/LICENSE.txt)
[![readthedocs](https://app.readthedocs.org/projects/pelutils/badge/?version=latest)](https://pelutils.readthedocs.io/en/latest/)

**Batteries-included utilities for Python projects**

Every project, experiment, or one-off script inevitably ends up reinventing much of
the same plumbing: some way to time a loop, saving and loading data to and from disk
in a convenient and human-readable manner, a decent logger, parsing a config file, a readable table.
`pelutils` bundles the good versions of these so you can get straight to the actual
work. It has no required dependencies beyond the scientific-Python staples, ships
type hints (including `py.typed`), and is easy to start using.

📖 **Full documentation: [pelutils.readthedocs.io](https://pelutils.readthedocs.io)**

## Highlights

- **Logger** — easy-to-use, colourful console output, log files with rotation, automatic
  stacktrace capture, and safe logging from multiple processes.
- **Timer & profiler** — a Matlab-style `tick`/`tock` timer and a near-zero-overhead
  profiler that prints a readable breakdown of where your time goes.
- **`UniversalJsonModel`** — a `pydantic.BaseModel` that can save *any* attribute to a
  human-readable JSON file (numpy arrays, tensors, and other unserialisable types are
  pickled transparently) and load it straight back.
- **`JobParser`** — one parser that unifies command-line arguments and config files,
  with support for running many jobs from a single config and auto-documenting them.
- **`unique`** — a linear-time drop-in for `numpy.unique`, dramatically faster on
  large arrays (backed by a small C extension).
- **Data-science helpers** — a `matplotlib` `Figure` context manager, histogram
  binning, reparametrised scipy distributions, `z_score`, LaTeX-ready tables, and
  numpy type aliases.

## Installation

```sh
pip install pelutils
```

`pelutils` supports Python 3.11+. A small subset of functionality can additionally
make use of [`PyTorch`](https://pytorch.org), which must be installed separately.

> **Importing:** every feature lives in its own submodule and must be imported from
> there — e.g. `from pelutils.logging import log`. Only `__version__` is exported at
> the top level. See the [docs](https://pelutils.readthedocs.io) for the full API.

## Logging

A simple but feature-rich logger that prints in colour and writes to a log file.

```py
from pelutils.logging import log, LogLevels

# Set up the logger by giving it the file to write to
# Omit the path to only print, never write a file
log.configure("run.log")

log.section("Starting run")           # Highlighted section header
log("Plain info line")                # Logs at INFO level
log.warning("Something looks off")
log.debug("Extra detail", "on two lines")

# Log exceptions with their full (chained) stacktrace
with log.log_errors:
    risky_operation()

# Temporarily change or silence the log level
with log.level(LogLevels.ERROR):
    log.warning("Suppressed")

# Rotate the log file by time or size
log.configure("run.log", rotation="day")    # or "1 GB", "hour", ...
```

When using multiprocessing, wrap a worker in `with log.collect:` so its lines are
written together instead of interleaving with other processes. See the
[logging docs](https://pelutils.readthedocs.io/en/latest/api/pelutils.logging.html) for input helpers, multiple loggers,
and more.

## Timing and profiling

Inspired by Matlab's `tic`/`toc`, with a profiler built on top.

```py
from pelutils.ticktock import TT

# Time a single block
TT.tick()
do_work()
seconds = TT.tock()

# Profile named sections in a loop, then print a breakdown
# Nested profiles are fully supported
for batch in batches:
    with TT.profile("Load"):
        x = load(batch)
    with TT.profile("Forward pass"):
        model(x)

print(TT)  # Table of hits, total time, and time share per section
```

`with TT.profile("name", hits=n):` records `n` hits at once, which is handy for very
tight loops or for a block that processes `n` items in parallel. `TT.do_at_interval(...)`
turns the same instance into a throttle for periodic tasks. The default `TT` is a
shared instance; construct your own with `TickTock()` when you need isolation.

## Serialisation

`UniversalJsonModel` extends `pydantic.BaseModel` with `save`/`load` methods and can
serialise attributes that pydantic cannot — numpy arrays, tensors, and arbitrary
objects are base64-pickled inline, everything else stays plain, human-readable JSON.
Long lists are wrapped to the line-length limit instead of one element per line.

```py
import numpy as np
from pydantic import BaseModel
from pelutils.serialization import UniversalJsonModel
from pelutils.types import FloatArray

class Nested(BaseModel):
    label: str

class Result(UniversalJsonModel):
    accuracy: float
    predictions: FloatArray   # numpy arrays are handled automatically
    meta: Nested

result = Result(
    accuracy=0.97,
    predictions=np.arange(5, dtype=np.float16),
    meta=Nested(label="run-1"),
)

result.save("results/run-1.json")
result = Result.load("results/run-1.json")
```

Use `to_json_dict()` / `from_json_dict(...)` to convert to and from a plain dict
without touching the filesystem — useful for nesting inside other structures. The
`pretty_json` helper function is also available on its own. The `serialization`
module also includes JSONL read/write helpers (`jsonl_dump`, `jsonl_load`, ...)
with largely the same interface as is provided by the built-in `json` module.

## Config and command-line argument parsing

`JobParser` combines typed command-line options with INI config files. CLI values
override config values, which override defaults. Declare `RequiredArg` for values
every job must provide, `OptionalArg` for values with defaults, and `Flag` for
booleans. Names are `--kebab-case` on the command line and `snake_case` attributes on
the resulting job.

```py
from pathlib import Path
from pelutils.job_parser import Flag, JobParser, OptionalArg, RequiredArg

parser = JobParser(
    RequiredArg("data-path", help="Training data directory"),
    OptionalArg("learning-rate", default=1e-4, type=float, help="Optimizer learning rate"),
    Flag("fp16", help="Use mixed precision"),
    multiple_jobs=True,
)

for job in parser.parse_jobs():
    print(job.name, job.data_path, job.learning_rate, job.fp16)
    job.write_documentation(Path("runs") / job.name / "arguments.ini")
    # ... run your application with the resolved job values
```

A single config file can define several named jobs (with a shared `[DEFAULT]`
section), and one CLI override applies to all of them:

```console
python main.py --config-file config.ini --learning-rate 5e-5
```

For a single job, drop `multiple_jobs=True` and call `parse_job()` instead. A config
path can target one section directly, e.g. `--config-file config.ini:low-lr`. See the
[job parser docs](https://pelutils.readthedocs.io/en/latest/api/pelutils.job_parser.html) for auto-documentation details.

## Fast `unique`

A linear-time alternative to `numpy.unique`, significantly faster on large arrays. It
also accepts torch tensors and pandas series. The returned elements are unsorted.

```py
import numpy as np
from pelutils.misc import unique

x = np.random.randint(0, 100, size=10_000_000)
values = unique(x)
values, index, inverse, counts = unique(
    x, return_index=True, return_inverse=True, return_counts=True,
)
```

## Data science

### Statistics

Common statistical helpers, plus wrappers around scipy distributions reparametrised
as in Jim Pitman's *Probability* (rather than scipy's `loc`/`scale`, which are
unintuitive for many distributions).

```py
from pelutils.stats import z_score
from pelutils.stats import expon

# 95 % confidence interval half-width for a standard normal (defaults give ~1.96)
half_width = std * z_score()

# One-sided z value for an Exponential(λ=2) at the 1 % significance level
zval = z_score(alpha=0.01, two_sided=False, distribution=expon(lambda_=2))
```

### Plotting

The `Figure` context manager fixes common `matplotlib` annoyances — sensible default
figure and font sizes, easy styling — and saves and closes the figure for you while
restoring `rcParams` afterwards.

```py
import matplotlib.pyplot as plt
from pelutils.plots import Figure, histogram, normal_binning

with Figure("plot.png", figsize=(20, 10), fontsize=20):
    plt.scatter(x, y, label="Data")
    plt.grid()
    plt.title("Very nice plot")
# Saved to plot.png and closed here

# histogram returns x and y coordinates ready for unpacking
plt.plot(*histogram(data, binning_fn=normal_binning))
```

Three binning functions are provided — `linear_binning`, `log_binning`, and
`normal_binning` (more resolution near the centre of roughly-normal data) — and custom
binning functions are supported. See the
[plotting docs](https://pelutils.readthedocs.io/en/latest/api/pelutils.plots.html).

### Numpy type aliases

Type aliases so you (and your type checker) do not have to track array dtypes by hand.

```py
from pelutils.types import FloatArray, IntArray, BoolArray

def process(features: FloatArray, labels: IntArray, mask: BoolArray): ...
```

## Also included

- `pelutils.misc.Table` — build aligned text tables which can also be easily export to LaTeX with `Table.to_latex()`.
- `pelutils.misc.hardware_info` / `OS` — describe the machine the code runs on.
- `pelutils.misc.git_repo_info` — the repo and commit the code is executing in.
- Assorted file and dict helpers (`reverse_line_iterator`, `except_keys`, ...).

## Supported platforms

Precompiled wheels are provided for most common platforms (not 32-bit systems). If no
wheel matches, `pip` builds from source which requires `<Python.h>` — install it with
`sudo apt install python3-dev` (Ubuntu) or `sudo dnf install python3-devel` (Fedora).
