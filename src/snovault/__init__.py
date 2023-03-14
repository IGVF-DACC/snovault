__version__ = '3.0.0'


from pyramid.config import Configurator

from pyramid.settings import asbool

from .config import (
    abstract_collection,
    collection,
    root,
)

from snovault.auditor import AuditFailure
from snovault.auditor import audit_checker

from snovault.interfaces import AUDITOR
from snovault.interfaces import BLOBS
from snovault.interfaces import CALCULATED_PROPERTIES
from snovault.interfaces import COLLECTIONS
from snovault.interfaces import CONNECTION
from snovault.interfaces import DBSESSION
from snovault.interfaces import STORAGE
from snovault.interfaces import ROOT
from snovault.interfaces import TYPES
from snovault.interfaces import UPGRADER
from snovault.interfaces import PHASE1_5_CONFIG
from snovault.interfaces import PHASE2_5_CONFIG
from snovault.interfaces import Created
from snovault.interfaces import BeforeModified
from snovault.interfaces import AfterModified
from snovault.interfaces import AfterUpgrade

from .calculated import calculated_property

from .schema_utils import load_schema

from .upgrader import upgrade_step

from .resources import (
    AbstractCollection,
    Collection,
    Item,
    Resource,
    Root,
)

from .app import (
    session,
    configure_dbsession,
    configure_sqs_client,
    configure_transaction_queue,
    configure_invalidation_queue,
    static_resources,
    changelogs,
    json_from_path,
)


def includeme(config):
    config.include('pyramid_retry')
    config.include('pyramid_tm')
    config.include('.util')
    config.include('.stats')
    config.include('.batchupgrade')
    config.include('.calculated')
    config.include('.config')
    config.include('.connection')
    config.include('.embed')
    config.include('.json_renderer')
    config.include('.validation')
    config.include('.predicates')
    config.include('.invalidation')
    config.include('.upgrader')
    config.include('.auditor')
    config.include('.storage')
    config.include('.typeinfo')
    config.include('.resources')
    config.include('.attachment')
    config.include('.schema_graph')
    config.include('.jsonld_context')
    config.include('.schema_views')
    config.include('.crud_views')
    config.include('.indexing_views')
    config.include('.resource_views')
    config.include('.elasticsearch.searches.configs')


def app_version(config):
    config.registry.settings['snovault.app_version'] = __version__


def main(global_config, **local_config):
    """ This function returns a Pyramid WSGI application.
    """
    settings = global_config
    settings.update(local_config)

    # TODO - these need to be set for dummy app
    # settings['snovault.jsonld.namespaces'] = json_asset('snovault:schemas/namespaces.json')
    # settings['snovault.jsonld.terms_namespace'] = 'https://www.encodeproject.org/terms/'
    settings['snovault.jsonld.terms_prefix'] = 'snovault'
    settings['snovault.elasticsearch.index'] = 'snovault'

    config = Configurator(settings=settings)
    from snovault.elasticsearch import APP_FACTORY
    config.registry[APP_FACTORY] = main  # used by mp_indexer
    config.include(app_version)

    config.include('pyramid_multiauth')  # must be before calling set_authorization_policy
    from pyramid_localroles import LocalRolesAuthorizationPolicy
    # Override default authz policy set by pyramid_multiauth
    config.set_authorization_policy(LocalRolesAuthorizationPolicy())
    config.include(session)

    config.include(configure_dbsession)
    config.include(configure_sqs_client)
    config.include(configure_transaction_queue)
    config.include(configure_invalidation_queue)
    config.include('snovault')
    config.commit()  # commit so search can override listing

    # Render an HTML page to browsers and a JSON document for API clients
    config.include('snowflakes.renderers')
    # these two should be application specific
    config.include('.authentication')
    config.include('snowflakes.root')

    if 'elasticsearch.server' in config.registry.settings:
        config.include('snovault.elasticsearch')
        config.include('snowflakes.search_views')

    config.include(static_resources)
    config.include(changelogs)

    if asbool(settings.get('testing', False)):
        config.include('.tests.testing_views')

    # Load upgrades last so that all views (including testing views) are
    # registered.
    # TODO we would need a generic upgrade audit PACKAGE (__init__)
    # config.include('.audit)
    # config.include('.upgrade')

    config.include('snowflakes.mappings.register')

    app = config.make_wsgi_app()

    return app
