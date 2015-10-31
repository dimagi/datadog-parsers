import re
import time
from datetime import datetime
from shared.utils import sanitize_url


def parse_nginx_timings(logger, line):
    if not line:
        return None

    try:
        date, http_method, url, status_code, request_time = _parse_line(line)
    except Exception:
        logger.exception('Failed to parse log line')
        return None

    if _should_skip_log(url):
        return None

    url = sanitize_url(url)
    timestamp = time.mktime(date.timetuple())

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

    return date, http_method, url, status_code, request_time
