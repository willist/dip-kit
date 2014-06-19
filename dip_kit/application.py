import abc
import sys

import jeni
import werkzeug.exceptions
from werkzeug.routing import Map, Rule, Submount

from .exception import ApplicationException
from .exception import Redirect, NotFound, MethodNotAllowed


class Injector(jeni.Injector):
    "dip-kit namespace for registered providers"


class Application(object, metaclass=abc.ABCMeta):
    METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']
    injector_class = Injector

    def __init__(self, plans):
        self.url_map = Map()
        self.endpoints = {}
        self.plan_map = {}
        for plan in plans:
            rule_obj_list = []
            for rule, methods, fn in plan.iter_routes():
                if fn is not None:
                    endpoint = fn.__name__
                    self.plan_map[fn] = plan
                    self.endpoints[endpoint] = fn
                    rule_obj_list.append(
                        Rule(rule, endpoint=endpoint, methods=methods))
            if plan.has_prefix():
                self.url_map.add(Submount(plan.get_prefix(), rule_obj_list))
            else:
                for rule_obj in rule_obj_list:
                    self.url_map.add(rule_obj)
        self.url_adapter = self.url_map.bind(server_name='unused')
        self.setup(plans)

    @abc.abstractmethod
    def setup(self, plans):
        "Register self.handle_request for all routes."

    @abc.abstractmethod
    def prepare_request(self, injector_class, *a, **kw):
        "Per request: provide data to injector, return root_url, path, method."

    @abc.abstractmethod
    def get_implementation(self):
        "Return concrete application implementation, e.g. the WSGI app."

    @abc.abstractmethod
    def build_response_application_exception(self, exc):
        "Build a response for the given ApplicationException."

    def build_response(self, fn_result):
        return fn_result

    def build_response_handled_error(self, handled_error):
        return handled_error

    def build_response_unhandled_error(self, exc_type, exc_value, tb=None):
        self.raise_error(exc_type, exc_value, tb)

    def match(self, path, method):
        try:
            endpoint, arguments = self.url_adapter.match(path, method)
            return self.endpoints[endpoint], arguments
        except werkzeug.exceptions.NotFound:
            raise NotFound()
        except werkzeug.exceptions.MethodNotAllowed:
            raise MethodNotAllowed()
        except werkzeug.routing.RequestRedirect as request_redirect:
            unused_url = 'http://unused'
            url = request_redirect.new_url
            if url.startswith(unused_url):
                url = url[len(unused_url):] # Strip unused_url.
            raise Redirect(url)

    def handle_request(self, *a, **kw):
        try:
            class Injector(self.injector_class):
                "Injector namespace for this request."
            root_url, path, method = self.prepare_request(Injector, *a, **kw)
            fn, arguments = self.match(path, method)
            # TODO: Put arguments into Injector, as well as url_for.
            plan = self.plan_map[fn]
            # TODO: Apply plan injector registration.
            response = self.try_handle_request(Injector, fn, plan)
            if response is None:
                raise ValueError('Response is None.')
            return response
        except Redirect as redirect:
            url = redirect.location
            if url.startswith('/'):
                try:
                    root_url
                except NameError:
                    root_url = ''
                if root_url:
                    url = root_url + url.lstrip('/')
            # else: trust that url is already full location.
            redirect.location = url
            return self.build_response_application_exception(redirect)
        except ApplicationException as exc:
            return self.build_response_application_exception(exc)
        except Exception:
            return self.build_response_unhandled_error(*sys.exc_info())

    def try_handle_request(self, injector_class, fn, plan):
        with injector_class() as injector:
            try:
                # TODO: Flatten calls if jeni gets .apply buff.
                for handler in plan.iter_before_request_handlers():
                    if injector.has_annotations(handler):
                        injector.apply(handler)
                    else:
                        handler()
                if injector.has_annotations(fn):
                    result = injector.apply(fn)
                else:
                    result = fn()
                for handler in plan.iter_after_request_handlers():
                    if injector.has_annotations(handler):
                        fn = injector.partial(handler)
                    else:
                        fn = handler
                    fn(result)
            except Exception as error:
                try:
                    handled = self.handle_error(injector, plan, error)
                    return self.build_response_handled_error(handled)
                except Exception:
                    # Error may have been re-raised, but not necessarily.
                    return self.build_response_unhandled_error(*sys.exc_info())
            else:
                return self.build_response(result)

    def handle_error(self, injector, plan, error):
        exc_type, exc_value, tb = sys.exc_info()
        assert exc_value is error
        for error_type, handler in plan.iter_errorhandlers():
            if isinstance(error, error_type):
                if injector.has_annotations(handler):
                    fn = injector.partial(handler)
                else:
                    fn = handler
                return fn(error)
        self.raise_error(exc_type, exc_value, tb)

    def raise_error(self, exc_type, exc_value, tb=None):
        if exc_value.__traceback__ is not tb:
            raise exc_value.with_traceback(tb)
        raise exc_value
