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

    with_config: bool
    location: str

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
        self.defaults = dict()  # { argname: default value }
        self.name = name
        self.multiple_jobs = multiple_jobs

        # Main parser for CLI arguments
        self.argparser = ArgumentParser(
            description = description,
            formatter_class = RawTextHelpFormatter,
        )
        self.argparser.add_argument("location", help="Location of output", type=str)
        self.argparser.add_argument("-c", "--config",
            help="Location of configuration file to use (if any). Config file should follow .ini format.", metavar="FILE")
        if description_last:
            self.argparser.epilog = description
            self.argparser.description = None

        abbrvs = set(["-h", "-c"])  # -h is reserved for --help and -c for --config
        for argname, settings in self.options.items():
            self.defaults[argname] = settings.pop("default") if argname not in self._bool_opts else self._bool_opts[argname]

            if show_defaults and "help" in settings:
                settings["help"] += f"\n  Default = {self.defaults[argname]}"

            # Add abbreviation if no conflict
            abbrv = f"-{argname[0]}"  # TODO: Use 3.8 syntax (walrus)
            if abbrv in abbrvs:
                self.argparser.add_argument(f"--{argname}", **settings)
            else:
                self.argparser.add_argument(abbrv, f"--{argname}", **settings)
                abbrvs.add(abbrv)

        # Parser for config file
        self.configparser = ConfigParser(allow_no_value=True)

    def _parse_known_args(self) -> dict[str, Any]:
        """ Returns a dict containing the arguments given explicitly from the command line """
        args, __ = self.argparser.parse_known_args()
        args = vars(args)
        known_args = dict()
        for argname, value in args.items():
            if value is None:
                continue
            elif argname in self._bool_opts and self._bool_opts[argname] == value:
                continue
            known_args[argname] = value
        return known_args

    def parse(self) -> list[dict[str, Any]]:
        """ Parse arguments and return a dict for each """
        # Parse command line arguments
        args = self._parse_known_args()
        self.location = args["location"]

        # Parse config files
        experiments, self.with_config = self._read_config(args)

        if not self.with_config:  # If CLI arguments only
            args = { **self.defaults, **args }  # TODO: Use 3.9 syntax
            args["location"] = os.path.join(self.location, self.name)\
                if self.multiple_jobs else self.location
            experiments.append({"name": self.name, **args})

        # Replace - with _ as argparse also does. This allows parsing experiments to a function using **
        for i in range(len(experiments)):
            experiments[i] = { kw.replace("-", "_"): v for kw, v in experiments[i].items() }

        return experiments

    def _set_bools_in_dict(self, d: dict[str, Any]):
        """ Boolean arguments present are set to the negation of their default values
        Those not present are set to default values """
        for argname, default_value in self._bool_opts.items():
            if argname in d:
                if isinstance(d[argname], bool):
                    continue
                d[argname] = not default_value
            else:
                d[argname] = default_value

    def _read_config(self, cli_args: dict) -> tuple[list, bool]:
        experiments = list()

        if "config" in cli_args:
            if not self.configparser.read([cli_args["config"]]):
                raise FileNotFoundError(f"Could not find config file {cli_args['config']}")

            # User set DEFAULT section should overwrite the defaults
            default_config_items = dict(self.configparser.items("DEFAULT"))
            self.defaults = {**self.defaults,  **default_config_items}  # TODO: Use 3.9 syntax

            if len(self.configparser) > 1 and not self.multiple_jobs:
                raise ValueError("Multiple jobs are given in the config file, "
                    "however the parser has been configured for a single job")

            # Each other section corresponds to an experiment
            for experiment_name in self.configparser.sections() if self.configparser.sections() else ["DEFAULT"]:
                config_items = dict(self.configparser.items(experiment_name))
                config_items = { kw: self.options[kw]["type"](v) for kw, v in config_items.items() if "type" in self.options[kw] }
                options = {**self.defaults, **config_items}  # TODO: Use 3.9 syntax
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

        return experiments, "config" in cli_args

    def document_settings(self, subfolder=""):
        """ Saves all settings used for experiments for reproducability """
        os.makedirs(os.path.join(self.location, subfolder), exist_ok = True)

        with open(os.path.join(self.location, subfolder, self.name + "_config.ini"), "w") as f:
            if self.with_config:
                self.configparser.write(f)
            f.write(f"\n# Run command\n# {' '.join(sys.argv)}\n")
            str_defaults = pformat(self.defaults).replace("\n", "\n# ")
            f.write(f"\n# Default configuration values at runtime\n# {str_defaults}")

