import unittest
from src.arith import add


class ArithmeticTests(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(add(4, 3), 7)

    def test_negative(self):
        self.assertEqual(add(-2, 5), 3)

    def test_zero(self):
        self.assertEqual(add(0, -6), -6)
