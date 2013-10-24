"""Register hooks for the application."""

import sys

from threading import Lock

from .provider import ApplicationProvider


class Builder(object):
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

        # Heavily Flask-inspired, but not Flask.
        self._got_first_request = False
        self.before_request_fns = []
        self.before_first_request_fns = []
        self.before_first_request_lock = Lock()
        self.after_request_fns = []
        self.errorhandlers = {}

    def build_provider(self, provider_class=None):
        if provider_class is None:
            provider_class = self.provider_class
        return provider_class(builder=self)

    def determine_methods(self, methods=None, method=None):
        if method is not None:
            return [method]
        return ['GET']

    def add_url_rule(self, rule, fn=None, methods=None, method=None):
        methods = self.determine_methods(methods=methods, method=method)
        self.routes[rule] = (fn, methods)

    def route(self, rule, methods=None, method=None):
        methods = self.determine_methods(methods=methods, method=method)

        def decorator(fn, methods=methods):
            self.routes[rule] = (fn, methods)
            return fn

        return decorator

    def errorhandler(self, exception):
        def decorator(fn):
            self.errorhandlers[exception] = fn
            return fn
        return decorator

    def handle_error(self, provider, error):
        exc_type, exc_value, tb = sys.exc_info()
        assert exc_value is error
        for typecheck, handler in self.errorhandlers.items():
            if isinstance(error, typecheck):
                return handler(provider, error)
        raise exc_type, exc_value, tb

    def before_request(self, fn):
        self.before_request_fns.append(fn)

    def before_first_request(self, fn):
        self.before_first_request_fns.append(fn)

    def handle_before_request(self, provider):
        if not self._got_first_request:
            with self.before_first_request_lock:
                if not self._got_first_request:
                    self._got_first_request = True
                    for fn in self.before_first_request_fns:
                        fn(provider)
        for fn in self.before_request_fns:
            fn(provider)

    def after_request(self, fn):
        self.after_request_fns.append(fn)

    def handle_after_request(self, provider):
        for fn in self.after_request_fns:
            fn(provider)
