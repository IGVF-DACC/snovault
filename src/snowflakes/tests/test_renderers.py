def test_render_error(anonhtmltestapp):
    res = anonhtmltestapp.get('/testing-render-error', status=200)


def test_render_error_multiple_times(anonhtmltestapp):
    res = anonhtmltestapp.get('/testing-render-error', status=200)


def test_render_error_then_success(anonhtmltestapp):
    anonhtmltestapp.get('/testing-render-error', status=200)
    res = anonhtmltestapp.get('/', status=200)
