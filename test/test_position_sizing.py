import unittest
from unittest.mock import Mock
from src.Ikarus import position_sizing
from src.Ikarus.objects import *


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
        self.assertEqual(allocation, {'XRPUSDT':1000})


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
        self.assertEqual(allocation, {'XRPUSDT':1000})
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