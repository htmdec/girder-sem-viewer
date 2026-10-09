import logging

from girder_sem_viewer import IgnorePhraseFilter, IgnoreURLFilter


def _record(msg, details=None):
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )
    if details is not None:
        record.details = details
    return record


def test_ignore_url_filter_drops_audit_record():
    filt = IgnoreURLFilter(("system", "check"))
    record = _record(
        "something entirely unrelated",
        details={"method": "GET", "route": ("system", "check"), "status": 200},
    )
    assert filt.filter(record) is False


def test_ignore_url_filter_keeps_audit_record_with_other_details():
    filt = IgnoreURLFilter(("system", "check"))
    for details in (
        {"method": "POST", "route": ("system", "check"), "status": 200},
        {"method": "GET", "route": ("system", "version"), "status": 200},
        {"method": "GET", "route": ("system", "check"), "status": 403},
    ):
        record = _record("something entirely unrelated", details=details)
        assert filt.filter(record) is True


def test_ignore_url_filter_drops_access_log_line():
    filt = IgnoreURLFilter(("system", "check"))
    record = _record('127.0.0.1 - - "GET /api/v1/system/check HTTP/1.1" 200')
    assert filt.filter(record) is False


def test_ignore_url_filter_keeps_other_access_log_lines():
    filt = IgnoreURLFilter(("system", "check"))
    record = _record('127.0.0.1 - - "GET /api/v1/system/version HTTP/1.1" 200')
    assert filt.filter(record) is True


def test_ignore_url_filter_honors_verb_and_status():
    filt = IgnoreURLFilter(("item", ":id"), verb="DELETE", status=204)
    record = _record(
        "msg", details={"method": "DELETE", "route": ("item", ":id"), "status": 204}
    )
    assert filt.filter(record) is False


def test_ignore_phrase_filter():
    filt = IgnorePhraseFilter("Uptime-Kuma")
    assert filt.filter(_record("GET / by Uptime-Kuma/1.23")) is False
    assert filt.filter(_record("GET / by curl/8.5.0")) is True
