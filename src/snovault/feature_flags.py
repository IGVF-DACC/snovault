import os

from appconfig_helper import AppConfigHelper


FEATURE_FLAGS = 'FEATURE_FLAGS'


def includeme(config):
    registry = config.registry
    registry[FEATURE_FLAGS] = get_feature_flags(registry.settings)


def get_feature_flags(settings):
    feature_flag_strategy = settings.get('feature_flag_strategy')
    if feature_flag_strategy == 'local':
        return LocalFeatureFlags()
    elif feature_flag_strategy == 'appconfig':
        return AppConfigHelper(
            appconfig_application=os.environ.get('APPCONFIG_APPLICATION'),
            appconfig_environment=os.environ.get('APPCONFIG_ENVIRONMENT'),
            appconfig_profile=os.environ.get('APPCONFIG_PROFILE'),
            max_config_age=60,
            fetch_on_read=True,
        )


class LocalFeatureFlags:

    def __init__(self):
        self.config = {
            'block_database_writes': {
                'enabled': False
            }
        }

    @property
    def config(self):
        return self.config
