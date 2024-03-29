from functools import wraps

from past.builtins import basestring
from pyramid.settings import asbool
from pyramid.traversal import (
    find_resource,
)
from pyramid.view import view_config

from pyramid.httpexceptions import HTTPServiceUnavailable

from uuid import (
    UUID,
    uuid4,
)
from .etag import if_match_tid
from .interfaces import (
    COLLECTIONS,
    CONNECTION,
    Created,
    BeforeModified,
    AfterModified,
)
from .resources import (
    Collection,
    Item,
)
from .validation import ValidationFailure
from .validators import (
    no_validate_item_content_patch,
    no_validate_item_content_post,
    no_validate_item_content_put,
    validate_item_content_patch,
    validate_item_content_post,
    validate_item_content_put,
)

from snovault.feature_flags import try_to_get_feature_flag_value_or_default


def includeme(config):
    config.scan(__name__, categories=None)


def split_child_props(type_info, properties):
    propname_children = {}
    item_properties = properties.copy()
    if type_info.schema_rev_links:
        for key, spec in type_info.schema_rev_links.items():
            if key in item_properties:
                propname_children[key] = item_properties.pop(key)
    return item_properties, propname_children


def ensure_child_link(props, type_info, link_attr, uuid):
    if type_info.schema['properties'][link_attr]['type'] == 'array':
        if link_attr not in props:
            props[link_attr] = uuid
        elif uuid not in props:
            props[link_attr].append(uuid)
    else:
        props[link_attr] = uuid


def update_children(context, request, propname_children):
    registry = request.registry
    conn = registry[CONNECTION]
    collections = registry[COLLECTIONS]
    schema_rev_links = context.type_info.schema_rev_links
    uuid = str(context.uuid)

    for propname, children in propname_children.items():
        link_type, link_attr = schema_rev_links[propname]
        found = set()

        # Add or update children included in properties
        for i, child_props in enumerate(children):
            if isinstance(child_props, basestring):  # IRI of (existing) child
                child = find_resource(collections[link_type], child_props)
            else:
                child_props = child_props.copy()
                child_type = child_props.pop('@type', None)
                if 'uuid' in child_props:  # update existing child
                    child_id = child_props.pop('uuid')
                    child = conn.get_by_uuid(child_id)
                    if not request.has_permission('edit', child):
                        msg = u'edit forbidden to %s' % request.resource_path(child)
                        raise ValidationFailure('body', [propname, i], msg)
                    ensure_child_link(
                        child_props, child.type_info, link_attr, uuid)
                    try:
                        update_item(child, request, child_props)
                    except ValidationFailure as e:
                        e.location = [propname, i] + e.location
                        raise
                else:  # add new child
                    child_type = child_type[0]
                    child_collection = collections[child_type]
                    ensure_child_link(
                        child_props, child_collection.type_info,
                        link_attr, uuid)
                    if not request.has_permission('add', child_collection):
                        msg = u'add forbidden to %s' % request.resource_path(child_collection)
                        raise ValidationFailure('body', [propname, i], msg)
                    child = create_item(child_collection.type_info, request, child_props)
            found.add(child.uuid)

        # Remove existing children that are not in properties
        for link_uuid in context.get_rev_links(propname):
            if link_uuid in found:
                continue
            child = conn.get_by_uuid(link_uuid)
            if not request.has_permission('visible_for_edit', child):
                continue
            if not request.has_permission('edit', child):
                msg = u'edit forbidden to %s' % request.resource_path(child)
                raise ValidationFailure('body', [propname, i], msg)
            try:
                delete_item(child, request)
            except ValidationFailure as e:
                e.location = [propname, i] + e.location
                raise


def create_item(type_info, request, properties, sheets=None):
    registry = request.registry
    item_properties, propname_children = split_child_props(type_info, properties)

    if 'uuid' in item_properties:
        uuid = UUID(item_properties.pop('uuid'))
    else:
        uuid = uuid4()

    item = type_info.factory.create(registry, uuid, item_properties, sheets)
    registry.notify(Created(item, request))

    if propname_children:
        update_children(item, request, propname_children)
    return item


def update_item(context, request, properties, sheets=None):
    registry = request.registry
    item_properties, propname_children = split_child_props(context.type_info, properties)

    registry.notify(BeforeModified(context, request))
    context.update(item_properties, sheets)
    registry.notify(AfterModified(context, request))

    if propname_children:
        update_children(context, request, propname_children)


def delete_item(context, request):
    properties = context.properties.copy()
    properties['status'] = 'deleted'
    update_item(context, request, properties)


def maybe_block_database_writes(view_callable):
    @wraps(view_callable)
    def wrapper(context, request, *args, **kwargs):
        block_flag = try_to_get_feature_flag_value_or_default(
            request=request,
            flag='block_database_writes',
            default=False
        )
        if block_flag in ['true', 'True', '1', True]:
            raise HTTPServiceUnavailable(
                'Database writes are temporarily blocked.'
            )
        return view_callable(context, request, *args, **kwargs)
    return wrapper


@view_config(context=Collection, permission='add', request_method='POST',
             validators=[validate_item_content_post])
@view_config(context=Collection, permission='add_unvalidated', request_method='POST',
             validators=[no_validate_item_content_post],
             request_param=['validate=false'])
@maybe_block_database_writes
def collection_add(context, request, render=None):
    if render is None:
        render = request.params.get('render', True)

    item = create_item(context.type_info, request, request.validated)

    if render == 'uuid':
        item_uri = '/%s/' % item.uuid
    else:
        item_uri = request.resource_path(item)
    if asbool(render) is True:
        rendered = request.embed(item_uri, '@@object', as_user=True)
    else:
        rendered = item_uri
    request.response.status = 201
    request.response.location = item_uri
    result = {
        'status': 'success',
        '@type': ['result'],
        '@graph': [rendered],
    }
    return result


@view_config(context=Item, permission='edit', request_method='PUT',
             validators=[validate_item_content_put], decorator=if_match_tid)
@view_config(context=Item, permission='edit', request_method='PATCH',
             validators=[validate_item_content_patch], decorator=if_match_tid)
@view_config(context=Item, permission='edit_unvalidated', request_method='PUT',
             validators=[no_validate_item_content_put],
             request_param=['validate=false'], decorator=if_match_tid)
@view_config(context=Item, permission='edit_unvalidated', request_method='PATCH',
             validators=[no_validate_item_content_patch],
             request_param=['validate=false'], decorator=if_match_tid)
@maybe_block_database_writes
def item_edit(context, request, render=None):
    """ This handles both PUT and PATCH, difference is the validator

    PUT - replaces the current properties with the new body
    PATCH - updates the current properties with those supplied.
    """
    if render is None:
        render = request.params.get('render', True)

    # This *sets* the property sheet
    update_item(context, request, request.validated)

    if render == 'uuid':
        item_uri = '/%s' % context.uuid
    else:
        item_uri = request.resource_path(context)
    if asbool(render) is True:
        rendered = request.embed(item_uri, '@@object', as_user=True)
    else:
        rendered = item_uri
    request.response.status = 200
    result = {
        'status': 'success',
        '@type': ['result'],
        '@graph': [rendered],
    }
    return result
