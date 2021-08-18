# Parser

## Classes

```py
class Parser:
    location: Optional[str]
    def __init__(
        self,
        options: Iterable[AbstractArgument],
        description: Optional[str] = None,
        multiple_jobs = False,
        clear_folders = True
    ):
        ...
    def parse(self) -> JobDescription | list[JobDescription]:
        ...
    def document(self) -> str:
        ...

class AbstractArgument(ABC):
    name: str
    abbrevation: Optional[str]
    help: Optional[str]

    def __hash__(self) -> int:
        return hash(self.name)

class Argument(ArgumentDescription):
    def __init__(
        name: str,
        *,
        abbrevation: Optional[str] = None,
        type: type | Callable[str, Any] = str,
        help: Optional[str],
        **kwargs,
    ):
        ...

class Option(ArgumentDescription):
    default: Any
    def __init__(
        name: str,
        *,
        default: Any,
        abbrevation: Optional[str] = None,
        type: type | Callable[str, Any] = str,
        help: Optional[str],
        **kwargs,
    ):
        ...

class Flag(ArgumentDescription):
    default: bool
    def __init__(
        name: str,
        *,
        abbrevation: Optional[str] = None,
        help: Optional[str],
        **kwargs,
    ):
        self.default = False
        ...

class JobDescription(Namespace):
    name: str
    location: str
    def todict(self) -> dict[str, Any]:
        return self.__dict__.copy()
    @property
    def explicit_args(self) -> set[str]:
        ...
    def __getitem__(self, argname: str) -> Any:
        ...
```

## Methods

```py
# Constructor
# `options`: Iterable of arguments. `ArgumentDescription` is a custom class describing arguments, including name, optional default value, etc.
# `description`: Description of the program.
# `multiple_jobs`: Whether or not it is possible to start multiple jobs. If `True`, all every job folder are subfolders within the given location. Use config files to control parameters of multiple jobs.
# `clear_folders`: If `True`, all job folders are emptied when Parser.parse is called
# `show_defaults`: Removed, behaviour is now the same as when it was set to `True`
# `name`: Removed, see section "Behaviour under different circumstances"
parser = Parser(
    options: Iterable[ArgumentDescription],
    description: Optional[str] = None,
    multiple_jobs = False,
    clear_folders = True
)

# Method for parsing given arguments and config file
# If `multiple_jobs` is `True`, a list of experiments is returned
# If not, only a single experiment is returned
experiments = parser.parse()

# Document settings to top folder
# Filename is "runconfig-<name>.ini"
documentation_path = parser.document()
```

## Behaviour under different circumstances

Reserved argument names: `location`, `-c/--config`, `-n/--name`

### `multiple_jobs` and config

- `name` for each job is set by the config file section headers, which are declared using the  `[HEADERNAME]` syntax in the `.ini` format
- Setting `name` from command line raises `CLIError`
- The path to each job is `parser.location/name`

### `multiple_jobs` and no config

- If `name` is set from command line, a single job will be located at `parser.location/name`
- If `name` is not set, it will default to a timestamp including microseconds

### `not multiple_jobs` and config

- Only a single section is allowed in the config file
- If multiple are given, `ConfigError` is raised
- `name` must be given as a section name in the config file, but can be overwritten from the command line
- `name` has no effect

### `not multiple_jobs` and no config

- `name` can be set explicitly from the command line and defaults to a timestamp including microseconds
- `name` has no effect
