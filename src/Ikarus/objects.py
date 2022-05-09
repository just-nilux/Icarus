'''
Observers are the configurable read-only units. They simply collect data at the end of each execution cycle
'''
from dataclasses import dataclass, field
import dataclasses
import logging
import string
import pandas as pd
from multipledispatch import dispatch
from json import JSONEncoder
import json
import collections.abc
import numpy as np
import copy
import bson
from enum import Enum

class ObjectEncoder(JSONEncoder):
    def default(self, o):
        if type(o) == np.int64:
            return int(o)
        return o.get()

class EnhancedJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if dataclasses.is_dataclass(o):
                return dataclasses.asdict(o)
            return super().default(o)




class GenericObject():

    templates = dict()
    
    trade = {
        "strategy": "",
        "status": "",
        "decision_time": "",
        "enter": {
        },
        "exit": {
        },
        "result": {
            "cause": "",
            "enter": {
                "type": "",
                "time": "",
                "price": "",
                "quantity": "",
                "amount": ""
            },
            "exit": {
                "type": "",
                "time": "",
                "price": "",
                "quantity": "",
                "amount": ""
            },
            "profit": 0,
            "liveTime": 0
        },
        "history": [],
        "update_history": []
    }
    # TODO: Adding states to 'history' is currently manual and cumbersome.
    #       It can be automated if an update method is used by the GenericObject class
    templates['observation'] = {
        "equity": 0
    }

    templates['analysis'] = {}
    
    templates['data'] = {}

    market = {
        "quantity": "",
        "amount": ""
    }
    
    oco = {
        "limitPrice": "",
        "stopPrice": "",
        "stopLimitPrice": "",
        "stopLimit_orderId": "",
        "quantity": "",
        "amount": "",
        "expire": "",
        "orderId": "",
        "stopLimit_orderId": ""
    }
    
    limit = {
        "price": "",
        "quantity": "",
        "amount": "",
        "expire": "",
        "orderId": ""
    }

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


class TradeResult(str, Enum):
    NONE = ''
    ENTER_EXP = 'enter_expire'
    MAN_CHANGE = 'manual_change'
    EXIT_EXP = 'exit_expire'
    CLOSED = 'closed'


class TradeState(str, Enum):
    OPEN_ENTER = 'open_enter'
    ENTER_EXP = 'enter_expire'
    WAITING_EXIT = 'waiting_exit'
    OPEN_EXIT = 'open_exit'
    EXIT_EXP = 'exit_expire'
    CLOSED = 'closed'


@dataclass
class Trade():
    decision_time: bson.Int64
    strategy: string
    pair: string
    id: string = ''
    status: TradeState = TradeState.OPEN_ENTER
    enter: dict = field(default_factory=dict)
    exit: dict = field(default_factory=dict)
    history: dict = field(default_factory=dict)
    action: bool = False

    def set_enter(self,enter_order):
        self.enter=enter_order

    def set_exit(self,enter_order):
        self.enter=enter_order


@dataclass
class LimitOrder():
    expire: bson.Int64
    price: float
    amount: float = 0.0
    quantity: float = 0.0
    fee: float = 0.0
    orderId: int = 0
    def __post_init__(self):
        if self.quantity == 0.0 and self.amount != 0.0:
            self.amount / (self.price * (1 + self.fee))
        elif self.quantity != 0.0 and self.amount == 0.0:
            self.amount = float(self.price * self.quantity)
        else:
            # TODO: Error on initialization
            pass


@dataclass
class OCOOrder():
    expire: bson.Int64
    limitPrice: float
    stopPrice: float
    stopLimitPrice: float
    quantity: float
    amount: float
    fee: float = 0.0
    orderId: int = 0
    stopLimit_orderId: int = 0


@dataclass
class MarketOrder():
    quantity: float
    amount: float
    fee: float = 0.0
    orderId: int = 0
    # TODO: Check if price is a member


@dataclass
class TradeResult():
    result: TradeResult = TradeResult.NONE
    enter: dict = field(default_factory=dict)
    exit: dict = field(default_factory=dict)
    profit: float = 0.0
    live_time: int = 0


class Order:
    type: string = '' # type(trade.enter).__name__
    time: bson.Int64 = 0
    price: float = 0.0
    quantity: float = 0.0
    amount: float = 0.0
    fee: float = 0.0


if __name__ == "__main__":
    #limit_order = LimitOrder(0,0,0,0)
    trade = Trade(0,'NewStrategy','BTCUSDT')
    trade.set_enter(LimitOrder(0,2,quantity=3))
    print(type(trade.enter) == LimitOrder)
    trade_Str = json.dumps(trade, cls=EnhancedJSONEncoder)
    pass