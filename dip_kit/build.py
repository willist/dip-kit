"""Register hooks for the application."""

import os

from .provider import ApplicationProvider


class Builder(object):
    # TODO: Add hooks for add_url_rule, before_/after_request, errorhandler.

    def __init__(self, config=None, app_provider_class=None):
        if app_provider_class is None:
            self.app_provider_class = ApplicationProvider
        else:
            self.app_provider_class = app_provider_class

        self.config = {}
        if config is not None:
            self.config.update(config)
        self.routes = {}

    def build_application_provider(self):
        return self.app_provider_class(builder=self)

    def route(self, rule, methods=None, method=None):
        if method is not None:
            methods = [method]
        elif methods is None:
            methods = ['GET']

        def decorator(fn, methods=methods):
            self.routes[rule] = (fn, methods)
            return fn

        return decorator
