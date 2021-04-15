import logging
import unittest
import datetime
from couch.parsers import parse_couch_logs
from parsing_utils import UnixTimestampTestMixin

logging.basicConfig(level=logging.DEBUG)

SIMPLE = '2015-10-31 18:32:03,963 [:mvp-pampaida] /a/mvp-pampaida/receiver/630916e49084b142c0a5a69c3a52b9b3/ PUT None d3abf611f2acdc7b4c32f7ebf4982a88 0:00:00.191515'
URL_NO_TASK = '2015-10-31 18:32:03,963 [:mvp-pampaida] /a/mvp-pampaida/receiver/630916e49084b142c0a5a69c3a52b9b3/ - commcarehq PUT 200 None d3abf611f2acdc7b4c32f7ebf4982a88 0:00:00.191515'
NO_URL_NO_TASK = '2015-10-31 18:32:03,963 [:mvp-pampaida] - - commcarehq PUT 200 None d3abf611f2acdc7b4c32f7ebf4982a88 0:00:00.191515'
NO_URL_TASK = '2015-10-31 18:32:03,963 [:mvp-pampaida] - corehq.apps.tasks.build_app commcarehq PUT 200 None d3abf611f2acdc7b4c32f7ebf4982a88 0:00:00.191515'
WITH_CONTENT_LENGTH = '2017-05-04 12:20:18,957 [:icds-cas] /a/icds-cas/apps/download/768932dcb27f35c63cdbb830c202c727/modules-0/forms-0.xml HEAD 200 258 /commcarehq__apps/ 0:00:00.007104'
WITH_DATABASE_NAME = '2017-05-04 12:20:21,416 [:icds-cas] /a/icds-cas/receiver/secure/768932dcb27f35c63cdbb830c202c727/ commcarehq__users GET 200 None _design/users/_view/by_username 0:00:00.004401'
WITH_USERNAME = "2017-05-04 12:20:21,416 [123@my-dom.commcarehq.org:my-dom] /a/my-dom/phone/restore/768932dcb27f35c63cdbb830c202c727/ HEAD 200 260 /commcarehq/ 0:00:00.004076"
WITH_SECONDS = "2017-05-04 12:20:21,416 [123@my-dom.commcarehq.org:my-dom] /a/my-dom/phone/restore/768932dcb27f35c63cdbb830c202c727/ HEAD 200 260 /commcarehq/ 0.004076"
BORKED = 'Borked'


class TestCouchLogParser(UnixTimestampTestMixin, unittest.TestCase):

    def _test_log_parsing(self, line, expected_timestamp, expected_request_time, expected_attrs):
        metric_name, timestamp, request_time, attrs = parse_couch_logs(logging, line)[0]

        expected_attrs.update({
            'metric_type': 'gauge',

        })

        self.assertEqual(metric_name, 'couch.timings')
        self.assert_timestamp_equal(timestamp, *expected_timestamp)
        self.assertEqual(expected_request_time, request_time)
        self.assertEqual(expected_attrs, attrs)
        return attrs

    def test_simple_log_parsing(self):
        self._test_log_parsing(SIMPLE, (datetime.datetime(2015, 10, 31, 18, 32, 03, 963), 1446316323), 0.191515, {
            'url': '/a/*/receiver/*/',
            'couch_url': '*',
            'status_code': 'None',
            'http_method': 'PUT',
            'database': '',
            'task': '',
        })

    def test_log_parsing_content_length(self):
        self._test_log_parsing(WITH_CONTENT_LENGTH, (datetime.datetime(2017, 5, 4, 12, 20, 18, 957), 1493900418), 0.007104, {
            'url': '/a/*/apps/download/*/modules-*/forms-*.xml',
            'couch_url': '/commcarehq__apps/',
            'status_code': '200',
            'http_method': 'HEAD',
            'database': '',
            'task': '',
        })

    def test_log_parsing_database_name(self):
        self._test_log_parsing(WITH_DATABASE_NAME, (datetime.datetime(2017, 5, 4, 12, 20, 21, 416), 1493900421), 0.004401, {
            'url': '/a/*/receiver/secure/*/',
            'couch_url': '_design/users/_view/by_username',
            'status_code': '200',
            'http_method': 'GET',
            'database': 'commcarehq__users',
            'task': '',
        })

    def test_log_parsing_username(self):
        self._test_log_parsing(WITH_USERNAME, (datetime.datetime(2017, 5, 4, 12, 20, 21, 416), 1493900421), 0.004076, {
            'url': '/a/*/phone/restore/*/',
            'couch_url': '/commcarehq/',
            'status_code': '200',
            'http_method': 'HEAD',
            'database': '',
            'task': '',
        })

    def test_log_parsing_seconds(self):
        self._test_log_parsing(WITH_SECONDS, (datetime.datetime(2017, 5, 4, 12, 20, 21, 416), 1493900421), 0.004076, {
            'url': '/a/*/phone/restore/*/',
            'couch_url': '/commcarehq/',
            'status_code': '200',
            'http_method': 'HEAD',
            'database': '',
            'task': '',
        })

    def test_borked_log_line(self):
        self.assertIsNone(parse_couch_logs(logging, BORKED))

    def test_url_no_task(self):
        self._test_log_parsing(URL_NO_TASK, (datetime.datetime(2015, 10, 31, 18, 32, 03, 963), 1446316323), 0.191515, {
            'url': '/a/*/receiver/*/',
            'couch_url': '*',
            'status_code': '200',
            'http_method': 'PUT',
            'database': 'commcarehq',
            'task': '-',
        })

    def test_no_url_no_task(self):
        self._test_log_parsing(NO_URL_NO_TASK, (datetime.datetime(2015, 10, 31, 18, 32, 03, 963), 1446316323), 0.191515, {
            'url': '-',
            'couch_url': '*',
            'status_code': '200',
            'http_method': 'PUT',
            'database': 'commcarehq',
            'task': '-',
        })

    def test_no_url_task(self):
        self._test_log_parsing(NO_URL_TASK, (datetime.datetime(2015, 10, 31, 18, 32, 03, 963), 1446316323), 0.191515, {
            'url': '-',
            'couch_url': '*',
            'status_code': '200',
            'http_method': 'PUT',
            'database': 'commcarehq',
            'task': 'corehq.apps.tasks.build_app',
        })
