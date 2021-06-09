from __future__ import annotations
from collections import defaultdict
import inspect
import json
import pickle
import os

import numpy as np
try:
    import torch
    _has_torch = True
except:
    _has_torch = False

# The special serializations that DataStorage supports.
# datatype: tuple consisting of save function (API is save(file, data)), load function (API is load(file_obj)) and extension
SERIALIZATIONS = {
    np.ndarray: (np.save, np.load, "npy"),
}
if _has_torch:
    SERIALIZATIONS[torch.Tensor] = (lambda f, d: torch.save(d, f), torch.load, "pt")

class DataStorage:
    """
    The DataStorage class is an augmentation of the dataclass that incluces a standard way to save and load data.

    Currently works specifically with:
        * Numpy arrays (numpy.ndarray)
        * Torch tensors (torch.Tensor)
        * Any json serializable type - that is, it should be savable by json.dump
    * All other data structures are pickled

    `json_name` chooses the name of the single json data file including all jsonifiable data
    `ignore_missing` sets fields not present in stored data to None instead of throwing an error
    This can be useful for backwards compatibility when loading data saved by older DataStorage instances

    Usage example
    ```
    @dataclass  # dataclass decoration is important for this to work
    class ResultData(DataStorage):
        shots: int
        goalscorers: list
        dists: np.ndarray

        json_name = 'game.json'
        ignore_missing = False

    rdata = ResultData(shots=1, goalscorers=["Max Fenger"], dists=np.ones(22)*10)
    rdata.save()
    # Now shots and goalscorers are saved in <pwd>/gamedata/game.json and dists in <pwd>/gamedata/dists.npy

    # In seperate script
    rdata = ResultData.load()
    print(rdata.goalscorers)  # ["Max Fenger"]
    ```
    """

    json_name      = "data.json"
    pickle_ext     = "p"
    ignore_missing = False

    def save(self, loc: str) -> list[str]:
        """
        Saves all the fields of the instatiated data classes as either json, pickle or designated serialization function
        :param str loc: Path to directory in which to save data
        """

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
                    json.dumps({key: data})
                    to_json[key] = data
                except TypeError:
                    to_pickle[key] = data

        # Save data
        paths = list()
        if to_json:
            paths.append(os.path.join(loc, self.json_name))
            with open(paths[-1], "w", encoding="utf-8") as f:
                json.dump(to_json, f)
        for key, data in to_pickle.items():
            paths.append(os.path.join(loc, f"{key}.{self.pickle_ext}"))
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
            pfile = os.path.join(loc, f"{key}.{cls.pickle_ext}")
            if os.path.isfile(pfile):
                with open(pfile, "rb") as f:
                    fields[key] = pickle.load(f)
            else:
                any_json = True

        if any_json:
            with open(os.path.join(loc, cls.json_name), encoding="utf-8") as f:
                fields.update(json.load(f))

        # Set missing parameters to None
        if cls.ignore_missing:
            for parameter in inspect.signature(cls.__init__).parameters:
                if parameter != "self":
                    fields[parameter] = fields.get(parameter)

        return cls(**fields)
