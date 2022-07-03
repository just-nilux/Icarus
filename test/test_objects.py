import unittest
from src.Ikarus.objects import *


class test_order_from_dict(unittest.TestCase):
    def test_limit(self):
        order_data = {'price': 0.2906, 'amount': 4749.5664, 'quantity': 16344.0, 'fee': 0.0, 'fee_rate': 0.0, 'orderId': 1652629743339, 'expire': 1559001600000}
        limit_from_dict = order_from_dict(order_data)
        limit_original = Limit(price=0.2906, amount=4749.5664, quantity=16344.0, 
            fee=0.0, fee_rate=0.0, orderId=1652629743339, expire=1559001600000)
        self.assertEqual(limit_from_dict, limit_original)

    def test_market(self):
        order_data = {'price': 0.2906, 'amount': 4749.5664, 'quantity': 16344.0, 'fee': 0.0, 'fee_rate': 0.0, 'orderId': 1652629743339}
        market_from_dict = order_from_dict(order_data)
        market_original = Market(price=0.2906, amount=4749.5664, quantity=16344.0, fee=0.0, fee_rate=0.0, orderId=1652629743339)
        self.assertEqual(market_from_dict, market_original)

    def test_oco(self):
        pass

    def setUp(self):
        print(self.id())
    
    def tearDown(self):
        #print(self._testMethodName)
        pass


class test_trade_from_dict(unittest.TestCase):
    def test_limit(self):
        data = {'_id': "ObjectId('628120f012791ee7ba')", 'decision_time': 1557705600000, 'strategy': 'ObjectStrategy', 'pair': 'XRPUSDT', 'status': 'open_enter', 'enter': {'price': 0.2906, 'amount': 4749.5664, 'quantity': 16344.0, 'fee': 0.0, 'orderId': 1652629743339, 'expire': 1559001600000}, 'exit': {'price': 0.3372, 'amount': 5511.510271497884, 'quantity': 16344.929630776644, 'fee': 0.0, 'orderId': None, 'expire': 1559001600000}, 'result': None, 'command': 'None', 'order_stash': []}
        trade_dict = trade_from_dict(data)
        trade_original = Trade(1557705600000, 'ObjectStrategy', 'XRPUSDT', EState.OPEN_ENTER, 
            Limit(0.2906, 4749.5664, 16344.0, 0.0 ,0.0, 1652629743339, 1559001600000),
            Limit(0.3372, 5511.510271497884, 16344.929630776644, 0.0, 0.0, None, 1559001600000),
            None, ECommand.NONE, [], _id="ObjectId('628120f012791ee7ba')")
        self.assertEqual(trade_dict, trade_original)

    def setUp(self):
        print(self.id())
    
    def tearDown(self):
        #print(self._testMethodName)
        pass

class test_trade_to_dict(unittest.TestCase):
    def test_id_does_not_exit(self):
        trade = Trade(123, "strategy", "pair")
        trade_dict= trade_to_dict(trade)
        self.assertFalse('_id' in trade_dict)

    def test_id_exit(self):
        trade = Trade(123, "strategy", "pair", _id="stringid")
        trade_dict = trade_to_dict(trade)
        self.assertTrue('_id' in trade_dict)


    def setUp(self):
        print(self.id())
    
    def tearDown(self):
        #print(self._testMethodName)
        pass

class test_fee_calculation(unittest.TestCase):
    def test_buy(self):
        pass

    def test_sell(self):
        pass

    def setUp(self):
        print(self.id())
    
    def tearDown(self):
        #print(self._testMethodName)
        pass

if __name__ == '__main__':
    unittest.main(verbosity=2)