from __future__ import annotations
import os
import json

import numpy as np


class DataStorage:
    """
    The DataStorage class is an augmentation of the dataclass that incluces a standard way to save and load data.

    Currently works with:
        * Numpy arrays (numpy.ndarray)
        * Any json serializable type - that is, it should be savable by json.dump

    The field `subfolder` is the directory in which to place all saved date
    `json_name` chooses the name of the single json data file including all jsonifiable data

    Usage example
    ```
    @dataclass
    class ResultData(DataStorage):
        shots: int
        goalscorers: list
        dists: np.ndarray

        subfolder = 'gamedata'
        json_name = 'game.json'

    rdata = ResultData(shots=1, goalscorers=["Max Fenger"], dists=np.ones(22)*10)
    rdata.save()
    # Now shots and goalscorers are saved in <pwd>/gamedata/game.json and dists in <pwd>/gamedata/dists.npy

    # In seperate script
    rdata = ResultData.load()
    print(rdata.goalscorers)  # ["Max Fenger"]
    ```
    """

    subfolder = ''
    json_name = 'data.json'

    def save(self, loc: str = '') -> list[str]:
        """Saves all the fields of the instatiated data classes in npy's or json in <`loc`>/<`self.subfolder`>

        :param str loc: Save location to place the subfolder in
        :return: list (with length = # of saved files) of full save paths
        """
        loc = self._get_loc(loc)
        if loc:
            os.makedirs(loc, exist_ok=True)

        # Split data by whether it should be saved .json and to .npy
        to_json, to_npy = dict(), dict()
        for key, data in self.__dict__.items():
            if isinstance(data, np.ndarray):
                to_npy.update({key: data})
            else:
                to_json.update({key: data})

        # Save data
        paths = [os.path.join(loc, self.json_name)]
        if to_json:
            with open(paths[0], "w", encoding="utf-8") as f:
                json.dump(to_json, f, indent=4)
        for key, arr in to_npy.items():
            paths.append(os.path.join(loc, f"{key}.npy"))
            np.save(paths[-1], arr)
        return paths

    @classmethod
    def load(cls, loc: str = ''):
        """
        Instantiates the DataStorage-inherited class by loading all files saved by `save` of that same class.
        :param str loc: Save location used
        :return: An instance of this class with the content of the files
        """
        loc = cls._get_loc(loc)
        any_json = False
        npys, non_numpy = dict(), dict()

        # Get .npy filenames and load these
        for key, field in cls.__dict__["__dataclass_fields__"].items():
            if field.type == np.ndarray:
                npys[key] = np.load(os.path.join(loc, f"{key}.npy"))
            else: any_json = True

        # Load .json if any non ndarray fields exist
        if any_json:
            with open(os.path.join(loc, cls.json_name), encoding="utf-8") as f:
                non_numpy = json.load(f)

        return cls(**non_numpy, **npys)

    @classmethod
    def _get_loc(cls, loc: str):
        return os.path.join(loc, cls.subfolder) if cls.subfolder else loc
