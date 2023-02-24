import pytest
import time


def pytest_configure():
    import logging
    logging.basicConfig()
    logging.getLogger('selenium').setLevel(logging.DEBUG)


@pytest.fixture
def external_tx():
    pass


def wait_for_indexing(testapp):
    double_check_number = 3
    while True:
        print('Waiting for indexing', double_check_number)
        is_indexing = bool(testapp.get('/indexer-info').json['is_indexing'])
        if is_indexing:
            double_check_number = 3
        else:
            double_check_number -= 1
        if double_check_number <= 0:
            break
        time.sleep(10)


@pytest.fixture
def poll_until_indexing_is_done():
    return wait_for_indexing


@pytest.fixture(scope='session')
def app_settings(wsgi_server_host_port, postgresql_server, elasticsearch_server):
    from snovault.tests.testappfixtures import _app_settings
    settings = _app_settings.copy()
    settings['create_tables'] = True
    settings['sqlalchemy.url'] = postgresql_server
    settings['elasticsearch.server'] = elasticsearch_server
    settings['collection_datastore'] = 'elasticsearch'
    settings['item_datastore'] = 'elasticsearch'
    settings['snovault.elasticsearch.index'] = 'snovault'
    return settings


@pytest.yield_fixture(scope='session')
def app(app_settings):
    from snowflakes import main
    app = main({}, **app_settings)

    yield app

    from snovault import DBSESSION
    DBSession = app.registry[DBSESSION]
    # Dispose connections so postgres can tear down.
    DBSession.bind.pool.dispose()


@pytest.mark.fixture_cost(500)
@pytest.yield_fixture(scope='session')
def workbook(app):
    from snovault.elasticsearch.manage_mappings import manage_mappings
    from webtest import TestApp
    from ...loadxl import load_all
    from pkg_resources import resource_filename
    environ = {
        'HTTP_ACCEPT': 'application/json',
        'REMOTE_USER': 'TEST',
    }
    testapp = TestApp(app, environ)
    inserts = resource_filename('snowflakes', 'tests/data/inserts/')
    docsdir = [resource_filename('snowflakes', 'tests/data/documents/')]
    manage_mappings(app)
    load_all(testapp, inserts, docsdir)
    wait_for_indexing(testapp)
    yield
    # XXX cleanup


@pytest.fixture(scope='session')
def wsgi_server_app(app):
    from http.cookies import SimpleCookie

    def wsgi_filter(environ, start_response):
        # set REMOTE_USER from cookie
        cookies = SimpleCookie()
        cookies.load(environ.get('HTTP_COOKIE', ''))
        if 'REMOTE_USER' in cookies:
            user = cookies['REMOTE_USER'].value
        else:
            user = 'TEST_AUTHENTICATED'
        environ['REMOTE_USER'] = user
        return app(environ, start_response)
    return wsgi_filter


@pytest.fixture(scope='session')
def base_url(wsgi_server):
    return wsgi_server
