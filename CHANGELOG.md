# History

## 3.0.0 - Breaking changes

- Strip all logged lines of extra whitespace
- Align logged lines with four space indents
- Do not automatically create subplots figure and axis in Figure
- Changed default axis timestamp labels to be more readable
- Support lists in moving average functions
- Changed DataStorage to have default name based on class name
- Non json-serializable data in DataStorage instances are now saved to a single pickle file
- Prevent NameError being raised if an exception was raised inside nested profiling without the use of `with TT.profile`

### Bug fixes

- Fixed missing `__init__.py` in `_entry_points` module

## 2.0.0 - Breaking changes

- Added `reset` method to `TickTock`
- Removed `TickTock.remove_outliers`
- Moved `is_windows` to static `OS` attribute, which also contains `is_mac` and `is_linux`
- Added `HardwareInfo`, which contains a bunch of system hardware information
- `Figure` now automatically creates necessary subdirectories
- Added `add_external_measurements` method to `TickTock`
- Added `tex` method to `Table` for producing LaTeX code for a `tabular` environment
- Replaced `clear_folders` argument in `Parser.parse_args` method with `JobDescription.prepare_directory` method
- `Parser` documentation files are now put in individual job directories when using `JobDescription.prepare_directory`
- `Parser.document` has been removed
- Changed from BSD-3-Clause license to MIT license

### Bug fixes

- Fixed different profiles with the same name in `TickTock` causing incorrect behavior
- Fixed `Parser` being unable to read cased arguments from config files

## 1.1.0

- Include `hashmap.c` license in distributions
- Include all header files in source distributions
- Fix `log.log_errors` logging `SystemExit(0)` as raised by `click` upon successful execution
- Moved away from `numpy` API for easier install
- Added `get_timestamp_for_files`
- Fixed various parser bugs

## 1.0.0 - Breaking changes, first stable release

- Removed `log.tqdm`
- Added binning functions to `pelutils.ds.plot`
- Added `pelutils.ds.distributions` with `scipy` distributions that use same notation as Jim Pitman's "Probability"
- Added `examples` directory, which currently only has plotting examples
- Removed `subfolder` attribute on `DataStorage` as this was cause for much confusion and many issues
- Changed pickle extension from `p` to `pkl`
- Added option to clear existing data folder saving with `DataStorage`
- Added indent option to `json` files saved by `DataStorage`
- Made naming of different submodules consistent
- Added `linecounter` entry point that allows plotting development of code in repositories over time
- Made `get_repo` return the absolute repository path
- Made logger use absolute instead of relative paths preventing issues with changing working directory
- Renamed `vline` to `hline` in `Table` as the line was horizontal rather than vertical
- Added `jsonl.dumps` and `jsonl.loads` and made all functions in `jsonl` module use same naming scheme as `json`
- Added support for Pytorch tensors to `c_ptr`
- Added `log.no_log` for disabling logging
- Renamed `Levels` to `LogLevels` as that makes it clearer in usage context
- `unique` can now take non-contiguous arrays and also has an `axis` argument
- Added a command line entry to examples, `pelexamples`
- Added a `binary_search` for searching in ordered iterables in `log(n)` time
- Added moving average function and variations thereof for plotting noisy data with uneven spacing
- Made `TickTock.tick` void and `TickTock.tock` raise `TickTockException` if `.tick` not called first
- Changed to `rapidjson` instead for built-in `json` module for all json operations for strictness and that sweet performance
- Added `reverse_line_iterator` for iterating through a file backwards
- Renamed `throws` to `raises`
- Reanedm `thousand_seps` to `thousands_seperators`
- Renamed HISTORY.md to CHANGELOG.md
- Made `get_timestamp` arguments keyword-only
- Added `restore_argv` decorator that allows safe testing of simulated `sys.argv`
- Added `except_keys` function for removing a list of keys from a dictionary
- Renamed `thousand_seps` to `thousands_seperators`
- Made C functions to work on most platforms
- Added `is_windows` function
- Removed `TickTock.profile_iter`
- Added `SimplePool` for testing with `multiprocessing.Pool`
- Renamed `MainTest` to `UnitTestCollection`
- Removed `BatchFeedForward`
- Added `Figure` plotting context class for easier plotting settings control
- Added convenience function for adding dates on the x axis, `get_dateticks`
- Added convenience function for getting path in test context, `UnitTestCollection.test_path`

### Bug fixes

- Fixed a bug where a backslash would sometimes be printed from the logger before square brackets
- Fixed `raises` throwing errors if error was not caught
- Made `thousands_seperators` work with negative numbers
- Made `corr_ci` handle all iterable types correctly

## 0.6.9 - Nice

- Made `load_jsonl` load the file lazily

## 0.6.7

- Logger can now be used without writing to file

## 0.6.6

- Fixed parser naming when using config files and not `multiple_jobs`
- Fixed parser naming when using cli only and `multiple_jobs`

## 0.6.5 - Breaking changes

- `Parser.parse` now returns only a single experiment dict if `multiple_jobs` is False
- Improved logger error messages
- Added `Parser.is_explicit` to check if an argument was given explicitly, either from CLI or a config file
- Fixed bug in parser, where if a type was not given, values from config files would not be used
- Made fields that should not be used externally private in parser
- Made `pelutils.ds.unique` slightly faster

## 0.6.4 - Breaking changes

- Commit is now logged as `DEBUG`
- Removed `BatchFeedForward.update_net`
- `BatchFeedForward` no longer requires batch size and increase factor as an argument
- Removed `reset_cuda` function, as was a too small and obscure function and broke distributed training
- Added `ignore_missing` field to `DataStorage` for ignoring missing fields in stored data

## 0.6.3 - Breaking changes

- Fixed bug where TickTock profiles would sometimes not be printed in the correct order
- Removed `TickTock.reset`
- Added `__len__` and `__iter__` methods to `TickTock`
- Added option to print standard deviation for profiles
- Renamed `TimeUnit` to `TimeUnits` to follow `enum` naming scheme
- Time unit lengths are now given in units/s rather than s/unit

## 0.6.2

- `TickTock.__str__` now raises a `ValueError` if profiling is still ongoing to prevent incorrect calculations
- Printing a `TickTock` instance now indents percentage of time spent to indicate task subsets

## 0.6.1

- Added `subfolder` argument to `Parser.document_settings`

## 0.6.0 - Breaking changes

- A global instance of `TickTock`, `TT`, has been added - similar to `log`
- Added `TickTock.profile_iter` for performing profiling over a for loop
- Fixed wrong error being thrown when keyboard interrupting within `with TT.profile(...)`
- All collected logs are now logged upon an exception being thrown when using `log.log_errors` and `collect_logs`
- Made `log.log_errors` capable of handling chained exeptions
- Made `log.throw` private, as it had little use and could be exploited
- `get_repo` no longer throws an error if a repository has not been found
- Added utility functions for reading and writing `.jsonl` files
- Fixed incorrect `torch` installations breaking importing `pelutils`

## 0.5.9

- Add `split_path` function which splits a path into components
- Fix bug in `MainTest` where test files where not deleted

## 0.5.7

- Logger prints to `stderr` instead of `stdout` at level WARNING or above
- Added `log.tqdm` that disables printing while looping over a `tqdm` object
- Fixed `from __future__ import annotations` breaking `DataStorage`

## 0.5.6

- DataStorage can save all picklable formats + `torch.Tensor` specifically

## 0.5.5

- Test logging now uses `Levels.DEBUG` by default
- Added `TickTock.fuse_multiple` for combining several `TickTock` instances
- Fixed bugs when using multiple `TickTock` instances
- Allow multiple hits in single profile
- Now possible to profile using `with` statement
- Added method to logger to parse boolean user input
- Added method to `Table` for adding vertical lines manually

## 0.5.4 - Breaking changes

- Change log error colour
- Replace default log level with print level that defaults to `Levels.INFO`

  `__call__` now always defaults to `Levels.INFO`
- Print microseconds as `us` instead of `mus`

## 0.5.3

- Fixed missing regex requirement

## 0.5.2

- Allowed disabling printing by default in logger

## 0.5.1

- Fixed accidental rich formatting in logger
- Fixed logger crashing when not configured

## 0.5.0 - Breaking changes

- Added np.unique-style unique function to `ds` that runs in linear time but does not sort
- Replaced verbose/non-verbose logging with logging levels similar to built-in `logging` module
- Added `with_print` option to `log.__call__`
- Undid change from 0.3.4 such that `None` is now logged again
- Added `format` module. Currently supports tables
- Updated stringification of profiles to include percentage of parent profile
- Added `throws` function that checks if a functions throws an exception of a specific type
- Use `Rich` for printing to console when logging

## 0.4.1

- Added append mode to logger to append to old log files instead of overwriting

## 0.4.0

- Added `ds` submodule for data science and machine learning utilities

  This includes `PyTorch` utility functions, statistics, and `matplotlib` default values

## 0.3.4

- Logger now raises errors normally instead of using `throw` method

## 0.3.3

- `get_repo` now accepts a custom path search for repo as opposed to always using working dir

## 0.3.2

- `log.input` now also accepts iterables as input

  For such inputs, it will return a generator of user inputs

## 0.3.1 - Breaking changes

- Added functionality to logger for logging repository commit
- Removed function `get_commit`
- Added function `get_repo` which returns repository path and commit

  It attempts to find a repository by searching from working directory and upwards
- Updates to examples in `README` and other minor documentation changes
- `set_seeds` no longer returns seed, as this is already given as input to the function

## 0.3.0 - Breaking changes

- Only works for Python 3.7+

- If logger has not been configured, it now does no logging instead of crashing

  This prevents dependecies that use the logger to crash the program if it is not used
- `log.throw` now also logs the actual error rather than just the stack trace
- `log` now has public property `is_verbose`
- Fixed `with log.log_errors` always throwing errors
- Added code samples to `README`
- `Parser` no longer automatically determines if experiments should be placed in subfolders

  Instead, this is given explicitly as an argument to `__init__`

  It also supports boolean flags in the config file

## 0.2.13

- Readd clean method to logger

## 0.2.12 - Breaking changes

- The logger is now solely a global variable

  Different loggers are handled internally in the global _Logger instance

## 0.2.11

- Add catch property to logger to allow automatically logging errors with with
- All code is now indented using spaces

## 0.2.10

- Allow finer verbosity control in logger
- Allow multiple log commands to be collected and logged at the same time
- Add decorator for aforementioned feature
- Change thousand_seps from TickTock method to stand-alone function in `__init__`
- Verbose logging now has same signature as normal logging

## 0.2.8

- Add code to execute code with specific environment variables

## 0.2.7

- Fix error where the full stacktrace was not printed by log.throw
- `set_seeds` now checks if torch is available

  This means torch seeds are still set without needing it as a dependency

## 0.2.6 - Breaking changes

- Make Unverbose class private and update documentation
- Update formatting when using .input

## 0.2.5

- Add input method to logger

## 0.2.4

- Better logging of errors

## 0.2.1 - Breaking changes

- Removed torch as dependency

## 0.2.0 - Breaking changes

- Logger is now a global variable, `log`

  Logging should happen by importing the log variable and calling `.configure` to set it up

  To reset the logger, `.clean` can be called
- It is still possible to just import `Logger` and use it in the traditional way, though `.configure` should be called first
- Changed timestamp function to give a cleaner output
- `get_commit` now returns `None` if `gitpython` is not installed

## 0.1.2

- Update documentation for logger and ticktock
- Fix bug where seperator was not an argument to `Logger.__call__`

## 0.1.0

- Include `DataStorage`
- Logger can throw errors and handle seperators
- TickTock includes time handling and units
- Minor parser path changes

## 0.0.1

- Logger, Parser, and TickTock added from previous projects
