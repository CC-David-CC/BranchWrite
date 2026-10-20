import unittest
from src.arith import multiply


class ArithmeticTests(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(multiply(4, 3), 12)

    def test_negative(self):
        self.assertEqual(multiply(-2, 5), -10)

    def test_zero(self):
        self.assertEqual(multiply(0, -6), 0)
