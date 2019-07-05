from pyramid.view import view_config

from snovault.elasticsearch.searches.responses import FieldedResponse
from snovault.elasticsearch.searches.fields import BasicSearchWithFacetsResponseField
from snovault.elasticsearch.searches.parsers import ParamsParser


def includeme(config):
    config.add_route('searchv2', '/searchv2{slash:/?}')
    config.scan(__name__)


DEFAULT_ITEM_TYPES = [
    'Lab',
    'Snowset',
    'Snowball',
    'Snowfort',
    'Snowflake',
]


@view_config(route_name='searchv2', request_method='GET', permission='search')
def searchv2(context, request):
    fr = FieldedResponse(
        response_fields=[
            BasicSearchWithFacetsResponseField(
                params_parser=ParamsParser(request),
                default_item_types=DEFAULT_ITEM_TYPES
            )
        ]
    )
    return fr.render()
