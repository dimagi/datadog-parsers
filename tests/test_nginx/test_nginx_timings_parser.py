import logging
import unittest
from datetime import datetime

from nose_parameterized import parameterized

from nginx.timings import _get_url_group, _sanitize_url, _get_log_details, LogDetails, _get_apdex
from parsing_utils import UnixTimestampTestMixin, get_unix_timestamp

logging.basicConfig(level=logging.DEBUG)

SIMPLE = '[28/Oct/2015:15:18:14 +0000] GET /favicon.ico HTTP/1.1 401 0.242'
API = '[28/Oct/2015:15:18:14 +0000] GET /a/uth-rhd/api/case/attachment/123/VH016.MP4 HTTP/1.1 200 1.2'
PRICING = '[28/Oct/2015:15:18:14 +0000] GET /pricing/ HTTP/1.1 200 0.2'
ICDS_DASHBOARD = '[28/Oct/2015:15:18:14 +0000] GET /a/anydomain/icds_dashboard/anything HTTP/1.1 401 0.18'
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


def _details(string_date, cache_status, method, url, status_code, duration, domain):
    ts = datetime.strptime(string_date, "%d/%b/%Y:%H:%M:%S")
    return LogDetails(
        get_unix_timestamp(ts),
        cache_status,
        method,
        url,
        status_code,
        duration,
        domain
    )

class TestLineParsing(UnixTimestampTestMixin, unittest.TestCase):
    @parameterized.expand([
        (SIMPLE, _details('28/Oct/2015:15:18:14', None, 'GET', '/favicon.ico', '401', 0.242, '')),
        (API, _details('28/Oct/2015:15:18:14', None, 'GET', '/a/*/api/case/attachment/123/VH016.MP4', '200', 1.2, 'uth-rhd')),
        (ICDS_DASHBOARD, _details('28/Oct/2015:15:18:14', None, 'GET', '/a/*/icds_dashboard/anything', '401', 0.18, 'anydomain')),
        (PRICING, _details('28/Oct/2015:15:18:14', None, 'GET', '/pricing/', '200', 0.2, '')),
        (HOME, _details('01/Sep/2017:20:14:43', None, 'GET', '/home/', '200', 18.067, '')),
        (FORMPLAYER, _details('04/Sep/2016:21:31:41', None, 'POST', '/formplayer/navigate_menu', '200', 19.33, '')),
        (CACHE, _details('01/Sep/2017:20:14:43', 'HIT', 'GET', '/a/*/apps/download/*/modules-*/forms-*.xml', '200', 18.067, 'icds-cas')),
        (CACHE_BLANK, _details('13/Sep/2017:12:34:14', '-', 'POST', '/a/*/receiver/secure/*/', '401', 0.955, 'hki-nepal-suaahara-2')),
        (URL_SPACES, _details('01/Sep/2017:07:19:09', None, 'GET', '/a/*/apps/download/*/media_profile.ccpr loira fabiao bila', '400', 0.001, 'infomovel-ccs')),
        (BORKED, None),
        (SKIPPED, None),
    ])
    def test_basic_log_parsing(self, line, expected):
        details = _get_log_details(logging, line)
        self.assertEqual(details , expected)

class TestNginxTimingsParser(UnixTimestampTestMixin, unittest.TestCase):

    def test_id_normalization(self):
        url = _sanitize_url(None, ID_NORMALIZE)

        self.assertEqual(url, '/a/*/modules-*/forms-*/form_data/*/uuid:*/')

    @parameterized.expand([
        (1, 1),
        (3, 1),
        (3.01, 0.5),
        (12, 0.5),
        (12.01, 0),
    ])
    def test_apdex(self, duration, score):
        self.assertEqual(_get_apdex(duration), score)

    @parameterized.expand([
        ('/', 'other'),
        ('/a/*/api', 'api'),
        ('/a/domain', 'other'),
        ('/1/2/3/4', 'other'),
        ('/a/*/cloudcare', 'cloudcare'),
        ('/pricing/', '/pricing/'),
        ('/home/', '/home/'),
        ('/a/*/phone/heartbeat/123456/', 'phone/heartbeat'),
        ('/hq/multimedia/file/CommCareAudio/123456/some-audio.mp3', 'mm/audio'),
        ('/hq/multimedia/file/CommCareVideo/123456/vid_daily_feeding.mp4', 'mm/video'),
        ('/hq/multimedia/file/CommCareImage/123456/module4_form0_en.png', 'mm/image'),
    ])
    def test_get_url_group(self, url, expected):
        group = _get_url_group(url)
        self.assertEqual(expected, group)
