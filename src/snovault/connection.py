from past.builtins import basestring
from pyramid.decorator import reify
from uuid import UUID
from .cache import ManagerLRUCache
from .interfaces import (
    CONNECTION,
    STORAGE,
    TYPES,
)


def includeme(config):
    registry = config.registry
    registry[CONNECTION] = Connection(registry)


class UnknownItemTypeError(Exception):
    pass


class Connection(object):
    ''' Intermediates between the storage and the rest of the system
    '''

    def __init__(self, registry):
        self.registry = registry
        self.item_cache = ManagerLRUCache('snovault.connection.item_cache', 1000)
        self.unique_key_cache = ManagerLRUCache('snovault.connection.key_cache', 1000)
        embed_cache_capacity = int(registry.settings.get('embed_cache.capacity', 5000))
        self.embed_cache = ManagerLRUCache('snovault.connection.embed_cache', embed_cache_capacity)
        self.rev_link_cache = ManagerLRUCache('snovault.connection.rev_link_cache', 1000)
        self.cohort_cache = ManagerLRUCache('snovault.connection.cohort_cache', 1000)
        self.cohort_size = max(min(500, self.rev_link_cache.capacity(registry) // 4), 1)  # A quarter of the cache, so links of one cohort always fit.

    @reify
    def storage(self):
        return self.registry[STORAGE]

    @reify
    def types(self):
        return self.registry[TYPES]

    def _cache_unique_keys(self, item):
        unique_key = item.collection.unique_key
        if unique_key is None:
            return
        try:
            values = item.unique_keys(item.properties).get(unique_key, ())
        except (KeyError, TypeError):  # Ignore unique_keys overrides that index into properties directly.
            return
        for value in values:
            self.unique_key_cache[(unique_key, value)] = item.uuid

    def _forget_unique_keys(self, model, unique_keys):
        # Current Key rows pointing to the Resource, through unique_keys backref.
        current = {
            (key.name, key.value)
            for key in model.unique_keys
        }
        new = {
            (name, value)
            for name, values in unique_keys.items()
            for value in values
        }
        for pkey in current - new:
            self.unique_key_cache.pop(pkey)

    def _get_item_from_model(self, model):
        uuid = str(model.uuid)
        item = self.item_cache.get(uuid)
        if item is not None:
            return item
        try:
            Item = self.types.by_item_type[model.item_type].factory
        except KeyError:
            raise UnknownItemTypeError(model.item_type)
        item = Item(self.registry, model)
        model.used_for(item)
        self.item_cache[uuid] = item
        self._cache_unique_keys(item)
        return item

    def get_by_uuid(self, uuid, default=None):
        if isinstance(uuid, basestring):
            try:
                uuid = UUID(uuid)
            except ValueError:
                return default
        elif not isinstance(uuid, UUID):
            raise TypeError(uuid)
        uuid = str(uuid)
        cached = self.item_cache.get(uuid)
        if cached is not None:
            return cached
        model = self.storage.get_by_uuid(uuid)
        if model is None:
            return default
        return self._get_item_from_model(model)

    def get_by_uuids(self, uuids, default=None):
        normalized_uuids = []
        for uuid in uuids:
            if isinstance(uuid, basestring):
                try:
                    uuid = UUID(uuid)
                except ValueError:
                    normalized_uuids.append(None)
                    continue
            elif not isinstance(uuid, UUID):
                raise TypeError(uuid)
            normalized_uuids.append(str(uuid))
        found = {}  # Keep results locally in case of cache churn.
        missing = []
        # Dedup and preserve order
        for uuid in dict.fromkeys(u for u in normalized_uuids if u is not None):
            cached = self.item_cache.get(uuid)
            if cached is not None:
                found[uuid] = cached
            else:
                missing.append(uuid)
        if missing:
            for uuid, model in zip(missing, self.storage.get_by_uuids(missing)):
                if model is not None:
                    found[uuid] = self._get_item_from_model(model)
        return [
            found.get(uuid, default)
            for uuid in normalized_uuids
        ]

    def get_by_unique_key(self, unique_key, name, default=None, index=None):
        pkey = (unique_key, name)
        cached = self.unique_key_cache.get(pkey)
        if cached is not None:
            return self.get_by_uuid(cached)
        model = self.storage.get_by_unique_key(unique_key, name, index=index)
        if model is None:
            return default
        self.unique_key_cache[pkey] = model.uuid
        return self._get_item_from_model(model)

    def _load_rev_links(self, model, rels):
        uuid = str(model.uuid)
        cohort = self.cohort_cache.get(uuid, (uuid,))
        pending = [
            member
            for member in cohort
            if member not in self.rev_link_cache
        ]
        by_target = self.storage.get_incoming_links_batch(pending, rels)
        if by_target is None:
            return None
        for target, by_rel in by_target.items():
            self.rev_link_cache[target] = by_rel
        return by_target[uuid]

    def get_rev_links(self, model, rel, *types):
        item_types = [self.types[t].item_type for t in types]
        rels = self.types.by_item_type[model.item_type].rev_link_rels
        if rel not in rels:
            # Fall back to individual lookup.
            return self.storage.get_rev_links(model, rel, *item_types)
        by_rel = self.rev_link_cache.get(str(model.uuid))
        if by_rel is None:
            # Try to load cache.
            by_rel = self._load_rev_links(model, rels)
            if by_rel is None:
                # Fall back to individual lookup.
                return self.storage.get_rev_links(model, rel, *item_types)
        return [
            source
            for source, item_type in by_rel[rel]
            if not item_types or item_type in item_types
        ]

    def __iter__(self, *types):
        if not types:
            item_types = self.types.by_item_type.keys()
        else:
            item_types = [self.types[t].item_type for t in types]
        for uuid in self.storage.__iter__(*item_types):
            yield uuid

    def __len__(self, *types):
        if not types:
            item_types = self.types.by_item_type.keys()
        else:
            item_types = [self.types[t].item_type for t in types]
        return self.storage.__len__(*item_types)

    def __getitem__(self, uuid):
        item = self.get_by_uuid(uuid)
        if item is None:
            raise KeyError(uuid)
        return item

    def create(self, type_, uuid):
        ti = self.types[type_]
        return self.storage.create(ti.item_type, uuid)

    def update(self, model, properties, sheets=None, unique_keys=None, links=None):
        if unique_keys is not None:
            self._forget_unique_keys(model, unique_keys)
        self.storage.update(model, properties, sheets, unique_keys, links)
