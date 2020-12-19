# 0.2.8

    - Add code to execute code with specific environment variables

# 0.2.7

    - Fix error where the full stacktrace was not printed by log.throw
    - set_seeds now checks if torch is available. This means torch seeds are still set without needing it as a dependency

# 0.2.6

    - Make Unverbose class private and update documentation
    - Update formatting when using .input

# 0.2.5

    - Add input method to logger

# 0.2.4

    - Better logging of errors

# 0.2.1 - BREAKING CHANGES

    - Removed torch as dependency

# 0.2.0 - BREAKING CHANGES

    - Logger is now a global variable. Logging should happen by importing the log variable and calling .configure to set it up. To reset the logger, .clean can be called.
    - It is still possible to just import Logger and use it in the traditional way, though .configure should be called first.
    - Changed timestamp function to give a cleaner output.
    - get_commit now returns None if gitpython is not installed.

# 0.1.2

    - Update documentation for logger and ticktock.
    - Fix bug where seperator was not an argument to Logger.__call__.

# 0.1.0

    - Include DataStorage.
    - Logger can throw errors and handle seperators.
    - TickTock includes time handling and units.
    - Minor parser path changes.

# 0.0.1

    - Logger, Parser, TickTock added from previous projects.
