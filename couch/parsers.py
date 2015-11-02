import collections
import time
from datetime import datetime
from shared.utils import sanitize_url, sanitize_couch_url

"""
Sample log line:
    2015-10-31 18:32:03,963 [:mvp-pampaida] /a/mvp-pampaida/receiver/630916e49084b142c0a5a69c3a52b9b3/ PUT None d3abf611f2acdc7b4c32f7ebf4982a88 0:00:00.191515
"""


def parse_couch_logs(logger, line):
    if not line:
        return None

    try:
        timestamp, domain, url, http_method, status_code, couch_url, request_seconds = _parse_line(line)
    except Exception:
        logger.exception('Failed to parse log line')
        return None

    return ('couch.timings', timestamp, request_seconds, {
        'metric_type': 'gauge',
        'url': url,
        'domain': domain,
        'http_method': http_method,
        'status_code': status_code,
        'couch_url': couch_url,
    })


def _parse_line(line):
    date1, date2, domain, url, http_method, status_code, couch_url, request_time = line.split()

    # Combine the two date parts and then strip off milliseconds because it cannot be parsed by datetime
    string_date = '{} {}'.format(date1, date2).split(',')[0]

    date = datetime.strptime(string_date, "%Y-%m-%d %H:%M:%S")
    timestamp = time.mktime(date.timetuple())

    # Strip off first to letters which are [: and last letter which is a closing ]
    domain = domain[2:-1]

    url = sanitize_url(url)
    couch_url = sanitize_couch_url(couch_url)

    hours, minutes, seconds = request_time.split(':')
    request_seconds = float(seconds) + (60 * float(minutes)) + (60 * 60 * float(hours))

    return timestamp, domain, url, http_method, status_code, couch_url, request_seconds
