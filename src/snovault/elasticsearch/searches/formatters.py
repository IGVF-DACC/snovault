
def get_aggregation_field():
    pass


def get_aggregation_title():
    pass


def get_aggregation_type():
    pass


def get_aggregation_results():
    pass


def get_aggregation_total():
    pass


def aggregation_is_appeneded():
    pass


def format_aggregation():
    return {
        FIELD: get_aggregation_field(),
        TITLE: get_aggregation_title(),
        TERMS: get_aggregation_results(),
        TOTAL: get_aggregation_total(),
        TYPE_KEY: get_aggregation_type(),
        APPENDED: aggregation_is_appeneded(),
    }


def format_aggregations():
    pass
