"""Register hooks for the application."""

import os


class Builder(object):
    # TODO: Add hooks for add_url_rule, before_/after_request, errorhandler.

    def __init__(self, config=None):
        self.config = {}
        if config is not None:
            self.config.update(config)
        self.routes = {}

    def route(self, rule, methods=None, method=None):
        if method is not None:
            methods = [method]
        elif methods is None:
            methods = ['GET']

        def decorator(fn, methods=methods):
            self.routes[rule] = (fn, methods)
            return fn

        return decorator
