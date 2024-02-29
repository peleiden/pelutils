from __future__ import annotations

import os
import pickle
from typing import Optional

import rapidjson


class DataStorage:
    """ The DataStorage class is an augmentation of the dataclass that incluces save and load functionality.
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
    ``` """

    def __init__(self, *args, **kwargs):
        """ This method is overwritten class is decorated with @dataclass.
        Therefore, if this method is called, it is an error. """
        raise TypeError("DataStorage class %s must be decorated with @dataclass" % self.__class__.__name__)

    @classmethod
    def json_name(cls, save_name: Optional[str] = None):
        return (save_name or cls.__name__) + ".json"

    @classmethod
    def pickle_name(cls, save_name: Optional[str] = None):
        return (save_name or cls.__name__) + ".pkl"

    def save(self, loc: str, save_name: Optional[str] = None, *, indent: Optional[int] = 4) -> list[str]:
        """ Saves all the fields of the instatiated data classes as either json,
        pickle or designated serialization function. Use save_name to overwrite
        default behavior of using the class name for file names. E.g. in a DataStorage
        class named Results, the defualt saved file names would be Results.json and
        Results.pkl. Settings save_name="gollum" would result in file names
        Returns list of saved files.
        :param str loc: Path to directory in which to save data. """

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
    def load(cls, loc: str, save_name: Optional[str] = None):
        """
        Instantiates the DataStorage-inherited class by loading all files saved by `save` of that same class.
        Use save_name to load json and pickle files that have been saved using explicitly set save_name.
        :param str loc: Path to directory from which to load data
        :return: An instance of this class with the content of the files
        """

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
            raise FileNotFoundError("Unable to find saved %s files in directory %s with name %s" % (
                cls.__name__, loc, (save_name or cls.__name__)
            ))

        return cls(**fields)
