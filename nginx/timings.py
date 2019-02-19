import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from parsing_utils import get_unix_timestamp
import re
from collections import namedtuple
from datetime import datetime


PARSER_RX = [
    r"^\[(?P<timestamp>[^]]+)\] ((?P<cache_status>[\w-]+) )?((?P<http_method>\w+) (?P<url>.+) (http\/\d\.\d)) (?P<status_code>\d{3}) (?P<request_time>\d+\.?\d*)",
]

TIMING_TAGS = {
    'http_method',
    'status_code',
}

APDEX_TAGS = TIMING_TAGS

REQUEST_TAGS = {
    'http_method',
    'status_code',
    'cache_status'
}

STATIC_GROUPS = {
    '/home/': '/home/',
    '/pricing/': '/pricing/',
    '/accounts/login/': 'login'
}

MM_MAPPING = {
    'CommCareAudio': 'mm/audio',
    'CommCareVideo': 'mm/video',
    'CommCareImage': 'mm/image',
}


class LogDetails(namedtuple('LogDetails', 'timestamp, cache_status, http_method, url, status_code, request_time, domain')):
    def to_tags(self, tag_whitelist, **kwargs):
        tags = self._asdict()
        if not self.cache_status:
            del tags['cache_status']

        for tag in tags:
            if tag not in tag_whitelist:
                del tags[tag]

        tags.update(kwargs)
        return tags


WILDCARD = '*'
APDEX_THRESHOLDS = (3, 12)


def parse_nginx_apdex(logger, line):
    details = _get_log_details(logger, line)
    if not details:
        return None

    url_group = _get_url_group(details.url)

    if details.request_time > APDEX_THRESHOLDS[1]:
        # Unsatisfied
        apdex_score = 0
    elif details.request_time > APDEX_THRESHOLDS[0]:
        # Tolerating
        apdex_score = 0.5
    else:
        # Satisfied
        apdex_score = 1

    return 'nginx.apdex', details.timestamp, apdex_score, details.to_tags(
        APDEX_TAGS,
        url_group=url_group,
        metric_type='gauge',
    )


def parse_nginx_timings(logger, line):
    details = _get_log_details(logger, line)
    if not details:
        return None

    url_group = _get_url_group(details.url)

    return 'nginx.timings', details.timestamp, details.request_time, details.to_tags(
        TIMING_TAGS,
        url_group=url_group,
        metric_type='gauge',
    )


def parse_nginx_counter(logger, line):
    details = _get_log_details(logger, line)
    if not details:
        return None

    url_group = _get_url_group(details.url)

    return 'nginx.requests', details.timestamp, 1, details.to_tags(
        REQUEST_TAGS,
        metric_type='counter',
        url_group=url_group,
        duration=get_duration_bucket(details.request_time)
    )


def get_duration_bucket(duration_in_sec):
    if duration_in_sec < 1:
        return 'lt_001s'
    elif duration_in_sec < 5:
        return 'lt_005s'
    elif duration_in_sec < 20:
        return 'lt_020s'
    elif duration_in_sec < 120:
        return 'lt_120s'
    else:
        return 'over_120s'


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
        group = parts[3] if len(parts) >= 4 else default
        if group == 'phone':
            return 'phone/{}'.format(parts[4])
        return group
    elif url.startswith('/hq/multimedia/file/'):
        parts = url.split('/')
        return MM_MAPPING.get(parts[4], 'mm/other')
    else:
        return STATIC_GROUPS.get(url, default)


def _should_skip_log(url):
    return re.search(r'^/static/', url)


def _parse_line(line):
    groupdict = None
    for parser in PARSER_RX:
        match = re.match(parser, line, re.IGNORECASE)
        if match:
            groupdict = match.groupdict()
            break

    if not groupdict:
        raise Exception('No parsers match line: "{}"'.format(line))

    fields = {}
    for field_name, transform in FIELDS.items():
        val = groupdict.get(field_name)
        fields[field_name] = transform(groupdict, val) if transform else val

    return LogDetails(**fields)


def _sanitize_url(_, url):
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


def _extract_domain(all_fields, _):
    url = all_fields['url']
    match = re.search(r'/a/(?P<domain>[0-9a-z-]+)', url)
    if not match:
        return ''
    return match.group('domain')


def _parse_timestamp(_, string_date):
    date = datetime.strptime(string_date, "%d/%b/%Y:%H:%M:%S +0000")
    return get_unix_timestamp(date)


def _request_time_to_float(_, duration):
    return float(duration.strip())


FIELDS = {
    'timestamp': _parse_timestamp,
    'cache_status': None,
    'http_method': None,
    'url': _sanitize_url,
    'status_code': None,
    'request_time': _request_time_to_float,
    'domain': _extract_domain,
}
