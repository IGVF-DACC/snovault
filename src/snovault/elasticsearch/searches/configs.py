import venusian

from collections.abc import Mapping
from collections import defaultdict
from .defaults import DEFAULT_TERMS_AGGREGATION_KWARGS
from .defaults import DEFAULT_EXISTS_AGGREGATION_KWARGS
from .interfaces import SEARCH_CONFIG


def includeme(config):
    registry = config.registry
    registry[SEARCH_CONFIG] = SearchConfigRegistry()
    config.add_directive('register_search_config', register_search_config)


class Config(Mapping):
    '''
    Used for filtering out inappropriate and None **kwargs before passing along to Elasticsearch.
    Implements Mapping type so ** syntax can be used.
    '''

    def __init__(self, allowed_kwargs=[], **kwargs):
        self._allowed_kwargs = allowed_kwargs
        self._kwargs = kwargs

    def _filtered_kwargs(self):
        return {
            k: v
            for k, v in self._kwargs.items()
            if v and k in self._allowed_kwargs
        }

    def __iter__(self):
        return iter(self._filtered_kwargs())

    def __len__(self):
        return len(self._filtered_kwargs())

    def __getitem__(self, key):
        return self._filtered_kwargs()[key]


class TermsAggregationConfig(Config):

    def __init__(self, allowed_kwargs=[], **kwargs):
        super().__init__(
            allowed_kwargs=allowed_kwargs or DEFAULT_TERMS_AGGREGATION_KWARGS,
            **kwargs
        )


class ExistsAggregationConfig(Config):

    def __init__(self, allowed_kwargs=[], **kwargs):
        super().__init__(
            allowed_kwargs=allowed_kwargs or DEFAULT_EXISTS_AGGREGATION_KWARGS,
            **kwargs
        )


class SortedTupleMap:

    def __init__(self):
        self._map = defaultdict(list)

    @staticmethod
    def _convert_key_to_sorted_tuple(key):
        if isinstance(key, str):
            key = [key]
        return tuple(sorted(key))

    def get(self, key, default=None):
        return self._map.get(
            self._convert_key_to_sorted_tuple(key),
            default
        )

    def add(self, key, value):
        key = self._convert_key_to_sorted_tuple(key)
        if isinstance(value, (list, tuple)):
            self._map[key].extend(value)
        else:
            self._map[key].append(value)

    def as_dict(self):
        return dict(self._map)


def get_search_config():
    return SearchConfig


class SearchConfigRegistry:

    def __init__(self):
        self.registry = {}

    def add(self, config):
        self.registry[config.name] = config

    def update(self, config):
        if config.name in self.registry:
            self.get(config.name).update(**config)
        else:
            self.add(config)

    def register_from_func(self, name, func):
        config = get_search_config()(name, func())
        self.update(config)

    def register_from_item(self, item):
        config = get_search_config().from_item(item)
        self.update(config)

    def clear(self):
        self.registry = {}

    def get(self, field, default=None):
        return self.registry.get(field, default)


class MutableConfig(Config):

    def update(self, **kwargs):
        self._kwargs.update(kwargs)


class SearchConfig(MutableConfig):

    ITEM_CONFIG_LOCATION = 'schema'
    CONFIG_KEYS = [
        'facets',
        'columns',
        'boost_values',
        'matrix',
        'fields',
    ]

    def __init__(self, name, config):
        config = config or {}
        super().__init__(
            allowed_kwargs=self.CONFIG_KEYS,
            **config
        )
        self.name = name

    def __getattr__(self, attr):
        if attr in self.CONFIG_KEYS:
            return self.get(attr, {})
        super().__getattr__(attr)

    @classmethod
    def from_item(cls, item):
        return cls(
            item.__name__,
            getattr(
                item,
                cls.ITEM_CONFIG_LOCATION,
                {}
            )
        )


def register_search_config(config, name, factory):
    config.action(
        ('set-search-config', name),
        config.registry[SEARCH_CONFIG].register_from_func,
        args=(
            name,
            factory
        )
    )


def search_config(name, **kwargs):
    '''
    Register a custom search config by name.
    '''
    def decorate(config):
        def callback(scanner, factory_name, factory):
            scanner.config.register_search_config(name, factory)
        venusian.attach(config, callback, category='pyramid')
        return config
    return decorate
