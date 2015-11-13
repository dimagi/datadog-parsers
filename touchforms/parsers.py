import time
import re
from datetime import datetime

def parser(logger, line):
    if not line or _should_skip(line):
        return None

    try:
        timestamp, domain, action, request_seconds = _parse_line(line)
    except Exception:
        logger.exception('Failed to parse log line')
        return None

    return ('touchforms.timings', timestamp, request_seconds, {
        'metric_type': 'gauge',
        'action': action,
        'domain': domain,
    })


def _should_skip(line):
    return 'Finished processing action' not in line


def _parse_line(line):
    match = re.search(r'action (?P<action>[\w-]+)', line)
    action = match.group('action')

    match = re.search(r'(?P<milliseconds>[0-9\.]+) ms ', line)
    request_seconds = float(match.group('milliseconds')) / 1000

    match = re.search(r"domain '(?P<domain>[-_\w]+)'", line)
    domain = match.group('domain')

    parts = line.split()
    string_date = '{} {}'.format(parts[1], parts[2]).split(',')[0]
    date = datetime.strptime(string_date, "%Y-%m-%d %H:%M:%S")
    timestamp = time.mktime(date.timetuple())

    return timestamp, domain, action, request_seconds
