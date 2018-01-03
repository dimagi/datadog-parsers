import logging
import unittest
import datetime
import time
from nginx.errors import parse_nginx_errors
from nose_parameterized import parameterized

logging.basicConfig(level=logging.DEBUG)

ERROR_CONNECTION_REFUSED = '2018/01/03 19:04:31 [error] 22548#22548: *16560854 connect() failed (111: Connection refused) while connecting to upstream, client: 123.12.123.12, server: www.commcarehq.org, request: "GET /a/dimagi/apps/view/ba37c12fd8c9ab8cff511e0a8d7db19b/current_version/ HTTP/2.0", upstream: "http://10.1.1.1:9010/a/dimagi/apps/view/ba37c12fd8c9ab8cff511e0a8d7db19b/current_version/", host: "www.commcarehq.org", referrer: "https://www.commcarehq.org/a/dimagi/apps/view/ba37c12fd8c9ab8cff511e0a8d7db19b/form/8e025b83c9a4c606f133f52cea6ffd5f/"'
WARN_BUFFERED_TO_FILE = '2018/01/03 19:46:16 [warn] 22552#22552: *16562567 an upstream response is buffered to a temporary file /var/lib/nginx/proxy/9/22/0001234567 while reading upstream, client: 123.12.1.1, server: www.commcarehq.org, request: "GET /a/dimagi/phone/restore/?version=2.0&since=3a740800856321c7b45c4dcf9b72982e&device_id=WebAppsLogin*user1@dimagi_commcarehq_org*as*123456&case_sync=livequery&as=123456@dimagi.commcarehq.org HTTP/1.1", upstream: "http://172.25.2.6:9010/a/dimagi/phone/restore/?version=2.0&since=3a740800856321c7b45c4dcf9b72982e&device_id=WebAppsLogin*user1@dimagi_commcarehq_org*as*123456&case_sync=livequery&as=123456@dimagi.commcarehq.org", host: "www.commcarehq.org"'


class TestNginxErrorsParser(unittest.TestCase):

    def test_error_connection_refused(self):
        metric_name, timestamp, one, attrs = parse_nginx_errors(logging, ERROR_CONNECTION_REFUSED)
        self.assertEqual(metric_name, 'nginx.error_logs')
        self.assertEqual(timestamp, time.mktime(datetime.datetime(2018, 1, 3, 19, 4, 31).timetuple()))
        self.assertEqual(one, 1)
        self.assertEqual(attrs['metric_type'], 'counter')

        self.assertEqual(attrs['log_level'], 'error')
        self.assertEqual(attrs['error_type'], 'connection_refused')

    def test_warn_buffered_to_file(self):
        metric_name, timestamp, one, attrs = parse_nginx_errors(logging, WARN_BUFFERED_TO_FILE)
        self.assertEqual(metric_name, 'nginx.error_logs')
        self.assertEqual(timestamp, time.mktime(datetime.datetime(2018, 1, 3, 19, 46, 16).timetuple()))
        self.assertEqual(one, 1)
        self.assertEqual(attrs['metric_type'], 'counter')

        self.assertEqual(attrs['log_level'], 'warn')
        self.assertEqual(attrs['error_type'], 'buffered_to_file')
