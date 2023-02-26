import unittest
from unittest.mock import Mock
from src.Ikarus import resource_allocator
from src.Ikarus.objects import *

class test_StrategyAllocator(unittest.TestCase):

    def test_default(self):

        distribution_config = {
            "initial_capital": 10000,
            "distribution_config": {"FixedLimitTarget":0.25, "FixedOCOTarget":0.75},
            "capital_coeff":1, 
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
            "capital_coeff":0.95, 
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
            "capital_coeff":1, 
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
            "capital_coeff":0.95, 
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
            "capital_coeff":0.95, 
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
