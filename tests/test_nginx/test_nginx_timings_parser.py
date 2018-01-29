import logging
import unittest
import datetime
from nginx.timings import parse_nginx_timings, parse_nginx_apdex, parse_nginx_counter, _get_url_group, _sanitize_url
from nose_parameterized import parameterized
from parsing_utils import UnixTimestampTestMixin

logging.basicConfig(level=logging.DEBUG)

SIMPLE = '[28/Oct/2015:15:18:14 +0000] GET /a/uth-rhd/api/case/attachment/a26f2e21-5f24-48b6-b283-200a21f79bb6/VH016899R9_000839_20150922T034026.MP4 HTTP/1.1 401 0.242'
PRICING = '[28/Oct/2015:15:18:14 +0000] GET /pricing/ HTTP/1.1 401 0.242'
ICDS_DASHBOARD = '[28/Oct/2015:15:18:14 +0000] GET /a/anydomain/icds_dashboard/anything HTTP/1.1 401 0.242'
TOLERATING = '[28/Oct/2015:15:18:14 +0000] GET /a/uth-rhd HTTP/1.1 401 3.2'
UNSATISFIED = '[28/Oct/2015:15:18:14 +0000] GET /a/uth-rhd HTTP/1.1 401 12.2'
BORKED = 'Borked'
SKIPPED = '[28/Oct/2015:15:18:14 +0000] GET /static/myawesomejsfile.js HTTP/1.1 200 0.242'
ID_NORMALIZE = '/a/ben/modules-1/forms-2/form_data/a3ds3/uuid:abc123/'
FORMPLAYER = '[04/Sep/2016:21:31:41 +0000] POST /formplayer/navigate_menu HTTP/1.1 200 19.330'
HOME = '[01/Sep/2017:20:14:43 +0000] GET /home/ HTTP/1.1 200 18.067'
CACHE = '[01/Sep/2017:20:14:43 +0000] HIT GET /a/icds-cas/apps/download/01d133d7c6264247bf0155f7c5e1af03/modules-11/forms-6.xml?profile=c708a9f737d147bfa57781dd46935502 HTTP/1.1 200 18.067'
CACHE_BLANK = '[13/Sep/2017:12:34:14 +0000] - POST /a/hki-nepal-suaahara-2/receiver/secure/393a1d06a6e8422092c089082ffb5c01/ HTTP/1.1 401 0.955"'
URL_SPACES = '[01/Sep/2017:07:19:09 +0000] GET /a/infomovel-ccs/apps/download/81630cfff87fdc77b8fd4a7427703bdc/media_profile.ccpr?latest=true&profile=None loira fabiao bila HTTP/1.1 400 0.001'


class TestNginxTimingsParser(UnixTimestampTestMixin, unittest.TestCase):

    @parameterized.expand([
        ('not_stored', SIMPLE),
        ('icds_dashboard', ICDS_DASHBOARD),
        ('/pricing/', PRICING),
    ])
    def test_basic_log_parsing(self, url_group, line):
        metric_name, timestamp, request_time, attrs = parse_nginx_timings(logging, line)

        self.assertEqual(metric_name, 'nginx.timings')
        self.assert_timestamp_equal(timestamp, datetime.datetime(2015, 10, 28, 15, 18, 14), 1446045494)
        self.assertEqual(request_time, 0.242)
        self.assertEqual(attrs['metric_type'], 'gauge')
        self.assertEqual(attrs['url_group'], url_group)
        self.assertEqual(attrs['status_code'], '401')
        self.assertEqual(attrs['http_method'], 'GET')

    def test_borked_log_line(self):
        self.assertIsNone(parse_nginx_timings(logging, BORKED))

    def test_skipped_line(self):
        self.assertIsNone(parse_nginx_timings(logging, SKIPPED))

    def test_id_normalization(self):
        url = _sanitize_url(None, ID_NORMALIZE)

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
        self.assertEqual(attrs['url_group'], '/home/')


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

    def test_parse_nginx_counter(self):
        metric_name, timestamp, count, attrs = parse_nginx_counter(logging, SIMPLE)

        self.assertEqual(metric_name, 'nginx.requests')
        self.assert_timestamp_equal(timestamp, datetime.datetime(2015, 10, 28, 15, 18, 14), 1446045494)
        self.assertEqual(count, 1)
        self.assertEqual(attrs['metric_type'], 'counter')
        self.assertEqual(attrs['url_group'], 'api')
        self.assertEqual(attrs['status_code'], '401')
        self.assertEqual(attrs['http_method'], 'GET')

    @parameterized.expand([
        ('/', 'other'),
        ('/a/*/api', 'api'),
        ('/a/domain', 'other'),
        ('/1/2/3/4', 'other'),
        ('/a/*/cloudcare', 'cloudcare'),
        ('/pricing/', '/pricing/'),
        ('/home/', '/home/'),
    ])
    def test_get_url_group(self, url, expected):
        group = _get_url_group(url)
        self.assertEqual(expected, group)

    def test_nginx_formplayer(self):
        self.assertIsNotNone(parse_nginx_timings(logging, FORMPLAYER))

    def test_cache(self):
        metric_name, timestamp, count, attrs = parse_nginx_counter(logging, CACHE)
        self.assertEqual(metric_name, 'nginx.requests')
        self.assert_timestamp_equal(timestamp, datetime.datetime(2017, 9, 1, 20, 14, 43), 1504296883)
        self.assertEqual(count, 1)
        self.assertEqual(attrs['metric_type'], 'counter')
        self.assertEqual(attrs['url_group'], 'apps')
        self.assertEqual(attrs['status_code'], '200')
        self.assertEqual(attrs['http_method'], 'GET')
        self.assertEqual(attrs['cache_status'], 'HIT')

        metric_name, timestamp, count, attrs = parse_nginx_counter(logging, CACHE_BLANK)
        self.assertEqual(attrs['cache_status'], '-')


    def test_url_with_spaces(self):
        metric_name, timestamp, count, attrs = parse_nginx_timings(logging, URL_SPACES)
        self.assertEqual(metric_name, 'nginx.timings')
        self.assert_timestamp_equal(timestamp, datetime.datetime(2017, 9, 1, 7, 19, 9), 1504250349)
        self.assertEqual(count, 0.001)
        self.assertEqual(attrs['status_code'], '400')
        self.assertEqual(attrs['http_method'], 'GET')
