import re
import time
from collections import namedtuple
from datetime import datetime

LogDetails = namedtuple('LogDetails', 'timestamp, http_method, url, status_code, request_time, domain')

WILDCARD = '*'
APDEX_THRESHOLDS = (3, 12)


def parse_nginx_apdex(logger, line):
    details = _get_log_details(logger, line)
    if not details:
        return None

    if details.request_time > APDEX_THRESHOLDS[1]:
        # Unsatisfied
        apdex_score = 0
    elif details.request_time > APDEX_THRESHOLDS[0]:
        # Tolerating
        apdex_score = 0.5
    else:
        # Satisfied
        apdex_score = 1

    # Return the output as a tuple
    return ('nginx.apdex', details.timestamp, apdex_score, {
        'metric_type': 'gauge',
        'url': details.url,
        'status_code': details.status_code,
        'http_method': details.http_method,
        'domain': details.domain,
    })


def parse_nginx_timings(logger, line):
    details = _get_log_details(logger, line)
    if not details:
        return None

    # Return the output as a tuple
    return ('nginx.timings', details.timestamp, details.request_time, {
        'metric_type': 'gauge',
        'url': details.url,
        'status_code': details.status_code,
        'http_method': details.http_method,
        'domain': details.domain,
    })


def parse_nginx_counter(logger, line):
    details = _get_log_details(logger, line)
    if not details:
        return None

    url_group = _get_url_group(details.url)

    # Return the output as a tuple
    return ('nginx.requests', details.timestamp, 1, {
        'metric_type': 'counter',
        'url_group': url_group,
        'url': details.url,
        'status_code': details.status_code,
        'http_method': details.http_method,
        'domain': details.domain,
    })


def _get_log_details(logger, line):
    if not line:
        return None

    try:
        details = _parse_line(line)
    except Exception:
        logger.exception('Failed to parse log line')
        return None

    if _should_skip_log(details.url):
        return None

    return details


def _get_url_group(url):
    default = 'other'
    if url.startswith('/a/' + WILDCARD):
        parts = url.split('/')
        return parts[3] if len(parts) >= 4 else default

    return default


def _should_skip_log(url):
    return re.search(r'^/static/', url)


def _parse_line(line):
    match = re.match(r'\[(?P<date>[^]]+)\]', line)
    string_date = match.group('date')
    date = datetime.strptime(string_date, "%d/%b/%Y:%H:%M:%S +0000")

    # First two dummy args are from the date being split
    _, _, http_method, url, http_protocol, status_code, request_time = line.split()

    timestamp = time.mktime(date.timetuple())
    domain = _extract_domain(url)
    url = _sanitize_url(url)
    return LogDetails(timestamp, http_method, url, status_code, float(request_time.strip()), domain)


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


def _extract_domain(url):
    match = re.search(r'/a/(?P<domain>[0-9a-z-]+)', url)
    if not match:
        return ''
    return match.group('domain')
