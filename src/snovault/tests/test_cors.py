import pytest


def test_cors_get_cors_headers(dummy_request):
    from snovault.cors import get_cors_headers
    assert dummy_request.response.headerlist == [
        ('Content-Type', 'text/html; charset=UTF-8'),
        ('Content-Length', '0')
    ]
    headers = {
        'Access-Control-Allow-Origin': 'some-origin.com',
        'Vary': 'Origin',
        'Other': 'Header',
        'Set-Cookie': 'xyz'
    }
    dummy_request.response.headers.update(headers)
    for header in headers:
        assert header in dummy_request.response.headers
    cors_headers = get_cors_headers(dummy_request)
    assert len(cors_headers) == 2
    assert cors_headers['Access-Control-Allow-Origin'] == 'some-origin.com'
    assert cors_headers['Vary'] == 'Origin'
