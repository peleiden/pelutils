# pelutils
Utility functions that we commonly use including flexible parser, logger and time taker.

## Parsing
A combination of parsing CLI and config file arguments which allows for a powerful, easy-to-use workflow.
Useful for parametric methods such as machine learning.

A file `main.py` could contain:
```py
options = {
    "location": { "default": "local_train", "help": "save_location", "type": str },
    "learning-rate": { "default": 1.5e-3, "help": "Controls size of parameter update", "type": float },
    "gamma": { "default": 1, "help": "Use of generator network in updating", "type": float },
    "initialize-zeros": { "help": "Whether to initialize all parameters to 0", "action": "store_true" },
}
parser = Parser(options)
experiments = parser.parse()
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
# This explicitly logs a ValueError and then raises it
log.throw(ValueError("Your value is bad, and you should feel bad"))
# The zero-division error is logged
with log.log_errors:
    0 / 0

# User input
inp = log.input("WHAT... is your favourite colour? ")

# Log all logs from a function at the same time
# This is especially useful when using multiple threads so logging does not get mixed up
def fun():
    log("Hello there")
    log("General Kenobi!")
with mp.Pool() as p:
    p.map(collect_logs(fun), args)
```


## Time taking
Simple time taker inspired by Matlab Tic, Toc, which also has profiling tooling.

```py
tt = TickTock()
tt.tick()
<some task>
seconds_used = tt.tock()

for i in range(100):
    tt.profile("Repeated code")
    <some task>
    tt.profile("Subtask")
    <some subtask>
    tt.end_profile()
    tt.end_profile()
print(tt)  # Prints a table view of profiled code sections
```

## Data Storage
A data class that saves/loads its fields from disk.
Anything that can be saved to a `json` file will be.
Other data types will be saved to relevant file formats.
Currently, `numpy` arrays is the only supported data type that is not saved to the `json` file.

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
