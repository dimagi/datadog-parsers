import unittest
import datetime
from parsing_utils import get_unix_timestamp


class TestParsingUtils(unittest.TestCase):
    def test_get_unix_timestamp(self):
        self.assertEqual(get_unix_timestamp(datetime.datetime(2015, 10, 28, 15, 18, 14)), 1446045494)

    def test_get_unix_timestamp_on_epoch(self):
        self.assertEqual(get_unix_timestamp(datetime.datetime(1970, 1, 1)), 0)
