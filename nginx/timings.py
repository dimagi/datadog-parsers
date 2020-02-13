import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from parsing_utils import get_unix_timestamp
import re
from collections import namedtuple
from datetime import datetime
import urlparse
import logging
logging.basicConfig(level=logging.INFO)

PARSER_RX = [
    r"^\[(?P<timestamp>[^]]+)\] ((?P<cache_status>[\w-]+) )?((?P<http_method>\w+) (?P<url>.+) (http\/\d\.\d)) (?P<status_code>\d{3}) (?P<request_time>\d+\.?\d*)( (?P<referer>.+))?",
]

TIMING_TAGS = {
    'http_method',
    'status_code',
}

APDEX_TAGS = TIMING_TAGS

REQUEST_TAGS = {
    'http_method',
    'status_code',
    'cache_status',
    'referer_group',
}

# These patterns are to be tried _in order_
# Group name is given by the `group_name` matching group, with the second element as fallback
URL_PATTERN_GROUPS = [
    (re.compile(r'^/a/[^/]+/(?P<group_name>phone/[^/]+)'), None),
    (re.compile(r'^/a/[^/]+/(?P<group_name>[^/]+)'), None),
    # Exact match
    (re.compile(r'^/home/$'), '/home/'),
    (re.compile(r'^/pricing/$'), '/pricing/'),
    (re.compile(r'^/accounts/login/$'), 'login'),
    # Prefix match
    (re.compile(r'^/formplayer/'), 'formplayer'),
    (re.compile(r'^/hq/multimedia/file/CommCareAudio/'), 'mm/audio'),
    (re.compile(r'^/hq/multimedia/file/CommCareVideo/'), 'mm/video'),
    (re.compile(r'^/hq/multimedia/file/CommCareImage/'), 'mm/image'),
    (re.compile(r'^/hq/multimedia/file/'), 'mm/other'),
]

MM_MAPPING = {
    'CommCareAudio': 'mm/audio',
    'CommCareVideo': 'mm/video',
    'CommCareImage': 'mm/image',
}


class LogDetails(namedtuple('LogDetails', 'timestamp, cache_status, http_method, url, status_code, request_time, domain, referer')):
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


def parse_logs(logger, line , *args):
    details = _get_log_details(logger, line)
    if not details:
        return None
    url_group = _get_url_group(details.url)
    referer_group = _get_url_group(details.referer) if details.referer else 'unknown'

    return [
        get_nginx_counter_metric(details, url_group, referer_group),
        get_nginx_apdex_metric(details, url_group, referer_group),
        get_nginx_timing_metric(details, url_group, referer_group)
     ]

def get_nginx_apdex_metric(details, url_group, referer_group):
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


def get_nginx_timing_metric(details, url_group, referer_group):
    return 'nginx.timings', details.timestamp, details.request_time, details.to_tags(
        TIMING_TAGS,
        url_group=url_group,
        metric_type='gauge',
        referer_group=referer_group,
    )


def get_nginx_counter_metric(details, url_group, referer_group):
    return 'nginx.requests', details.timestamp, 1, details.to_tags(
        REQUEST_TAGS,
        metric_type='counter',
        url_group=url_group,
        duration=get_duration_bucket(details.request_time),
        referer_group=referer_group,
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
    if details:
      if _should_skip_log(details.url):
          return None

    return details


def _get_url_group(url):
    default = 'other'
    for pattern, group_name in URL_PATTERN_GROUPS:
        match = pattern.search(url)
        if match:
            return match.groupdict().get('group_name', group_name)
    return default


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
        logging.warning('No parsers match line: "{}"'.format(line)) 
        return None

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


def _sanitize_referer(_, url):
    if url and url != '-':
        if url.startswith('http'):
            url = urlparse.urlsplit(url).path
        return _sanitize_url(_, url)
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
    'referer': _sanitize_referer,
}
