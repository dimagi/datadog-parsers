import logging
import unittest
from touchforms.parsers import parser

SIMPLE = 'INFO 2015-11-12 16:39:39,605 xformserver 20514 27 Finished processing action submit-all in 6.99996948242 ms for session 002734587f774dadbccb96e5f4453546 in domain \'aspace\''
SKIPPED = 'INFO 2015-11-12 16:39:39,598 xformplayer 20514 27 [locking] requested lock for session 002734587f774dadbccb96e5f4453546'


class TestTouchformsParser(unittest.TestCase):

    def test_basic_log_parsing(self):
        metric_name, timestamp, request_time, attrs = parser(logging, SIMPLE)

        self.assertEqual(metric_name, 'touchforms.timings')
        self.assertEqual(timestamp, 1447364379.0)
        self.assertEqual(request_time, 6.99996948242 / 1000)
        self.assertEqual(attrs['metric_type'], 'gauge')
        self.assertEqual(attrs['action'], 'submit-all')
        self.assertEqual(attrs['domain'], 'aspace')

    def test_skipped_line(self):
        self.assertIsNone(parser(logging, SKIPPED))
