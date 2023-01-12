import unittest
from unittest.mock import Mock
from src.Ikarus import resource_allocator
from src.Ikarus.objects import *

class test_StrategyAllocator(unittest.TestCase):

    def test_default(self):

        distribution_config = {
            "initial_capital": 10000,
            "distribution_config": {"FixedLimitTarget":0.25, "FixedOCOTarget":0.75},
            "max_capital_use":1, 
            "stop_capital":None
        }
        discrete_allocator = resource_allocator.DiscreteStrategyAllocator(
            **distribution_config
        )
        allocation = discrete_allocator.allocate(None, [])
        self.assertEqual(allocation, {"FixedLimitTarget":2500, "FixedOCOTarget":7500})

    def test_max_capital_use(self):

        distribution_config = {
            "initial_capital": 10000,
            "distribution_config": {"FixedLimitTarget":0.25, "FixedOCOTarget":0.75},
            "max_capital_use":0.95, 
            "stop_capital":None
        }
        discrete_allocator = resource_allocator.DiscreteStrategyAllocator(
            **distribution_config
        )
        allocation = discrete_allocator.allocate(None, [])
        self.assertEqual(allocation, {"FixedLimitTarget":2375, "FixedOCOTarget":7125})

    def test_stop_capital(self):

        distribution_config = {
            "initial_capital": 1000,
            "distribution_config": {"FixedLimitTarget":0.25, "FixedOCOTarget":0.75},
            "max_capital_use":1, 
            "stop_capital":1000
        }
        discrete_allocator = resource_allocator.DiscreteStrategyAllocator(
            **distribution_config
        )
        allocation = discrete_allocator.allocate(None, [])
        self.assertEqual(allocation, {"FixedLimitTarget":0, "FixedOCOTarget":0})

    def test_trade_with_positive_profit(self):
        distribution_config = {
            "initial_capital": 1000,
            "distribution_config": {"FixedLimitTarget":0.25, "FixedOCOTarget":0.75},
            "max_capital_use":0.95, 
            "stop_capital":None
        }
        discrete_allocator = resource_allocator.DiscreteStrategyAllocator(
            **distribution_config
        )

        allocation = discrete_allocator.allocate(None, [])
        self.assertEqual(allocation, {"FixedLimitTarget":237.5, "FixedOCOTarget":712.5})

        trade = Trade(123, "FixedLimitTarget", "pair")
        trade.status = EState.CLOSED
        trade.result = TradeResult(profit=+100)
        live_trades = [trade]
        allocation = discrete_allocator.allocate(None, live_trades)
        self.assertEqual(allocation, {"FixedLimitTarget":332.5, "FixedOCOTarget":712.5})

    def test_trade_with_negative_profit(self):
        distribution_config = {
            "initial_capital": 1000,
            "distribution_config": {"FixedLimitTarget":0.25, "FixedOCOTarget":0.75},
            "max_capital_use":0.95, 
            "stop_capital":None
        }
        discrete_allocator = resource_allocator.DiscreteStrategyAllocator(
            **distribution_config
        )

        allocation = discrete_allocator.allocate(None, [])
        self.assertEqual(allocation, {"FixedLimitTarget":237.5, "FixedOCOTarget":712.5})

        trade = Trade(123, "FixedLimitTarget", "pair")
        trade.status = EState.CLOSED
        trade.result = TradeResult(profit=-100)
        live_trades = [trade]
        allocation = discrete_allocator.allocate(None, live_trades)
        self.assertEqual(allocation, {"FixedLimitTarget":142.5, "FixedOCOTarget":712.5})


    def setUp(self):
        print(self.id())
    
    def tearDown(self):
        #print(self._testMethodName)
        pass


class test_DefaultTradeAllocator(unittest.TestCase):

    def test_single_pair(self):

        pairs = ['XRPUSDT']

        allocate_kwargs = {
            'max_live_trade':1,
            'strategy_capital':1000,
            'trade_list':[]
        }
        def_trade_allocator = resource_allocator.DefaultTradeAllocator(pairs)

        allocation = def_trade_allocator.allocate(**allocate_kwargs)
        self.assertEqual(allocation, {"XRPUSDT":1000})


    def test_multi_pair(self):

        pairs = ['XRPUSDT', 'BTCUSDT']

        allocate_kwargs = {
            'max_live_trade':2,
            'strategy_capital':1000,
            'trade_list':[]
        }
        def_trade_allocator = resource_allocator.DefaultTradeAllocator(pairs)

        allocation = def_trade_allocator.allocate(**allocate_kwargs)
        self.assertEqual(allocation, {'XRPUSDT':500, 'BTCUSDT':500})


    def test_pair_number_gt_max_live_trade(self):
        pairs = ['XRPUSDT', 'BTCUSDT']

        allocate_kwargs = {
            'max_live_trade':1,
            'strategy_capital':1000,
            'trade_list':[]
        }
        def_trade_allocator = resource_allocator.DefaultTradeAllocator(pairs)

        allocation = def_trade_allocator.allocate(**allocate_kwargs)
        self.assertEqual(allocation, {'XRPUSDT':1000})


    def test_pair_number_lt_max_live_trade(self):
        pairs = ['XRPUSDT', 'BTCUSDT']

        allocate_kwargs = {
            'max_live_trade':4,
            'strategy_capital':1000,
            'trade_list':[]
        }
        def_trade_allocator = resource_allocator.DefaultTradeAllocator(pairs)

        allocation = def_trade_allocator.allocate(**allocate_kwargs)
        self.assertEqual(allocation, {'XRPUSDT':250, 'BTCUSDT':250})


    def test_zero_strategy_capital(self):
        pairs = ['XRPUSDT', 'BTCUSDT']

        allocate_kwargs = {
            'max_live_trade':4,
            'strategy_capital':0,
            'trade_list':[]
        }
        def_trade_allocator = resource_allocator.DefaultTradeAllocator(pairs)

        allocation = def_trade_allocator.allocate(**allocate_kwargs)
        self.assertEqual(allocation, {})


    def test_strategy_cap_lte_in_trade_cap(self):
        pairs = ['XRPUSDT', 'BTCUSDT']
        trade = Trade(123, "StrategyName", "XRPUSDT")
        trade.set_enter(Limit(5,100))

        allocate_kwargs = {
            'max_live_trade':1,
            'strategy_capital':0,
            'trade_list':[trade]
        }
        def_trade_allocator = resource_allocator.DefaultTradeAllocator(pairs)

        allocation = def_trade_allocator.allocate(**allocate_kwargs)
        self.assertEqual(allocation, {})


    def test_closed_trade(self):
        pairs = ['XRPUSDT']
        trade = Trade(123, "StrategyName", "XRPUSDT")
        trade.status = EState.CLOSED

        allocate_kwargs = {
            'max_live_trade':1,
            'strategy_capital':1000,
            'trade_list':[trade]
        }
        def_trade_allocator = resource_allocator.DefaultTradeAllocator(pairs)

        allocation = def_trade_allocator.allocate(**allocate_kwargs)
        self.assertEqual(allocation, {'XRPUSDT':1000})
        pass


    def test_open_trade(self):
        pairs = ['XRPUSDT', 'BTCUSDT']
        trade = Trade(123, "StrategyName", "XRPUSDT")
        trade.set_enter(Limit(5,100))
        trade.status = EState.WAITING_EXIT

        allocate_kwargs = {
            'max_live_trade':2,
            'strategy_capital':1000,
            'trade_list':[trade]
        }
        def_trade_allocator = resource_allocator.DefaultTradeAllocator(pairs)

        allocation = def_trade_allocator.allocate(**allocate_kwargs)
        self.assertEqual(allocation, {'BTCUSDT':900})
        pass


    def setUp(self):
        print(self.id())
    
    def tearDown(self):
        #print(self._testMethodName)
        pass