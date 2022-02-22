from __future__ import annotations
from collections import defaultdict
from typing import Optional
import os
import pickle

import numpy as np
import rapidjson
try:
    import torch
    _has_torch = True
except:
    _has_torch = False


# The special serializations that DataStorage supports.
# datatype: tuple consisting of save function (API is save(file, data)), load function (API is load(file_obj)) and extension
# Can be extended by user if necessary
SERIALIZATIONS = {
    np.ndarray: (np.save, np.load, "npy"),
}
if _has_torch:
    SERIALIZATIONS[torch.Tensor] = lambda f, d: torch.save(d, f), torch.load, "pt"

class DataStorage:
    """ The DataStorage class is an augmentation of the dataclass that incluces save and load functionality.

    Currently works specifically with:
    - Numpy arrays (numpy.ndarray)
    - Torch tensors (torch.Tensor)
    - Any json serializable type - that is, it should be savable by json.dump
    All other data structures are pickled.

    DataStorage classes must inherit from DataStorage and be annotated with `@dataclass`.
    It is further possible to give arguments to the class definition:
    - `json_name`: Name of the saved json file
    - `indent`:    How many spaces to use for indenting in the json file

    Usage example:
    ```py
    @dataclass
    class ResultData(DataStorage, json_name="game.json", indent=4):
        shots: int
        goalscorers: list
        dists: np.ndarray

    rdata = ResultData(shots=1, goalscorers=["Max Fenger"], dists=np.ones(22)*10)
    rdata.save("max")
    # Now shots and goalscorers are saved in <pwd>/max/game.json and dists in <pwd>/max/dists.npy

    # Then to load
    rdata = ResultData.load("max")
    print(rdata.goalscorers)  # ["Max Fenger"]
    ``` """

    _pickle_ext = "pkl"

    def __init_subclass__(cls, *, json_name="data.json", indent: Optional[int]=None):
        cls._json_name  = json_name
        cls._indent     = indent

    def __init__(self, *args, **kwargs):
        """ This method is overwritten class is decorated with @dataclass.
        Therefore, if this method is called, it is an error. """
        raise TypeError("DataStorage class %s must be decorated with @dataclass" % self.__class__.__name__)

    def save(self, loc: str) -> list[str]:
        """ Saves all the fields of the instatiated data classes as either json,
        pickle or designated serialization function.
        :param str loc: Path to directory in which to save data. """

        os.makedirs(loc, exist_ok=True)

        # Split data by whether it should be saved using a known function or using pickle or json
        func_serialize = defaultdict(dict)
        to_pickle, to_json = dict(), dict()
        for key, data in self.__dict__.items():
            for datatype in SERIALIZATIONS:
                if isinstance(data, datatype):
                    func_serialize[datatype][key] = data
                    break
            else:
                try:
                    # Test whether the data is json serializable by dumping it to string.
                    rapidjson.dumps({key: data})
                    to_json[key] = data
                except TypeError:
                    to_pickle[key] = data

        # Save data
        paths = list()
        if to_json:
            paths.append(os.path.join(loc, self._json_name))
            with open(paths[-1], "w", encoding="utf-8") as f:
                # Save json. This does not guarantee writing to disk, so flushing
                # and synchronization is also done to increase chance of writing
                dump = rapidjson.dumps(to_json, indent=self._indent)
                f.write(dump)
                f.flush()
                os.fsync(f.fileno())
        for key, data in to_pickle.items():
            paths.append(os.path.join(loc, f"{key}.{self._pickle_ext}"))
            with open(paths[-1], "wb") as f:
                pickle.dump(data, f)
        for seri, datas in func_serialize.items():
            save, _, ext = SERIALIZATIONS[seri]
            for key, data in datas.items():
                paths.append(os.path.join(loc, f"{key}.{ext}"))
                save(paths[-1], data)

        return paths

    @classmethod
    def load(cls, loc: str):
        """
        Instantiates the DataStorage-inherited class by loading all files saved by `save` of that same class.
        :param str loc: Path to directory from which to load data
        :return: An instance of this class with the content of the files
        """

        fields = dict()
        # List of fields non-loadable using the SERIALIZATIONS functions
        generals = list()

        for field_name in cls.__dict__["__dataclass_fields__"]:
            for _, load, ext in SERIALIZATIONS.values():
                datapath = os.path.join(loc, f"{field_name}.{ext}")
                if os.path.exists(datapath):
                    fields[field_name] = load(datapath)
                    break
            else:
                generals.append(field_name)

        # Check if the field was saved with pickle
        any_json = False
        for key in generals:
            pfile = os.path.join(loc, f"{key}.{cls._pickle_ext}")
            if os.path.isfile(pfile):
                with open(pfile, "rb") as f:
                    fields[key] = pickle.load(f)
            else:
                any_json = True

        if any_json:
            with open(os.path.join(loc, cls._json_name), encoding="utf-8") as f:
                fields.update(rapidjson.load(f))

        return cls(**fields)
