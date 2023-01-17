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



class EOrderType(str, Enum):
    MARKET = 'Market'
    LIMIT = 'Limit'
    OCO = 'OCO'


class ECommand(str, Enum):
    NONE = None
    CANCEL = 'cancel'                   # Cancel order
    UPDATE = 'update'                   # Update order (CANCEL + EXEC_X)
    EXEC_EXIT = 'execute_exit'          # Execute exit order   
    EXEC_ENTER = 'execute_enter'        # Execute enter order


'''
ECause is used to explain the cause for a Trade to become EState.CLOSED
'''
class ECause(str, Enum):
    NONE = None
    ENTER_EXP = 'enter_expire'
    MAN_CHANGE = 'manual_change'
    MARKET = 'market'
    LIMIT = 'limit' 
    STOP_LIMIT = 'stop_limit' 


class EState(str, Enum):
    WAITING_ENTER = 'waiting_enter'
    OPEN_ENTER = 'open_enter'
    ENTER_EXP = 'enter_expire'
    WAITING_EXIT = 'waiting_exit'
    OPEN_EXIT = 'open_exit'
    EXIT_EXP = 'exit_expire'
    CLOSED = 'closed'


class EObserverType(str, Enum):
    BALANCE = 'balance'
    QUOTE_ASSET = 'quote_asset'


@dataclass
class ReportMeta:
    title: str = ''
    filename: str = ''


@dataclass
class Report:
    meta: ReportMeta
    data: None


@dataclass
class Observer:
    type: EObserverType
    ts: bson.Int64
    data: None

    def to_dict(self):
        return asdict(self)

@dataclass
class Order:
    '''
    NOTE: Orders has nothing to do with the fees, they contain the quantity, the price and the amount 
        before the fees applied

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

    '''
    #       
    # NOTE: If the change of an field affects others,
    #       then it is performed via a setter.

    price: float = None
    amount: float = None
    quantity: float = None
    orderId: int = None

    def __post_init__(self):

        if self.quantity == None and self.amount == None and self.price == None:
            pass

        elif self.quantity == None:
            self.quantity = safe_divide(self.amount, self.price)

        elif self.amount == None:
            self.amount = safe_multiply(self.price, self.quantity)

        else:
            # TODO: Error on initialization
            pass

    def set_price(self, price) -> None:
        self.price = price
        self.amount = safe_multiply(self.price, self.quantity)


    def set_quantity(self, quantity) -> None:
        self.quantity = quantity
        self.amount = safe_multiply(self.price, self.quantity)


@dataclass
class Market(Order):
    pass


@dataclass
class Limit(Order):
    expire: bson.Int64 = None


@dataclass
class OCO(Order):
    # NOTE: When Selling, stop_price > stop_limit_price
    expire: bson.Int64 = None
    stop_price: float = None            # Price to trigger stop limit order
    stop_limit_price: float = None      # Price of stop limit order
    stop_limit_orderId: int = None


@dataclass
class Result(Order):
    type: string = '' # type(trade.enter).__name__
    time: bson.Int64 = None
    fee: float = 0.0


@dataclass
class TradeResult():
    cause: ECause = ECause.NONE
    enter: Result = None
    exit: Result = None
    profit: float = 0.0
    live_time: int = 0


'''
Fee Calculation is handled in the creation of the Result() objects:
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


    NOTE: Binance do not keep the net profit. It keeps the "Total" which corresponds to result.enter/exit.amount + result.enter/exit.fee
    Date(UTC)	        Market	Type	Price	Amount	Total	Fee	Fee Coin
    2022-05-09 23:44:48	BTCUSDT	BUY	30150	0.01662	501.093	0.00125301	BNB

'''

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

    def reset_exit(self):
        self.exit=None

    def set_command(self, command):
        self.command=command

    def reset_command(self):
        self.command=ECommand.NONE

    def stash_exit(self): # Stash the exit order when it will about to be updated
        self.order_stash.append(copy.deepcopy(self.exit))

    def set_result_enter(self, time, quantity=None, price=None, fee_rate=0):
        '''
            Result modules (enter or exit) contains 
            - The paid fee for the order execution
            - The total value(amount) of the received asset in the quote currency after the fee
        '''
        self.result.enter = Result()
        if quantity: 
            self.result.enter.quantity = quantity
        else:
            self.result.enter.quantity = self.enter.quantity

        if price: 
            self.result.enter.price = price
        else:
            self.result.enter.price = self.enter.price

        self.status = EState.WAITING_EXIT
        self.result.enter.type = type(self.enter).__name__.lower()
        self.result.enter.time = time

        # Evaluate the fee on the quantity and the amount after fee
        self.result.enter.fee = safe_multiply(self.result.enter.quantity, fee_rate)
        self.result.enter.quantity = safe_substract(self.result.enter.quantity, self.result.enter.fee)
        self.result.enter.amount = safe_multiply(self.result.enter.quantity, self.result.enter.price)
        

    def set_result_exit(self, time, quantity=None, price=None, fee_rate=None, status=EState.CLOSED, cause=ECause.NONE):
        self.result.exit = Result()
        if quantity: 
            self.result.exit.quantity = quantity
        else:
            self.result.exit.quantity = self.exit.quantity # Exit qty is already gets the result.enter.quantity

        if price: 
            self.result.exit.price = price
        else:
            self.result.exit.price = self.exit.price

        self.status = status
        self.result.cause = cause
        self.result.exit.type = type(self.exit).__name__.lower()
        self.result.exit.time = time

        # Evaluate the fee on the quantity and the amount after fee
        self.result.exit.amount = safe_multiply(self.result.exit.price, self.result.exit.quantity)
        self.result.exit.fee = safe_multiply(self.result.exit.amount, fee_rate)
        self.result.exit.amount = safe_substract(self.result.exit.amount, self.result.exit.fee)

        # self.result.profit indicates the effect of this trade to the capital
        enter_cost = safe_sum(self.result.enter.amount, safe_multiply(self.result.enter.fee, self.result.enter.price)) # trade.enter.amount
        self.result.profit = safe_substract(self.result.exit.amount, enter_cost)
        self.result.live_time = self.result.exit.time - self.decision_time


def is_trade_phase_enter(trade: Trade) -> bool:

    if trade.status in [EState.OPEN_ENTER, EState.ENTER_EXP, EState.WAITING_ENTER]:
        return True

    elif trade.status in [EState.OPEN_EXIT, EState.EXIT_EXP, EState.WAITING_EXIT]:
        return False

    else:
        raise Exception(f'LTO {trade.id} status {trade.status}')


def order_from_dict(order_data):
    if not order_data:
        return None

    order = Order()
    if 'type' in order_data.keys():
        order = Result()
        order.fee = order_data['fee']
    elif 'expire' not in order_data.keys():
        order = Market()
    else:
        if 'stop_price' not in order_data.keys():
            order = Limit()
        else:
            order = OCO()
            order.stop_price = order_data['stop_price']
            order.stop_limit_price = order_data['stop_limit_price']
            order.stop_limit_orderId = order_data['stop_limit_orderId']
        order.expire = order_data['expire']
    order.price = order_data['price']
    order.amount = order_data['amount']
    order.quantity = order_data['quantity']
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
        
        if data['exit'] != None:
            trade_result.exit = order_from_dict(data['exit'])
            trade_result.exit.time = data['exit']['time']
            trade_result.exit.type = data['exit']['type']

        return trade_result


def trade_from_dict(data):
    return Trade(data['decision_time'], data['strategy'], data['pair'], EState(data['status']),
        order_from_dict(data['enter']), order_from_dict(data['exit']), result_from_dict(data['result']),
        ECommand(data['command']), [order_from_dict(order) for order in data['order_stash']], _id=data['_id'])
    

if __name__ == "__main__":
    price=0.2906
    price_to_set=0.25
    quantity=4749.5664
    amount=1187.3916
    fee_rate = 0.001

    order_buy = Limit(price=price, amount=amount, fee_rate=fee_rate, orderId=1652629743339, expire=1559001600000)
    order_buy.set_price(price=price_to_set, use_amount_for_fee_calc=False)
    pass