import unittest


class TestCI02FailureGate(unittest.TestCase):
    def test_intentional_failure(self):
        self.fail("CI-02: intentional test failure")
