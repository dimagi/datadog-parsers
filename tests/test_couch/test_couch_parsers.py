import logging
import unittest
from couch.parsers import parse_couch_logs

logging.basicConfig(level=logging.DEBUG)

SIMPLE = '2015-10-31 18:32:03,963 [:mvp-pampaida] /a/mvp-pampaida/receiver/630916e49084b142c0a5a69c3a52b9b3/ PUT None d3abf611f2acdc7b4c32f7ebf4982a88 0:00:00.191515'
WITH_CONTENT_LENGTH = '2017-05-04 12:20:18,957 [:icds-cas] /a/icds-cas/apps/download/768932dcb27f35c63cdbb830c202c727/modules-0/forms-0.xml HEAD 200 258 /commcarehq__apps/ 0:00:00.007104'
WITH_DATABASE_NAME = '2017-05-04 12:20:21,416 [:icds-cas] /a/icds-cas/receiver/secure/768932dcb27f35c63cdbb830c202c727/ commcarehq__users GET 200 None _design/users/_view/by_username 0:00:00.004401'
BORKED = 'Borked'


class TestCouchLogParser(unittest.TestCase):

    def _test_log_parsing(self, line, timestamp, request_time, expected_attrs):
        metric_name, timestamp, request_time, attrs = parse_couch_logs(logging, line)

        expected_attrs.update({
            'metric_type': 'gauge',

        })

        self.assertEqual(metric_name, 'couch.timings')
        self.assertEqual(timestamp, timestamp)
        self.assertEqual(request_time, request_time)
        self.assertEqual(expected_attrs, attrs)

    def test_simple_log_parsing(self):
        self._test_log_parsing(SIMPLE, 1446309123.0, 0.191515, {
            'domain': 'mvp-pampaida',
            'url': '/a/*/receiver/*/',
            'couch_url': '*',
            'status_code': 'None',
            'http_method': 'PUT',
            'database': ''
        })

    def test_log_parsing_content_length(self):
        self._test_log_parsing(WITH_CONTENT_LENGTH, 1446309123.0, 0.191515, {
            'domain': 'icds-cas',
            'url': '/a/*/apps/download/*/modules-*/forms-*.xml',
            'couch_url': '/commcarehq__apps/',
            'status_code': '200',
            'http_method': 'HEAD',
            'database': ''
        })

    def test_log_parsing_database_name(self):
        self._test_log_parsing(WITH_DATABASE_NAME, 1446309123.0, 0.191515, {
            'domain': 'icds-cas',
            'url': '/a/*/receiver/secure/*/',
            'couch_url': '_design/users/_view/by_username',
            'status_code': '200',
            'http_method': 'GET',
            'database': 'commcarehq__users'
        })

    def test_borked_log_line(self):
        self.assertIsNone(parse_couch_logs(logging, BORKED))
