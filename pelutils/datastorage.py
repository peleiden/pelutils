from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Type, TypeVar

import rapidjson

_T = TypeVar("_T", bound="DataStorage")

class DataStorage:
    """The DataStorage class is an augmentation of the dataclass that incluces save and load functionality.

    DataStorage classes must inherit from DataStorage and be annotated with `@dataclass`. Data will be saved
    to two files: A json files for json-serializable data and a pickle file for everything else. These files
    are by default named after the class, but it is possible to use a custom name in the save and load methods.
    The files are only created if necessary, so for instance if all data is json-serializable, no pickle file
    will be created.

    Data is in general preserved exactly as-is when saved data is loaded into memory with few exceptions.
    Nnotably, tuples are considered json-serializble, and so will be saved to the json file and will be
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
    """

    def __init__(self, *args, **kwargs):
        """This method is overwritten in any class decorated with @dataclass.

        Therefore, if this method is called, it is an error.
        """  # noqa: D401, D404
        raise TypeError(f"DataStorage class {self.__class__.__name__} must be decorated with @dataclass")

    @classmethod
    def json_name(cls, save_name: str | None = None):
        """Return the name of the json file to where json serializable data will be saved."""
        return (save_name or cls.__name__) + ".json"

    @classmethod
    def pickle_name(cls, save_name: str | None = None):
        """Return the name of the pickle file to where non json serializable data will be saved."""
        return (save_name or cls.__name__) + ".pkl"

    def save(self, loc: str | Path, save_name: str | None = None, *, indent: int | None = 4) -> list[str]:
        """Save all the fields of the instatiated data classes as either json, pickle or designated serialization function.

        Parameters
        ----------
        loc : str | Path
            Directory in which to save data.
        save_name : str | None, optional
            If given, file name (excluding extension) to use for saving, by default None.
        indent : int | None, optional
            Indent used for the json file, by default 4. It is recommended to set to None when large objects are saved to json.

        Returns
        -------
        list[str]
            Produced files containing the data.
        """
        loc = str(loc)
        os.makedirs(loc, exist_ok=True)

        to_json = dict()
        to_pickle = dict()

        for key, data in self.__dict__.items():
            try:
                # Test whether the data is json serializable by dumping it to string.
                rapidjson.dumps({key: data})
                to_json[key] = data
            except TypeError:
                to_pickle[key] = data

        # Save data
        paths = list()
        if to_json:
            paths.append(os.path.join(loc, self.json_name(save_name)))
            with open(paths[-1], "w", encoding="utf-8") as f:
                # Save json. This does not guarantee writing to disk, so flushing
                # and synchronization is also done to increase chance of writing
                dump = rapidjson.dumps(to_json, indent=indent)
                f.write(dump)
                f.flush()
                os.fsync(f.fileno())

        if to_pickle:
            paths.append(os.path.join(loc, self.pickle_name(save_name)))
            with open(paths[-1], "wb") as f:
                pickle.dump(to_pickle, f)
                f.flush()
                os.fsync(f.fileno())

        return paths

    @classmethod
    def load(cls: Type[_T], loc: str | Path, save_name: str | None = None) -> _T:
        """Instantiate the DataStorage-inherited class by loading all files saved by `save` of that same class.

        Parameters
        ----------
        loc : str | Path
            Directory from which to load data.
        save_name : str | None, optional
            If given, file name (excluding extension) to use for loading, by default None. It should match what was given to `save`.

        Returns
        -------
        DataStorage
            An instance of this class with the content of the files.
        """
        loc = str(loc)
        json_file = os.path.join(loc, cls.json_name(save_name))
        pickle_file = os.path.join(loc, cls.pickle_name(save_name))

        fields = dict()

        if os.path.isfile(json_file):
            with open(json_file, encoding="utf-8") as f:
                fields.update(rapidjson.load(f))

        if os.path.isfile(pickle_file):
            with open(pickle_file, "rb") as f:
                fields.update(pickle.load(f))

        if not os.path.isfile(json_file) and not os.path.isfile(pickle_file):
            raise FileNotFoundError(f"Unable to load {cls.__name__}; neither {json_file} nor {pickle_file} found.")

        return cls(**fields)
