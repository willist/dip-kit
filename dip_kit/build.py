"""Register hooks for the application."""

from .provider import ApplicationProvider


class Builder(object):
    # TODO: Add hooks for add_url_rule, before_/after_request, errorhandler.

    default_provider_class = ApplicationProvider

    def __init__(self, config=None, provider_class=None):
        if provider_class is None:
            self.provider_class = self.default_provider_class
        else:
            self.provider_class = provider_class

        self.config = {}
        if config is not None:
            self.config.update(config)
        self.routes = {}

    def build_provider(self, provider_class=None):
        if provider_class is None:
            provider_class = self.provider_class
        return provider_class(builder=self)

    def route(self, rule, methods=None, method=None):
        if method is not None:
            methods = [method]
        elif methods is None:
            methods = ['GET']

        def decorator(fn, methods=methods):
            self.routes[rule] = (fn, methods)
            return fn

        return decorator
