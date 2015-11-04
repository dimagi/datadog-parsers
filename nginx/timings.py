import re
import time
from datetime import datetime

WILDCARD = '*'
APDEX_THRESHOLDS = (3, 12)


def parse_nginx_apdex(logger, line):
    if not line:
        return None

    try:
        timestamp, http_method, url, status_code, request_time = _parse_line(line)
    except Exception:
        logger.exception('Failed to parse log line')
        return None

    if _should_skip_log(url):
        return None

    # Convert the metric value into a float
    request_time = float(request_time.strip())
    if request_time > APDEX_THRESHOLDS[1]:
        # Unsatisfied
        apdex_score = 0
    elif request_time > APDEX_THRESHOLDS[0]:
        # Tolerating
        apdex_score = 0.5
    else:
        # Satisfied
        apdex_score = 1

    # Return the output as a tuple
    return ('nginx.apdex', timestamp, apdex_score, {
        'metric_type': 'gauge',
        'url': url,
        'status_code': status_code,
        'http_method': http_method,
    })


def parse_nginx_timings(logger, line):
    if not line:
        return None

    try:
        timestamp, http_method, url, status_code, request_time = _parse_line(line)
    except Exception:
        logger.exception('Failed to parse log line')
        return None

    if _should_skip_log(url):
        return None

    # Convert the metric value into a float
    request_time = float(request_time.strip())

    # Return the output as a tuple
    return ('nginx.timings', timestamp, request_time, {
        'metric_type': 'gauge',
        'url': url,
        'status_code': status_code,
        'http_method': http_method,
    })


def _should_skip_log(url):
    return re.search(r'^/static/', url)


def _parse_line(line):
    match = re.match(r'\[(?P<date>[^]]+)\]', line)
    string_date = match.group('date')
    date = datetime.strptime(string_date, "%d/%b/%Y:%H:%M:%S +0000")

    # First two dummy args are from the date being split
    _, _, http_method, url, http_protocol, status_code, request_time = line.split()

    timestamp = time.mktime(date.timetuple())
    url = _sanitize_url(url)
    return timestamp, http_method, url, status_code, request_time


def _sanitize_url(url):
    # Normalize all domain names
    url = re.sub(r'/a/[0-9a-z-]+', '/a/{}'.format(WILDCARD), url)

    # Normalize all urls with indexes or ids
    url = re.sub(r'/modules-[0-9]+', '/modules-{}'.format(WILDCARD), url)
    url = re.sub(r'/forms-[0-9]+', '/forms-{}'.format(WILDCARD), url)
    url = re.sub(r'/form_data/[a-z0-9-]+', '/form_data/{}'.format(WILDCARD), url)
    url = re.sub(r'/uuid:[a-z0-9-]+', '/uuid:{}'.format(WILDCARD), url)
    url = re.sub(r'[-0-9a-f]{10,}', '{}'.format(WILDCARD), url)

    # Remove URL params
    url = re.sub(r'\?[^ ]*', '', url)
    return url
