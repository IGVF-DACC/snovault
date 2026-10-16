from past.builtins import basestring
from pyramid.decorator import reify
from uuid import UUID
from .cache import ManagerLRUCache
from .interfaces import (
    COLLECTIONS,
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

    @reify
    def storage(self):
        return self.registry[STORAGE]

    @reify
    def types(self):
        return self.registry[TYPES]

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

        try:
            Item = self.types.by_item_type[model.item_type].factory
        except KeyError:
            raise UnknownItemTypeError(model.item_type)

        item = Item(self.registry, model)
        model.used_for(item)
        self.item_cache[uuid] = item
        return item

    def get_by_uuids(self, uuids, default=None):
        ''' Batched equivalent of get_by_uuid.

        Resolves cache hits locally and fetches the remaining uuids from
        storage in a single call instead of one storage round trip per
        uuid, which is what made large (5000-100000 member) linkTo/rev
        lists expensive to resolve. Goes straight to write (Postgres)
        storage: this is only ever reached when calculate_properties is
        actually computing a schema_links/rev property from scratch,
        which -- same as the deep-embed fan-out in Path.expand_path_with_frame
        -- only happens when request.datastore is already 'database'
        (indexing, or after a cache invalidation forces it for the rest
        of the request). A cache-valid item's @@object view is served
        directly from its pre-rendered ES document (cached_views.py) and
        never reaches this code at all, so there's no case where this
        should go through the ES-backed read path.
        '''
        results = [default] * len(uuids)
        fetch_uuids = []
        fetch_indices = []
        for i, candidate in enumerate(uuids):
            if isinstance(candidate, basestring):
                try:
                    candidate = UUID(candidate)
                except ValueError:
                    continue
            elif not isinstance(candidate, UUID):
                raise TypeError(candidate)

            candidate = str(candidate)
            cached = self.item_cache.get(candidate)
            if cached is not None:
                results[i] = cached
            else:
                fetch_uuids.append(candidate)
                fetch_indices.append(i)

        if fetch_uuids:
            models = self.storage.write.get_by_uuids(fetch_uuids)
            for i, fetch_uuid, model in zip(fetch_indices, fetch_uuids, models):
                if model is None:
                    continue
                try:
                    Item = self.types.by_item_type[model.item_type].factory
                except KeyError:
                    raise UnknownItemTypeError(model.item_type)
                item = Item(self.registry, model)
                model.used_for(item)
                self.item_cache[fetch_uuid] = item
                results[i] = item

        return results

    def get_by_unique_key(self, unique_key, name, default=None, index=None):
        pkey = (unique_key, name)

        cached = self.unique_key_cache.get(pkey)
        if cached is not None:
            return self.get_by_uuid(cached)

        model = self.storage.get_by_unique_key(unique_key, name, index=index)
        if model is None:
            return default

        uuid = model.uuid
        self.unique_key_cache[pkey] = uuid
        cached = self.item_cache.get(uuid)
        if cached is not None:
            return cached

        try:
            Item = self.types.by_item_type[model.item_type].factory
        except KeyError:
            raise UnknownItemTypeError(model.item_type)

        item = Item(self.registry, model)
        model.used_for(item)
        self.item_cache[uuid] = item
        return item

    def _cache_model(self, model):
        if model is None:
            return
        uuid = str(model.uuid)
        if uuid in self.item_cache:
            return
        try:
            Item = self.types.by_item_type[model.item_type].factory
        except KeyError:
            return
        item = Item(self.registry, model)
        model.used_for(item)
        self.item_cache[uuid] = item

    def warm_cache_for_paths(self, paths):
        ''' Pre-resolves a batch of resource paths (e.g. the members of a
        large linkTo/rev list) against write (Postgres) storage in a
        couple of grouped queries, so that the per-path request.embed()
        calls that follow -- see Path.expand_path_with_frame in util.py --
        hit a warm cache instead of each making their own database round
        trip. Always goes through write storage: the deep-embed fan-out
        this exists for only ever runs during indexing or after a cache
        invalidation, both of which already force datastore='database',
        so there is nothing for the ES-backed read path to contribute here.
        '''
        collections = self.registry[COLLECTIONS]
        by_collection = {}
        for path in paths:
            parts = path.strip('/').split('/')
            if len(parts) != 2:
                continue
            collection_name, name = parts
            collection = collections.get(collection_name)
            if collection is None:
                continue
            by_collection.setdefault(collection_name, []).append(name)

        for collection_name, names in by_collection.items():
            collection = collections[collection_name]
            uuid_names = []
            key_names = []
            for name in names:
                try:
                    UUID(name)
                except ValueError:
                    key_names.append(name)
                else:
                    uuid_names.append(name)

            if uuid_names:
                for model in self.storage.write.get_by_uuids(uuid_names):
                    self._cache_model(model)

            if key_names and collection.unique_key is not None:
                index = getattr(collection.type_info, 'item_type', None)
                models = self.storage.write.get_by_unique_keys(
                    collection.unique_key, key_names, index=index,
                )
                for name, model in zip(key_names, models):
                    if model is None:
                        continue
                    self._cache_model(model)
                    self.unique_key_cache[(collection.unique_key, name)] = model.uuid

    def get_rev_links(self, model, rel, *types):
        item_types = [self.types[t].item_type for t in types]
        return self.storage.get_rev_links(model, rel, *item_types)

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
        self.storage.update(model, properties, sheets, unique_keys, links)
