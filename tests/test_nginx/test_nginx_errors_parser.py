import logging
import unittest
import datetime
from nginx.errors import parse_nginx_errors
from nose_parameterized import parameterized
from parsing_utils import UnixTimestampTestMixin

logging.basicConfig(level=logging.DEBUG)

ERROR_CONNECTION_REFUSED = '2018/01/03 19:04:31 [error] 22548#22548: *16560854 connect() failed (111: Connection refused) while connecting to upstream, client: 123.12.123.12, server: www.commcarehq.org, request: "GET /a/dimagi/apps/view/ba37c12fd8c9ab8cff511e0a8d7db19b/current_version/ HTTP/2.0", upstream: "http://10.1.1.1:9010/a/dimagi/apps/view/ba37c12fd8c9ab8cff511e0a8d7db19b/current_version/", host: "www.commcarehq.org", referrer: "https://www.commcarehq.org/a/dimagi/apps/view/ba37c12fd8c9ab8cff511e0a8d7db19b/form/8e025b83c9a4c606f133f52cea6ffd5f/"'
WARN_BUFFERED_TO_FILE_UPSTREAM = '2018/01/03 19:46:16 [warn] 22552#22552: *16562567 an upstream response is buffered to a temporary file /var/lib/nginx/proxy/9/22/0001234567 while reading upstream, client: 123.12.1.1, server: www.commcarehq.org, request: "GET /a/dimagi/phone/restore/?version=2.0&since=3a740800856321c7b45c4dcf9b72982e&device_id=WebAppsLogin*user1@dimagi_commcarehq_org*as*123456&case_sync=livequery&as=123456@dimagi.commcarehq.org HTTP/1.1", upstream: "http://172.25.2.6:9010/a/dimagi/phone/restore/?version=2.0&since=3a740800856321c7b45c4dcf9b72982e&device_id=WebAppsLogin*user1@dimagi_commcarehq_org*as*123456&case_sync=livequery&as=123456@dimagi.commcarehq.org", host: "www.commcarehq.org"'
WARN_BUFFERED_TO_FILE_CLIENT = '2019/02/18 12:17:13 [warn] 20106#20106: *174576880 a client request body is buffered to a temporary file /var/lib/nginx/body/0028365258, client: 106.77.16.63, server: cas.commcarehq.org, request: "POST /a/icds-cas/receiver/secure/e67b3b92cac543138f25a8c0a2e18732/ HTTP/2.0", host: "cas.commcarehq.org"'

EXPECTED = {
    ERROR_CONNECTION_REFUSED: {
        'log_level': 'error',
        'error_type': 'connection_refused',
        'timestamp': (datetime.datetime(2018, 1, 3, 19, 4, 31), 1515006271)
    },
    WARN_BUFFERED_TO_FILE_UPSTREAM: {
        'log_level': 'warn',
        'error_type': 'buffer_to_file/upstream',
        'timestamp': (datetime.datetime(2018, 1, 3, 19, 46, 16), 1515008776)
    },
    WARN_BUFFERED_TO_FILE_CLIENT: {
        'log_level': 'warn',
        'error_type': 'buffer_to_file/client',
        'timestamp': (datetime.datetime(2019, 2, 18, 12, 17, 13), 1550492233)
    }
}


class TestNginxErrorsParser(UnixTimestampTestMixin, unittest.TestCase):

    @parameterized.expand([
        (log_line,) for log_line in EXPECTED
    ])
    def test_error_parsing(self, log_line):
        metric_name, timestamp, one, attrs = parse_nginx_errors(logging, log_line)
        self.assertEqual(metric_name, 'nginx.error_logs')

        expected = EXPECTED[log_line]
        self.assert_timestamp_equal(timestamp, *expected['timestamp'])
        self.assertEqual(one, 1)
        self.assertEqual(attrs['metric_type'], 'counter')

        self.assertEqual(attrs['log_level'], expected['log_level'])
        self.assertEqual(attrs['error_type'], expected['error_type'])
