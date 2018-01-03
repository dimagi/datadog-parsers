import os
import sys
from parsing_utils import get_unix_timestamp

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import re
from collections import namedtuple
from datetime import datetime


SHARED_DETAILS_REGEXES = [
    r'(?P<timestamp>\d\d\d\d/\d\d/\d\d \d\d:\d\d:\d\d) \[(?P<log_level>\w+)\].*'
]

TYPE_REGEXES = [
    (r'connect\(\) failed \(111: Connection refused\) while connecting to upstream', 'connection_refused'),
    (r'an upstream response is buffered to a temporary file', 'buffered_to_file')
]


LogDetails = namedtuple('LogDetails', ['timestamp', 'log_level', 'error_type'])


def parse_nginx_errors(logger, line):
    details = _get_log_details(logger, line)
    if not details:
        return None

    return 'nginx.error_logs', details.timestamp, 1, {
        'metric_type': 'counter',
        'log_level': details.log_level,
        'error_type': details.error_type,
    }


def _get_log_details(logger, line):
    if not line:
        return None

    try:
        details = _parse_line(line)
    except Exception:
        logger.exception('Failed to parse log line')
        return None

    return details


def _parse_line(line):
    groupdict = None
    for regex in SHARED_DETAILS_REGEXES:
        match = re.match(regex, line)
        if match:
            groupdict = match.groupdict()
            break

    if not groupdict:
        raise Exception('No parsers match line: "{}"'.format(line))

    for regex, error_type in TYPE_REGEXES:
        if re.search(regex, line):
            break
    else:
        error_type = 'other'

    return LogDetails(
        timestamp=_parse_timestamp(groupdict['timestamp']),
        log_level=groupdict['log_level'],
        error_type=error_type,
    )


def _parse_timestamp(string_date):
    date = datetime.strptime(string_date, "%Y/%m/%d %H:%M:%S")
    return get_unix_timestamp(date)
