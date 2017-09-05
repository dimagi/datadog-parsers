import logging
import unittest
from nginx.timings import parse_nginx_timings, parse_nginx_apdex, parse_nginx_counter, _get_url_group, _sanitize_url
from nose_parameterized import parameterized

logging.basicConfig(level=logging.DEBUG)

SIMPLE = '[28/Oct/2015:15:18:14 +0000] - GET /a/uth-rhd/api/case/attachment/a26f2e21-5f24-48b6-b283-200a21f79bb6/VH016899R9_000839_20150922T034026.MP4 HTTP/1.1 401 0.242'
TOLERATING = '[28/Oct/2015:15:18:14 +0000] - GET /a/uth-rhd HTTP/1.1 401 3.2'
UNSATISFIED = '[28/Oct/2015:15:18:14 +0000] - GET /a/uth-rhd HTTP/1.1 401 12.2'
BORKED = 'Borked'
SKIPPED = '[28/Oct/2015:15:18:14 +0000] - GET /static/myawesomejsfile.js HTTP/1.1 200 0.242'
ID_NORMALIZE = '/a/ben/modules-1/forms-2/form_data/a3ds3/uuid:abc123/'
FORMPLAYER = '[04/Sep/2016:21:31:41 +0000] - POST /formplayer/navigate_menu HTTP/1.1 200 19.330'
HOME = '[01/Sep/2017:20:14:43 +0000] - GET /home/ HTTP/1.1 200 18.067'
CACHE = '[01/Sep/2017:20:14:43 +0000] HIT GET /a/icds-cas/apps/download/01d133d7c6264247bf0155f7c5e1af03/modules-11/forms-6.xml?profile=c708a9f737d147bfa57781dd46935502 HTTP/1.1 200 18.067'


class TestNginxTimingsParser(unittest.TestCase):

    def test_basic_log_parsing(self):
        metric_name, timestamp, request_time, attrs = parse_nginx_timings(logging, SIMPLE)

        self.assertEqual(metric_name, 'nginx.timings')
        self.assertEqual(timestamp, 1446038294.0)
        self.assertEqual(request_time, 0.242)
        self.assertEqual(attrs['metric_type'], 'gauge')
        self.assertEqual(attrs['url'], 'not_stored')
        self.assertEqual(attrs['status_code'], '401')
        self.assertEqual(attrs['http_method'], 'GET')
        self.assertEqual(attrs['domain'], 'uth-rhd')

    def test_borked_log_line(self):
        self.assertIsNone(parse_nginx_timings(logging, BORKED))

    def test_skipped_line(self):
        self.assertIsNone(parse_nginx_timings(logging, SKIPPED))

    def test_id_normalization(self):
        url = _sanitize_url(ID_NORMALIZE)

        self.assertEqual(url, '/a/*/modules-*/forms-*/form_data/*/uuid:*/')

    def test_home_counter(self):
        metric_name, timestamp, one, attrs = parse_nginx_counter(logging, HOME)
        self.assertEqual(metric_name, 'nginx.requests')
        self.assertEqual(one, 1)
        self.assertEqual(attrs['http_method'], 'GET')
        self.assertEqual(attrs['url_group'], '/home/')

    def test_home_timings(self):
        metric_name, timestamp, request_time, attrs = parse_nginx_timings(logging, HOME)
        self.assertEqual(metric_name, 'nginx.timings')
        self.assertEqual(request_time, 18.067)
        self.assertEqual(attrs['http_method'], 'GET')
        self.assertEqual(attrs['url'], '/home/')


    def test_apdex_parser_satisfied(self):
        metric_name, timestamp, apdex_score, attrs = parse_nginx_apdex(logging, SIMPLE)
        self.assertEqual(apdex_score, 1)

    def test_apdex_parser_tolerating(self):
        metric_name, timestamp, apdex_score, attrs = parse_nginx_apdex(logging, TOLERATING)
        self.assertEqual(apdex_score, 0.5)

    def test_apdex_parser_unsatisfied(self):
        metric_name, timestamp, apdex_score, attrs = parse_nginx_apdex(logging, UNSATISFIED)
        self.assertEqual(apdex_score, 0)

    def test_nginx_counter(self):
        metric_name, timestamp, count, attrs = parse_nginx_apdex(logging, SIMPLE)
        self.assertEqual(count, 1)
        self.assertEqual(attrs['domain'], 'uth-rhd')

    def test_parse_nginx_counter(self):
        metric_name, timestamp, count, attrs = parse_nginx_counter(logging, SIMPLE)

        self.assertEqual(metric_name, 'nginx.requests')
        self.assertEqual(timestamp, 1446038294.0)
        self.assertEqual(count, 1)
        self.assertEqual(attrs['metric_type'], 'counter')
        self.assertEqual(attrs['url_group'], 'api')
        self.assertEqual(attrs['status_code'], '401')
        self.assertEqual(attrs['http_method'], 'GET')
        self.assertEqual(attrs['domain'], 'uth-rhd')

    @parameterized.expand([
        ('/', 'other'),
        ('/a/*/api', 'api'),
        ('/a/domain', 'other'),
        ('/1/2/3/4', 'other'),
        ('/a/*/cloudcare', 'cloudcare'),
    ])
    def test_get_url_group(self, url, expected):
        group = _get_url_group(url)
        self.assertEqual(expected, group)

    def test_nginx_formplayer(self):
        self.assertIsNotNone(parse_nginx_timings(logging, FORMPLAYER))

    def test_cache(self):
        metric_name, timestamp, count, attrs = parse_nginx_counter(logging, CACHE)
        self.assertEqual(metric_name, 'nginx.requests')
        self.assertEqual(timestamp, 1504289683.0)
        self.assertEqual(count, 1)
        self.assertEqual(attrs['metric_type'], 'counter')
        self.assertEqual(attrs['url_group'], 'apps')
        self.assertEqual(attrs['status_code'], '200')
        self.assertEqual(attrs['http_method'], 'GET')
        self.assertEqual(attrs['domain'], 'icds-cas')
        self.assertEqual(attrs['cache_status'], 'HIT')
