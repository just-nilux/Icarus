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
from .safe_operators import safe_divide, safe_multiply, safe_substract, safe_sum

def trade_list_to_json(trade_list):
    return [json.dumps(trade, cls=EnhancedJSONEncoder) for trade in trade_list]


def trade_to_dict(trade):
    trade_dict = asdict(trade)
    if trade_dict['_id'] == None: 
        del trade_dict['_id']
    return trade_dict


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
    CLOSED_STOP_LOSS = 'closed_stop_loss' # 'oco_stoploss'
    # Previously:
    #   lto_list[i]['result']['cause'] = STAT_CLOSED
    #   lto_list[i]['result']['exit']['type'] = 'oco_stoploss'


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
    '''
    NOTE: Initially the known parameters might be:
        quantity: Market Sell
        price ( + amount ): Limit Buy/Sell
           
        In all of the enter cases there is an allocated amount. The quantity is evaluated based on the price.
        Even in the case of Market Buy: we evaluate the quantity by dividing the amount to the last closed price
    
    Method of Order creation:
        Market(amount=allocated_amount, price=last_closed_price) # Market Buy
            - quantity evaluated
            - quantity used in order
        Market(quantity=enter_quantity price=last_closed_price) # Market Sell
            - amount evaluated
            - quantity used in order
        Limit(amount=allocated_amount, price=target_price)  # Limit Buy
            - quantity is evaluated
            - quantity and price used in order
        Limit(quantity=enter_quantity, price=target_price)  # Limit Sell
            - amount is evaluated
            - quantity and price used in order
        OCO()  # OCO Buy
            - 
            - 
        OCO()  # OCO Sell
            - 
            - 

    Fee Calculation:
        https://www.binance.com/en/support/faq/e85d6e703b874674840122196b89780a
        Trading fees are always charged in the asset you receive. For example:
            if you buy ETH/USDT, the fee is paid in ETH. 
            If you sell ETH/USDT, the fee is paid in USDT.

        For example:
            You place an order to buy 10 ETH for 3,452.55 USDT each:
            Trading fee = 10 ETH * 0.1% = 0.01 ETH
            Or you place an order to sell 10 ETH for 3,452.55 USDT each:
            Trading fee = (10 ETH * 3,452.55 USDT) * 0.1% = 34.5255 USDT

        Afterwards the fee is substracted from the amount to get the "net" result. As a result:
            You will receive 10 - 0.01 = 9.99 ETH
            You will reveive 3452.55 - 34.5255 = 3418.0245 USDT

        TLDR:
            From the Order object point of view the fee can be evaluated by the quantity or the amount
            If the pair ETH/USDT is used and we buy ETH using USDT, then the fee is evaluated and charged in ETH
            If the pair ETH/USDT is used and we sell ETH using USDT (buy USDT using ETH), then the fee is evaluated and charged in USDT

    '''
    #       
    # NOTE: If the change of an field affects others,
    #       then it is performed via a setter.

    price: float = None
    amount: float = None
    # NOTE: The amount causes some kind of confusion around here. The point is:
    #   It is either evaluated by the price and quantity
    #   It is used in the evaluation of the quantity (by the help of price)
    # When the amount is provided it is provided as the NEXT NEXT REFACTORING
    quantity: float = None
    fee_rate: float = 0.0
    fee: float = 0.0
    orderId: int = None

    def __post_init__(self):

        if self.quantity == None and self.amount == None and self.price == None:
            pass
        elif self.quantity == None:
            # NOTE: If the quantity is unknown it is probably the buy side.
            self.quantity = safe_divide(self.amount, self.price)
            self.fee = safe_multiply(self.quantity, self.fee_rate)
            #self.quantity = safe_substract(self.quantity, self.fee)
            # NOTE: The quantity should not be affacted by the future fees but in the below, the amount can be affacted
            #   Since it has no effect on the order.

        elif self.amount == None:
            # NOTE: If the amount is unknown (and the quantity is known) it is probably the sell side.
            self.amount = safe_multiply(self.price, self.quantity)
            self.fee = safe_multiply(self.amount, self.fee_rate)
            #self.amount = safe_substract(self.amount, self.fee)
            # NOTE: Fee is not substracted from the amount because it is not done on the above (considering quantity).

        else:
            # TODO: Error on initialization
            pass

    def set_price(self, price, use_amount_for_fee_calc=True) -> None:
        self.price = price
        self.amount = safe_multiply(self.price, self.quantity)

        if use_amount_for_fee_calc:
            self.fee = safe_multiply(self.amount, self.fee_rate)
        else:
            self.fee = safe_multiply(self.quantity, self.fee_rate)

    def set_quantity(self, quantity, use_amount_for_fee_calc=True) -> None:
        self.quantity = quantity
        self.amount = safe_multiply(self.price, self.quantity)

        if use_amount_for_fee_calc:
            self.fee = safe_multiply(self.amount, self.fee_rate)
        else:
            self.fee = safe_multiply(self.quantity, self.fee_rate)


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
    order_stash: list = field(default_factory=list)
    _id: str = None

    def set_enter(self,enter_order):
        self.enter=enter_order

    def set_exit(self,exit_order):
        self.exit=exit_order

    def reset_command(self):
        self.command=ECommand.NONE

    def stash_exit(self): # Stash the exit order when it will about to be updated
        self.order_stash.append(copy.deepcopy(self.exit))

    def set_result_enter(self, time, quantity=None, price=None, fee=None, fee_rate=None):

        if not quantity: quantity = self.enter.quantity
        if not price: price = self.enter.price
        if not fee: fee = self.result.enter.fee

        self.status = EState.WAITING_EXIT
        self.result.enter.type = type(self.enter).__name__.lower()
        self.result.enter.time = time
        self.result.enter.quantity = quantity
        self.result.enter.set_price(price)

        if fee:
            self.result.enter.fee = fee
        elif fee_rate:
            self.result.enter.fee = round(safe_multiply(self.result.enter.amount,fee_rate),8)

        

    def set_result_exit(self, time, quantity=None, price=None, fee=None, fee_rate=None, status=EState.CLOSED, cause=ECause.CLOSED):

        if not quantity: quantity = self.exit.quantity
        if not price: price = self.exit.price

        self.status = status
        self.result.cause = cause
        self.result.exit.type = type(self.exit).__name__.lower()
        self.result.exit.time = time
        self.result.exit.quantity = quantity
        self.result.exit.set_price(price)

        if fee:
            self.result.exit.fee = fee
        elif fee_rate:
            self.result.exit.fee = round(safe_multiply(self.result.exit.amount,fee_rate),8)

        self.result.profit = self.result.exit.amount \
            - self.result.enter.amount \
            - self.result.enter.fee \
            - self.result.exit.fee

        self.result.live_time = self.result.exit.time - self.result.enter.time


def is_trade_phase_enter(trade: Trade) -> bool:

    if trade.status in [EState.OPEN_ENTER, EState.ENTER_EXP, EState.WAITING_ENTER]:
        return True

    elif trade.status in [EState.OPEN_EXIT, EState.EXIT_EXP, EState.WAITING_EXIT]:
        return False

    else:
        raise Exception(f'LTO {trade.id} status {trade.status}')


def order_from_dict(order_data):
    order = Order()
    if 'type' in order_data.keys():
        order = Result()
    elif 'expire' not in order_data.keys():
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


def result_from_dict(data):
        if not isinstance(data, dict):
            return None

        trade_result = TradeResult()
        if 'cause' in  data: trade_result.cause=data['cause']
        if 'profit' in  data: trade_result.profit=data['profit']
        if 'live_time' in  data: trade_result.live_time=data['live_time']
        if data['enter'] != None:
            trade_result.enter = order_from_dict(data['enter'])
            trade_result.enter.time = data['enter']['time']
            trade_result.enter.type = data['enter']['type']
        else:
            trade_result.enter = Result()
        
        if data['exit'] != None:
            trade_result.exit = order_from_dict(data['exit'])
            trade_result.exit.time = data['exit']['time']
            trade_result.exit.type = data['exit']['type']
        else:
            trade_result.exit = Result()

        return trade_result


def trade_from_dict(data):
    return Trade(data['decision_time'], data['strategy'], data['pair'], EState(data['status']),
        order_from_dict(data['enter']), order_from_dict(data['exit']), result_from_dict(data['result']),
        ECommand(data['command']), [order_from_dict(order) for order in data['order_stash']], _id=data['_id'])
    

if __name__ == "__main__":
    order = Order()
    trade = Trade(123, "strategy", "pair",enter=order)
    print(trade_to_dict(trade))
    pass