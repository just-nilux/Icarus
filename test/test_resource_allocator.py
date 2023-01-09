import unittest
from unittest.mock import Mock
from src.Ikarus import resource_allocator
from src.Ikarus.objects import *

class test_StrategyAllocator(unittest.TestCase):

    def test_default(self):

        distribution_config = {
            "initial_capital": 10000,
            "config": {"FixedLimitTarget":0.25, "FixedOCOTarget":0.75},
            "max_capital_use":None, 
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
            "config": {"FixedLimitTarget":0.25, "FixedOCOTarget":0.75},
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
            "config": {"FixedLimitTarget":0.25, "FixedOCOTarget":0.75},
            "max_capital_use":None, 
            "stop_capital":1000
        }
        discrete_allocator = resource_allocator.DiscreteStrategyAllocator(
            **distribution_config
        )
        allocation = discrete_allocator.allocate(None, [])
        self.assertEqual(allocation, {"FixedLimitTarget":0, "FixedOCOTarget":0})

    def test_trade_with_positive_profit(self):
        trade = Trade(123, "FixedLimitTarget", "pair")
        trade.status = EState.CLOSED
        trade.result = TradeResult(profit=+100)
        live_trades = [trade]

        distribution_config = {
            "initial_capital": 1000,
            "config": {"FixedLimitTarget":0.25, "FixedOCOTarget":0.75},
            "max_capital_use":None, 
            "stop_capital":None
        }
        discrete_allocator = resource_allocator.DiscreteStrategyAllocator(
            **distribution_config
        )

        allocation = discrete_allocator.allocate(None, live_trades)
        self.assertEqual(allocation, {"FixedLimitTarget":350, "FixedOCOTarget":750})

    def test_trade_with_negative_profit(self):
        trade = Trade(123, "FixedLimitTarget", "pair")
        trade.status = EState.CLOSED
        trade.result = TradeResult(profit=-100)
        live_trades = [trade]

        distribution_config = {
            "initial_capital": 1000,
            "config": {"FixedLimitTarget":0.25, "FixedOCOTarget":0.75},
            "max_capital_use":None, 
            "stop_capital":None
        }
        discrete_allocator = resource_allocator.DiscreteStrategyAllocator(
            **distribution_config
        )

        allocation = discrete_allocator.allocate(None, live_trades)
        self.assertEqual(allocation, {"FixedLimitTarget":150, "FixedOCOTarget":750})


    def test_trade_with_negative_profit(self):
        trade = Trade(123, "FixedLimitTarget", "pair")
        trade.status = EState.CLOSED
        trade.result = TradeResult(profit=-100)
        live_trades = [trade]

        distribution_config = {
            "initial_capital": 1000,
            "config": {"FixedLimitTarget":0.25, "FixedOCOTarget":0.75},
            "max_capital_use":None, 
            "stop_capital":None
        }
        discrete_allocator = resource_allocator.DiscreteStrategyAllocator(
            **distribution_config
        )

        allocation = discrete_allocator.allocate(None, live_trades)
        self.assertEqual(allocation, {"FixedLimitTarget":150, "FixedOCOTarget":750})


    def setUp(self):
        print(self.id())
    
    def tearDown(self):
        #print(self._testMethodName)
        pass
