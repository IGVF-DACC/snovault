import os

from pyramid.view import view_config

from appconfig_helper import AppConfigHelper


FEATURE_FLAGS = 'FEATURE_FLAGS'

LOCAL_FEATURE_FLAGS = {
    'block_database_writes': {
        'enabled': False
    }
}


def includeme(config):
    register_feature_flags(config, LOCAL_FEATURE_FLAGS)
    config.add_route('feature_flags', '/feature-flags{slash:/?}')
    config.scan(__name__, categories=None)


def register_feature_flags(config, local_feature_flags):
    registry = config.registry
    registry[FEATURE_FLAGS] = initialize_feature_flags(
        registry.settings,
        LOCAL_FEATURE_FLAGS
    )


def initialize_feature_flags(settings, local_feature_flags):
    feature_flag_strategy = settings.get('feature_flag_strategy')
    if feature_flag_strategy == 'local':
        return LocalFeatureFlags(
            feature_flags=local_feature_flags
        )
    elif feature_flag_strategy == 'appconfig':
        return AppConfigHelper(
            appconfig_application=os.environ.get('APPCONFIG_APPLICATION'),
            appconfig_environment=os.environ.get('APPCONFIG_ENVIRONMENT'),
            appconfig_profile=os.environ.get('APPCONFIG_PROFILE'),
            max_config_age=60,
            fetch_on_read=True,
        )


class LocalFeatureFlags:

    def __init__(self, feature_flags):
        self._config = feature_flags

    @property
    def config(self):
        return self._config


@view_config(
    route_name='feature_flags',
    request_method='GET',
)
def feature_flags(context, request):
    return request.registry[FEATURE_FLAGS].config
