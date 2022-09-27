import os
import pytest

from pyramid.paster import get_appsettings


@pytest.fixture(scope='session')
def ini_file(request):
    path = os.path.abspath(
        'config/pyramid/ini/development.ini'
    )
    return get_appsettings(path, name='app')
