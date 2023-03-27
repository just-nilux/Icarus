import unittest
from unittest.mock import Mock
from icarus import position_sizing
from icarus.objects import *


class test_evaluate_size(unittest.TestCase):

    def test_single_pair(self):
        allocate_kwargs = {
            'pairs': ['XRPUSDT'],
            'max_live_trade':1,
            'strategy_capital':1000,
            'trade_list':[]
        }

        allocation = position_sizing.evaluate_size(**allocate_kwargs)
        self.assertEqual(allocation, {"XRPUSDT":1000})


    def test_multi_pair(self):
        allocate_kwargs = {
            'pairs': ['XRPUSDT', 'BTCUSDT'],
            'max_live_trade':2,
            'strategy_capital':1000,
            'trade_list':[]
        }

        allocation = position_sizing.evaluate_size(**allocate_kwargs)
        self.assertEqual(allocation, {'XRPUSDT':500, 'BTCUSDT':500})


    def test_pair_number_gt_max_live_trade(self):
        allocate_kwargs = {
            'pairs': ['XRPUSDT', 'BTCUSDT'],
            'max_live_trade':1,
            'strategy_capital':1000,
            'trade_list':[]
        }

        allocation = position_sizing.evaluate_size(**allocate_kwargs)
        self.assertTrue(allocation == {'XRPUSDT':1000} or allocation == {'BTCUSDT':1000})



    def test_pair_number_lt_max_live_trade(self):
        allocate_kwargs = {
            'pairs': ['XRPUSDT', 'BTCUSDT'],
            'max_live_trade':4,
            'strategy_capital':1000,
            'trade_list':[]
        }

        allocation = position_sizing.evaluate_size(**allocate_kwargs)
        self.assertEqual(allocation, {'XRPUSDT':250, 'BTCUSDT':250})


    def test_zero_strategy_capital(self):
        allocate_kwargs = {
            'pairs': ['XRPUSDT', 'BTCUSDT'],
            'max_live_trade':4,
            'strategy_capital':0,
            'trade_list':[]
        }

        allocation = position_sizing.evaluate_size(**allocate_kwargs)
        self.assertEqual(allocation, {})


    def test_strategy_cap_lte_in_trade_cap(self):
        trade = Trade(123, "StrategyName", "XRPUSDT")
        trade.set_enter(Limit(5,100))

        allocate_kwargs = {
            'pairs': ['XRPUSDT', 'BTCUSDT'],
            'max_live_trade':1,
            'strategy_capital':0,
            'trade_list':[trade]
        }

        allocation = position_sizing.evaluate_size(**allocate_kwargs)
        self.assertEqual(allocation, {})


    def test_closed_trade(self):
        trade = Trade(123, "StrategyName", "XRPUSDT")
        trade.status = EState.CLOSED

        allocate_kwargs = {
            'pairs': ['XRPUSDT', 'BTCUSDT'],
            'max_live_trade':1,
            'strategy_capital':1000,
            'trade_list':[trade]
        }

        allocation = position_sizing.evaluate_size(**allocate_kwargs)
        self.assertTrue(allocation == {'XRPUSDT':1000} or allocation == {'BTCUSDT':1000})
        pass


    def test_open_trade(self):
        trade = Trade(123, "StrategyName", "XRPUSDT")
        trade.set_enter(Limit(5,100))
        trade.status = EState.WAITING_EXIT

        allocate_kwargs = {
            'pairs': ['XRPUSDT', 'BTCUSDT'],
            'max_live_trade':2,
            'strategy_capital':1000,
            'trade_list':[trade]
        }

        allocation = position_sizing.evaluate_size(**allocate_kwargs)
        self.assertEqual(allocation, {'BTCUSDT':900})
        pass


    def setUp(self):
        print(self.id())
    
    def tearDown(self):
        #print(self._testMethodName)
        pass


class test_evaluate_stop_loss(unittest.TestCase):

    def test_fee_rate_gt_0_and_used(self):
        fee_rate = 0.001 

        trade = Trade(123, "StrategyName", "XRPUSDT")
        trade.set_enter(Limit(price=5,amount=100,quantity=20))
        trade.result = TradeResult()
        trade.set_result_enter(123456, fee_rate=fee_rate)
        allocate_kwargs = {
            'strategy_capital': 200,
            'max_loss_coeff':0.02,
            'trade':trade,
            'fee_rate': fee_rate
        }

        stop_loss_price = position_sizing.evaluate_stop_loss(**allocate_kwargs)
        trade.set_result_exit(123456,
            cause=ECause.STOP_LIMIT,
            price=stop_loss_price,
            quantity=trade.result.enter.quantity,
            fee_rate=fee_rate)

        price_change_ratio = (trade.result.exit.price - trade.result.enter.price) / trade.result.enter.price
        percentage_profit = (trade.result.exit.amount - trade.enter.amount)/ trade.enter.amount

        description = "percentage_profit should be <= price_change_ratio due to negative affect of fees"
        self.assertLessEqual(percentage_profit, price_change_ratio, description)

        description = "lowest_profit value should not be exceeded downward by the profit of the trade"
        lowest_profit = -allocate_kwargs['max_loss_coeff']*allocate_kwargs['strategy_capital']
        self.assertLess(lowest_profit, trade.result.profit, description)

    def test_fee_rate_gt_0_and_not_used(self):
        fee_rate = 0.001 

        trade = Trade(123, "StrategyName", "XRPUSDT")
        trade.set_enter(Limit(price=5,amount=100,quantity=20))
        trade.result = TradeResult()
        trade.set_result_enter(123456, fee_rate=fee_rate)
        allocate_kwargs = {
            'strategy_capital': 200,
            'max_loss_coeff':0.02,
            'trade':trade,
            'fee_rate': None
        }

        stop_loss_price = position_sizing.evaluate_stop_loss(**allocate_kwargs)
        trade.set_result_exit(123456,
            cause=ECause.STOP_LIMIT,
            price=stop_loss_price,
            quantity=trade.result.enter.quantity,
            fee_rate=fee_rate)

        price_change_ratio = (trade.result.exit.price - trade.result.enter.price) / trade.result.enter.price
        percentage_profit = (trade.result.exit.amount - trade.enter.amount)/ trade.enter.amount

        description = "percentage_profit should be <= price_change_ratio due to negative affect of fees"
        self.assertLessEqual(percentage_profit, price_change_ratio, description)

        description = "lowest_profit value should be exceeded downward by the profit of the trade due to existing fees that are not used in calculation"
        lowest_profit = -allocate_kwargs['max_loss_coeff']*allocate_kwargs['strategy_capital']
        self.assertGreater(lowest_profit, trade.result.profit, description)

    def test_fee_rate_eq_0_and_used(self):
        fee_rate = 0

        trade = Trade(123, "StrategyName", "XRPUSDT")
        trade.set_enter(Limit(price=5,amount=100,quantity=20))
        trade.result = TradeResult()
        trade.set_result_enter(123456, fee_rate=fee_rate)
        allocate_kwargs = {
            'strategy_capital': 200,
            'max_loss_coeff':0.02,
            'trade':trade,
            'fee_rate': fee_rate
        }

        stop_loss_price = position_sizing.evaluate_stop_loss(**allocate_kwargs)
        trade.set_result_exit(123456,
            cause=ECause.STOP_LIMIT,
            price=stop_loss_price,
            quantity=trade.result.enter.quantity,
            fee_rate=fee_rate)
        price_change_ratio = safe_divide(safe_substract(trade.result.exit.price, trade.result.enter.price), trade.result.enter.price)
        percentage_profit = safe_divide(safe_substract(trade.result.exit.amount, trade.enter.amount), trade.enter.amount)

        description = "percentage_profit should be == price_change_ratio since the fee is 0"
        self.assertEqual(percentage_profit, price_change_ratio, description)

        description = "lowest_profit value should be equal to the profit of the trade since the fee is 0"
        lowest_profit = -safe_multiply(allocate_kwargs['max_loss_coeff'],allocate_kwargs['strategy_capital'])
        self.assertEqual(lowest_profit, trade.result.profit, description)

    def test_fee_rate_eq_0_and_not_used(self):
        fee_rate = 0

        trade = Trade(123, "StrategyName", "XRPUSDT")
        trade.set_enter(Limit(price=5,amount=100,quantity=20))
        trade.result = TradeResult()
        trade.set_result_enter(123456, fee_rate=fee_rate)
        allocate_kwargs = {
            'strategy_capital': 200,
            'max_loss_coeff':0.02,
            'trade':trade,
            'fee_rate': None
        }

        stop_loss_price = position_sizing.evaluate_stop_loss(**allocate_kwargs)
        trade.set_result_exit(123456,
            cause=ECause.STOP_LIMIT,
            price=stop_loss_price,
            quantity=trade.result.enter.quantity,
            fee_rate=fee_rate)
        price_change_ratio = safe_divide(safe_substract(trade.result.exit.price, trade.result.enter.price), trade.result.enter.price)
        percentage_profit = safe_divide(safe_substract(trade.result.exit.amount, trade.enter.amount), trade.enter.amount)
        
        description = "percentage_profit should be == price_change_ratio since the fee is 0"
        self.assertEqual(percentage_profit, price_change_ratio, description)

        description = "lowest_profit value should be equal to the profit of the trade since the fee is 0 no matter if it is considered in stop_loss_price calculation"
        lowest_profit = -safe_multiply(allocate_kwargs['max_loss_coeff'],allocate_kwargs['strategy_capital'])
        self.assertEqual(lowest_profit, trade.result.profit, description)


    def setUp(self):
        print(self.id())
    
    def tearDown(self):
        #print(self._testMethodName)
        pass

