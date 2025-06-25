# Manually specify dependencies on an audit or calculated property
# that should be included in mapping hash calculation.
def watch_for_changes_in(*, functions, version=None):
    def decorator(func):
        if not hasattr(func, '__watch_for_changes_in__'):
            func.__watch_for_changes_in__ = {
                'functions': [],
                'version': None
            }
        func.__watch_for_changes_in__['functions'].extend(functions)
        func.__watch_for_changes_in__['version'] = version
        return func
    return decorator
