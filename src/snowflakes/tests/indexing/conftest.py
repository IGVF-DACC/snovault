import pytest
import time


def pytest_configure():
    import logging
    logging.basicConfig()
    logging.getLogger('selenium').setLevel(logging.DEBUG)


@pytest.fixture
def external_tx():
    pass


def wait_for_indexing():
    time.sleep(45)


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
    from snovault.elasticsearch.manage_mappings import manage_mappings
    app = main({}, **app_settings)
    manage_mappings(app)

    yield app

    from snovault import DBSESSION
    DBSession = app.registry[DBSESSION]
    # Dispose connections so postgres can tear down.
    DBSession.bind.pool.dispose()


@pytest.mark.fixture_cost(500)
@pytest.yield_fixture(scope='session')
def workbook(app):
    from webtest import TestApp
    environ = {
        'HTTP_ACCEPT': 'application/json',
        'REMOTE_USER': 'TEST',
    }
    testapp = TestApp(app, environ)

    from ...loadxl import load_all
    from pkg_resources import resource_filename
    inserts = resource_filename('snowflakes', 'tests/data/inserts/')
    docsdir = [resource_filename('snowflakes', 'tests/data/documents/')]
    load_all(testapp, inserts, docsdir)
    wait_for_indexing()
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
