'''
Observers are the configurable read-only units. They simply collect data at the end of each execution cycle
'''
from dataclasses import dataclass, field, asdict
import dataclasses
import string
from multipledispatch import dispatch
from json import JSONEncoder
import json
import numpy as np
import copy
import bson
from enum import Enum
from .safe_operators import safe_multiply

def trade_list_to_json(trade_list):
    return [json.dumps(trade, cls=EnhancedJSONEncoder) for trade in trade_list]


def trade_list_to_dict(trade_list):
    return [asdict(trade) for trade in trade_list]


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

class EOrderType(str, Enum):
    MARKET = 'Market'
    LIMIT = 'Limit'
    OCO = 'OCO'


class ECommand(str, Enum):
    NONE = None
    CANCEL = 'cancel'                   # Cancel order
    UPDATE = 'update'                   # Update order (CANCEL + EXEC_X)
    MARKET_ENTER = 'market_enter'       # Do market enter
    MARKET_EXIT = 'market_exit'         # Do market exit
    EXEC_EXIT = 'execute_exit'          # Execute exit order   
    EXEC_ENTER = 'execute_enter'        # Execute enter order


class ECause(str, Enum):
    NONE = None
    ENTER_EXP = 'enter_expire'
    MAN_CHANGE = 'manual_change'
    EXIT_EXP = 'exit_expire'
    CLOSED = 'closed'


class EState(str, Enum):
    WAITING_ENTER = 'waiting_enter'
    OPEN_ENTER = 'open_enter'
    ENTER_EXP = 'enter_expire'
    WAITING_EXIT = 'waiting_exit'
    OPEN_EXIT = 'open_exit'
    EXIT_EXP = 'exit_expire'
    CLOSED = 'closed'


@dataclass
class Order:
    # NOTE: If the change of an field affects others,
    #       then it is performed via a setter.
    price: float = 0
    amount: float = None
    quantity: float = None
    fee: float = 0.0                    # Only for having an estimation in amount calculation
    orderId: int = None
    def __post_init__(self):
        if self.quantity == None and self.amount == None:
            pass
        elif self.quantity == None:
            # TODO: Safe operator integration
            self.quantity = self.amount / (self.price * (1 + self.fee))
        elif self.amount == None:
            # TODO: Safe operator integration
            self.amount = float(self.price * self.quantity)
        else:
            # TODO: Error on initialization
            pass

    def set_price(self, price):
        #self.amount = float(self.price * self.quantity)
        self.price = price
        self.amount = safe_multiply(self.price, self.quantity)
        self.fee = safe_multiply(self.amount, self.fee)


@dataclass
class Market(Order):
    pass


@dataclass
class Limit(Order):
    expire: bson.Int64 = None


@dataclass
class OCO(Order):
    expire: bson.Int64 = None
    stopPrice: float = None
    stopLimitPrice: float = None
    stopLimit_orderId: int = None


@dataclass
class Result(Order):
    type: string = '' # type(trade.enter).__name__
    time: bson.Int64 = None


@dataclass
class TradeResult():
    cause: ECause = ECause.NONE
    enter: Result = None
    exit: Result = None
    profit: float = 0.0
    live_time: int = 0


@dataclass
class Trade():
    decision_time: bson.Int64
    strategy: string
    pair: string
    status: EState = EState.WAITING_ENTER
    enter: dict = None
    exit: dict = None
    result: TradeResult = None
    command: ECommand = ECommand.NONE
    update_history: list = field(default_factory=list)

    def set_enter(self,enter_order):
        self.enter=enter_order

    def set_exit(self,exit_order):
        self.exit=exit_order

    def set_command(self,command):
        self.command=command

    def clear_command(self):
        self.command=ECommand.NONE


def order_from_dict(order_data):
    order = Order()
    if 'expire' not in order_data.keys():
        order = Market()
    else:
        if 'stopPrice' not in order_data.keys():
            order = Limit()
        else:
            order = OCO()
            order.stopPrice = order_data['stopPrice']
            order.stopLimitPrice = order_data['stopLimitPrice']
            order.stopLimit_orderId = order_data['stopLimit_orderId']
        order.expire = order_data['expire']
    order.price = order_data['price']
    order.amount = order_data['amount']
    order.quantity = order_data['quantity']
    order.fee = order_data['fee']
    order.orderId = order_data['orderId']
    return order


def trade_from_dict(data):
    return Trade(data['decision_time'], data['strategy'], data['pair'], EState(data['status']),
        order_from_dict(data['enter']), order_from_dict(data['exit']), data['result'],
        ECommand(data['command']), data['update_history'])
    

if __name__ == "__main__":
    pass