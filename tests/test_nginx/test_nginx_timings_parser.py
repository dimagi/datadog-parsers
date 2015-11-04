import logging
import unittest
from nginx.timings import parse_nginx_timings, parse_nginx_apdex

logging.basicConfig(level=logging.DEBUG)

SIMPLE = '[28/Oct/2015:15:18:14 +0000] GET /a/uth-rhd/api/case/attachment/a26f2e21-5f24-48b6-b283-200a21f79bb6/VH016899R9_000839_20150922T034026.MP4 HTTP/1.1 401 0.242'
TOLERATING = '[28/Oct/2015:15:18:14 +0000] GET /a/uth-rhd HTTP/1.1 401 3.2'
UNSATISFIED = '[28/Oct/2015:15:18:14 +0000] GET /a/uth-rhd HTTP/1.1 401 12.2'
BORKED = 'Borked'
SKIPPED = '[28/Oct/2015:15:18:14 +0000] GET /static/myawesomejsfile.js HTTP/1.1 200 0.242'
ID_NORMALIZE = '[28/Oct/2015:15:18:14 +0000] GET /a/ben/modules-1/forms-2/form_data/a3ds3/uuid:abc123/ HTTP/1.1 200 0.242'


class TestNginxTimingsParser(unittest.TestCase):

    def test_basic_log_parsing(self):
        metric_name, timestamp, request_time, attrs = parse_nginx_timings(logging, SIMPLE)

        self.assertEqual(metric_name, 'nginx.timings')
        self.assertEqual(timestamp, 1446059894.0)
        self.assertEqual(request_time, 0.242)
        self.assertEqual(attrs['metric_type'], 'gauge')
        self.assertEqual(attrs['url'], '/a/*/api/case/attachment/*/VH016899R9_000839_20150922T034026.MP4')
        self.assertEqual(attrs['status_code'], '401')
        self.assertEqual(attrs['http_method'], 'GET')

    def test_borked_log_line(self):
        self.assertIsNone(parse_nginx_timings(logging, BORKED))

    def test_skipped_line(self):
        self.assertIsNone(parse_nginx_timings(logging, SKIPPED))

    def test_id_normalization(self):
        metric_name, timestamp, request_time, attrs = parse_nginx_timings(logging, ID_NORMALIZE)

        self.assertEqual(attrs['url'], '/a/*/modules-*/forms-*/form_data/*/uuid:*/')

    def test_apdex_parser_satisfied(self):
        metric_name, timestamp, apdex_score, attrs = parse_nginx_apdex(logging, SIMPLE)
        self.assertEqual(apdex_score, 1)

    def test_apdex_parser_tolerating(self):
        metric_name, timestamp, apdex_score, attrs = parse_nginx_apdex(logging, TOLERATING)
        self.assertEqual(apdex_score, 0.5)

    def test_apdex_parser_unsatisfied(self):
        metric_name, timestamp, apdex_score, attrs = parse_nginx_apdex(logging, UNSATISFIED)
        self.assertEqual(apdex_score, 0)
