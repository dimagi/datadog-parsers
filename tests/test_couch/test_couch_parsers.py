import logging
import unittest
from couch.parsers import parse_couch_logs

logging.basicConfig(level=logging.DEBUG)

SIMPLE = '2015-10-31 18:32:03,963 [:mvp-pampaida] /a/mvp-pampaida/receiver/630916e49084b142c0a5a69c3a52b9b3/ PUT None d3abf611f2acdc7b4c32f7ebf4982a88 0:00:00.191515'
BORKED = 'Borked'


class TestCouchLogParser(unittest.TestCase):

    def test_basic_log_parsing(self):
        metric_name, timestamp, request_time, attrs = parse_couch_logs(logging, SIMPLE)

        self.assertEqual(metric_name, 'couch.timings')
        self.assertEqual(timestamp, 1446330723.0)
        self.assertEqual(request_time, 0.191515)
        self.assertEqual(attrs['metric_type'], 'gauge')
        self.assertEqual(attrs['url'], '/a/*/receiver/*/')
        self.assertEqual(attrs['domain'], 'mvp-pampaida')
        self.assertEqual(attrs['couch_url'], 'd3abf611f2acdc7b4c32f7ebf4982a88')
        self.assertEqual(attrs['status_code'], 'None')
        self.assertEqual(attrs['http_method'], 'PUT')

    def test_borked_log_line(self):
        self.assertIsNone(parse_couch_logs(logging, BORKED))
