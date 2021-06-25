'''
Observers are the configurable read-only units. They simply collect data at the end of each execution cycle
'''
import logging
import pandas as pd
from multipledispatch import dispatch
from json import JSONEncoder
import collections.abc
import numpy as np
import copy

class ObjectEncoder(JSONEncoder):
    def default(self, o):
        if type(o) == np.int64:
            return int(o)
        return o.get()


class GenericObject():

    templates = dict()
    
    templates['trade'] = {
        "status": "",
        "tradeid": "",
        "enter": {
            "limitBuy": {
                "price": "",
                "amount": ""
            },
            "expire": "",
            "enterTime": ""
        },
        "exit": {
            "oco": {
                "limitSellPrice": "",
                "stopPrice": "",
                "stopLimitPrice": "",
                "amount": ""
            },
            "limitSell": {
                "price":"",
                "amount": ""
            },
            "expire": "",
            "exitTime": ""
        },
        "result": {
            "canceled": {
                "time": "",
                "reason": ""
            },
            "closed": {
                "reason": "",
                "buyAmount": "",
                "uyPrice": "",
                "sellAmount": "",
                "sellPrice": "",
                "profit": "",
                "perc": "",
                "totalTime": ""
            }
        }
    }

    templates['observation'] = {
        "equity": 0
    }

    templates['analysis'] = {}
    
    templates['data'] = {}


    def __init__(self, template_name=None):
        if template_name is None:
            self._obj = dict()
        else:
            self._obj = copy.deepcopy(GenericObject.templates[template_name])

    @dispatch(dict)
    def load(self, item):     
        self._data_obj = item
        pass

    @dispatch(str, object)
    def load(self, keyword, item):
        self._obj[keyword] = item
        pass

    @dispatch(list, object)
    def load(self, obj_path, item):

        #TODO: Generic solution needs to be added
        # Temporary quick fix
        if len(obj_path) == 2:
            self._obj[obj_path[0]][obj_path[1]] = item
        elif len(obj_path) == 3:
            self._obj[obj_path[0]][obj_path[1]][obj_path[2]] = item
        pass

    def dump(self):
        pass

    @staticmethod
    def nested_update(obj, key, value):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    GenericObject.nested_update(v, key, value)
                elif k == key:
                    obj[k] = value
        elif isinstance(obj, list):
            for item in obj:
                GenericObject.nested_update(item, key, value)
        return obj

    @dispatch()
    def get(self):
        return self._obj

    @dispatch(str)
    def get(self, keyword):
        return self._obj[keyword]

    @dispatch(list)
    def get(self, obj_path):
        current_level = self._obj
        for keyword in obj_path:
            current_level = current_level[keyword]
        return current_level
