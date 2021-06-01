'''
Observers are the configurable read-only units. They simply collect data at the end of each execution cycle
'''
import logging
import pandas as pd
from multipledispatch import dispatch
from json import JSONEncoder


class ObjectEncoder(JSONEncoder):
        def default(self, o):
            return o.get()


class GenericObject():

    templates = dict()
    
    templates['trade'] = {
        "status": "",
        "enter": {
            "isProcessed": "",
            "limitBuy": "",
            "expire": "",
            "enterTime": ""
        },
        "exit": {
            "oco": {
                "isProcessed": "",
                "limitSell": "",
                "stopPrice": "",
                "stopLimit": "",
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
            self._obj =GenericObject.templates[template_name]

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
        pass

    def dump(self):
        pass

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
