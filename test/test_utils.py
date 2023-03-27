import unittest
from icarus.utils import *

class test_minute_to_time_scale(unittest.TestCase):
    def test_exact_minute(self):
        self.assertEqual(minute_to_time_scale(1440), '1d')

    def test_scaler(self):
        self.assertEqual(minute_to_time_scale(720), '12h')

    def test_none(self):
        self.assertEqual(minute_to_time_scale(90), None)

    def test_oco(self):
        pass

    def setUp(self):
        print(self.id())
    
    def tearDown(self):
        #print(self._testMethodName)
        pass
