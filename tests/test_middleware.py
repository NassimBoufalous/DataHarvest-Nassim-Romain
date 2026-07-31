from types import SimpleNamespace

from dataharvest.middleware import LoggingMiddleware, RetryMiddleware


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def make_config(retries=3):
    return SimpleNamespace(fetcher=SimpleNamespace(retries=retries))


def test_logging_middleware_process_request_returns_url_and_headers_unchanged():
    middleware = LoggingMiddleware()
    headers = {"User-Agent": "DataHarvest/1.0"}

    url, returned_headers = middleware.process_request("https://example.com/", headers)

    assert url == "https://example.com/"
    assert returned_headers is headers


def test_logging_middleware_process_response_returns_response_unchanged():
    middleware = LoggingMiddleware()
    middleware.process_request("https://example.com/", {})
    response = FakeResponse(200)

    result = middleware.process_response(response)

    assert result is response


def test_logging_middleware_process_response_without_prior_request():
    # process_response() appele sans process_request() prealable : ne doit pas lever.
    middleware = LoggingMiddleware()
    response = FakeResponse(200)

    result = middleware.process_response(response)

    assert result is response


def test_retry_middleware_init_reads_max_retries_from_config():
    middleware = RetryMiddleware(make_config(retries=5), base_delay=2.0)

    assert middleware.max_retries == 5
    assert middleware.base_delay == 2.0


def test_retry_middleware_process_request_and_response_are_passthrough():
    middleware = RetryMiddleware(make_config())
    headers = {"User-Agent": "DataHarvest/1.0"}

    url, returned_headers = middleware.process_request("https://example.com/", headers)
    response = FakeResponse(200)
    returned_response = middleware.process_response(response)

    assert (url, returned_headers) == ("https://example.com/", headers)
    assert returned_response is response


def test_should_retry_true_on_exception():
    middleware = RetryMiddleware(make_config())

    assert middleware.should_retry(exception=ConnectionError("boom")) is True


def test_should_retry_true_on_429_and_5xx():
    middleware = RetryMiddleware(make_config())

    assert middleware.should_retry(response=FakeResponse(429)) is True
    assert middleware.should_retry(response=FakeResponse(500)) is True
    assert middleware.should_retry(response=FakeResponse(503)) is True


def test_should_retry_false_on_success_or_client_error():
    middleware = RetryMiddleware(make_config())

    assert middleware.should_retry(response=FakeResponse(200)) is False
    assert middleware.should_retry(response=FakeResponse(404)) is False


def test_should_retry_false_when_nothing_given():
    middleware = RetryMiddleware(make_config())

    assert middleware.should_retry() is False


def test_backoff_delay_is_exponential():
    middleware = RetryMiddleware(make_config(), base_delay=1.0)

    assert middleware.backoff_delay(0) == 1.0
    assert middleware.backoff_delay(1) == 2.0
    assert middleware.backoff_delay(3) == 8.0
