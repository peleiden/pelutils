from __future__ import annotations
import os, sys
from argparse import ArgumentParser, RawTextHelpFormatter
from configparser import ConfigParser
from typing import Any

from pprint import pformat


class Parser:
    """
    Maintains multiple parsers to allow a workflow of mixing use of config files and CLI arguments.

    Can read from single .ini file and CLI arguments. CLI arguments overwrite settings in all experiments defined if ini file.
    In .ini file, defaults for all runs can be set in [DEFAULT] section and multiple runs can be added with their own section.

    The parser returns a list of dicts of the parsed settings for the experiments.

    Quick example:
    A file `main.py` could contain:
    ```
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
    """

    _with_config: bool
    location: str
    explicit_args: list[set[str]]

    def __init__(
        self,
        options: dict,
        name = "Experiment",
        description = "Run experiments with these options",
        show_defaults = True,
        description_last = False,
        multiple_jobs = True,  # If this is True, all jobs are put in subfolders
    ):
        """
        Receives a dict of options.
        This should be a dict of dicts where each dict corresponds to an option with the key as the name.
        In the dict for each option, the key "default" should store the default value and all other keys should correspond to
        kwargs in ArgumentParser.add_argument.
        """
        self.options = options
        self._bool_opts = { argname: settings["action"] == "store_false" for argname, settings
            in options.items() if settings.get("action") in ("store_false", "store_true") }
        self._defaults = dict()  # { argname: default value }
        self.name = name
        self.multiple_jobs = multiple_jobs

        # Main parser for CLI arguments
        self._argparser = ArgumentParser(
            description = description,
            formatter_class = RawTextHelpFormatter,
        )
        self._argparser.add_argument("location", help="Location of output", type=str)
        self._argparser.add_argument("-c", "--config",
            help="Location of configuration file to use (if any). Config file should follow .ini format.", metavar="FILE")
        if description_last:
            self._argparser.epilog = description
            self._argparser.description = None

        abbrvs = {"-h", "-c"}  # -h is reserved for --help and -c for --config
        for argname, settings in self.options.items():
            self._defaults[argname] = settings.pop("default") if argname not in self._bool_opts else self._bool_opts[argname]

            if show_defaults and "help" in settings:
                settings["help"] += f"\n  Default = {self._defaults[argname]}"

            # Add argument and optionally abbrevation if no conflict
            abbrv = f"-{argname[0]}"
            if abbrv in abbrvs:
                self._argparser.add_argument(f"--{argname}", **settings)
            else:
                self._argparser.add_argument(abbrv, f"--{argname}", **settings)
                abbrvs.add(abbrv)

        # Parser for config file
        self._configparser = ConfigParser(allow_no_value=True)

    def _parse_known_args(self) -> dict[str, Any]:
        """ Returns a dict containing the arguments given explicitly from the command line """
        args, __ = self._argparser.parse_known_args()
        args = vars(args)
        known_args = dict()
        for argname, value in args.items():
            if value is None or (argname in self._bool_opts and self._bool_opts[argname] == value):
                continue
            known_args[argname] = value
        return known_args

    def parse(self) -> list[dict[str, Any]] | dict[str, Any]:
        """ Parse arguments and return a dict for each. Only a single dict is returned if multiple_jobs is False """
        # Parse command line arguments
        args = self._parse_known_args()
        self.location = args["location"]
        explicit_cli_args = set(args)

        # Parse config files
        experiments, explicit_config_args = self._read_config(args)
        self._with_config = bool(experiments)

        if not self._with_config:  # If CLI arguments only
            args = { **self._defaults, **args }
            if self.multiple_jobs:
                args["location"] = os.path.join(self.location, self.name)
            experiments.append({"name": self.name, **args})
            self.explicit_args = [explicit_cli_args]
        else:
            self.explicit_args = [set.union(explicit_cli_args, conf_args) for conf_args in explicit_config_args]

        # Replace - with _ as argparse also does. This allows parsing experiments to a function using **
        for i in range(len(experiments)):
            experiments[i] = { kw.replace("-", "_"): v for kw, v in experiments[i].items() }
            self.explicit_args[i] = { arg.replace("-", "_") for arg in self.explicit_args[i] }

        return experiments if self.multiple_jobs else experiments[0]

    def _set_bools_in_dict(self, d: dict[str, Any]):
        """ Boolean arguments present are set to the negation of their default values
        Those not present are set to default values """
        for argname, default_value in self._bool_opts.items():
            if argname in d and not isinstance(d[argname], bool):
                d[argname] = not default_value
            else:
                d[argname] = default_value

    def _read_config(self, cli_args: dict) -> tuple[list[dict], list[set]]:
        """ Parses a configuration file. Options in cli_args override config files
        Returns a list of experiments and a list of explicitly given config arguments """
        experiments = list()
        explicit_config_args = list()

        if "config" in cli_args:
            if not self._configparser.read([cli_args["config"]]):
                raise FileNotFoundError(f"Could not find config file {cli_args['config']}")

            # User set DEFAULT section should overwrite the defaults
            default_config_items = dict(self._configparser.items("DEFAULT"))
            self._defaults = { **self._defaults,  **default_config_items }

            if len(self._configparser) > 1 and not self.multiple_jobs:
                raise ValueError(
                    "Multiple jobs are given in the config file, however the parser has been configured for a single job"
                )

            # Each other section corresponds to an experiment
            for experiment_name in self._configparser.sections() if self._configparser.sections() else ["DEFAULT"]:
                config_items = dict(self._configparser.items(experiment_name))
                explicit_config_args.append(
                    set.union(set(default_config_items), config_items)
                )
                config_items = {
                    kw: self.options[kw]["type"](v) if "type" in self.options[kw] else v
                    for kw, v in config_items.items()
                }
                options = { **self._defaults, **config_items }
                self._set_bools_in_dict(options)

                experiment_name = experiment_name if experiment_name != "DEFAULT" else self.name

                # Put experiments into single subfolders
                location = os.path.join(self.location, experiment_name)\
                    if self.multiple_jobs else self.location

                args = cli_args.copy()
                del args["config"]
                experiments.append({
                    **options,
                    **args,
                    "name": experiment_name,
                    "location": location,
                })

        return experiments, explicit_config_args

    def document_settings(self, subfolder=""):
        """ Saves all settings used for experiments for reproducability """
        os.makedirs(os.path.join(self.location, subfolder), exist_ok = True)

        with open(os.path.join(self.location, subfolder, self.name + "_config.ini"), "w") as f:
            if self._with_config:
                self._configparser.write(f)
            f.write(f"\n# Run command\n# {' '.join(sys.argv)}\n")
            str_defaults = pformat(self._defaults).replace("\n", "\n# ")
            f.write(f"\n# Default configuration values at runtime\n# {str_defaults}")

    def is_explicit(self, argname: str, job: int=None) -> bool:
        """ Checks whether a given argument was set explicitly in a config file or from cli
        If self.multiple_jobs is False, job should not be given. Otherwise, a job number must be given """
        return argname in self.explicit_args[job if self.multiple_jobs else 0]
