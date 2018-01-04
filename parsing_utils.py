import calendar


def get_unix_timestamp(naive_datetime_representing_utc):
    return calendar.timegm(naive_datetime_representing_utc.utctimetuple())


class UnixTimestampTestMixin(object):
    def assert_timestamp_equal(self, actual_timestamp, expected_utc_datetime, expected_timestamp=None):
        """
        this is a nice way to force the writer of a test that includes testing timestamps
        to include _both_ the actual timestamp int _and_ the utc datetime it represents
        """

        if expected_timestamp is not None:
            # assert the writer of the test's datetime and timestamp match
            self.assertEqual(get_unix_timestamp(expected_utc_datetime), expected_timestamp)
            # assert the timestamp under test matches the expected value
            self.assertEqual(actual_timestamp, expected_timestamp)
        else:
            # help the writer of the test by generating the timestamp for them
            self.fail("Use this timestamp value: {}".format(get_unix_timestamp(expected_utc_datetime)))
