import flask
import jeni
import werkzeug

from dip_kit.provider import ApplicationProvider, RequestProvider
from dip_kit.session import SessionMixin
from dip_kit.user import UserMixin
from dip_kit.wsgi import WsgiMixin


class FlaskRequestProvider(SessionMixin, UserMixin, RequestProvider):
    def get_args(self, name=None):
        if name is not None:
            if name in self.request.view_args:
                return self.request.view_args[name]
            if name in self.request.args:
                return self.request.args[name]
            return jeni.UNSET
        args = werkzeug.datastructures.MultiDict()
        args.update(self.request.args)
        args.update(self.request.view_args)
        return args

    def get_form(self, name=None):
        if name is not None:
            return self.request.form.get(name, jeni.UNSET)
        return self.request.form

    def get_headers(self, name=None):
        if name is not None:
            return self.request.headers.get(name, jeni.UNSET)
        headers = werkzeug.datastructures.MultiDict()
        headers.update(self.request.headers)
        return headers


class FlaskApplicationProvider(WsgiMixin, ApplicationProvider):
    request_provider_class = FlaskRequestProvider

    def build_app(self, config):
        self.require_config_key('SECRET_KEY')
        template_folder = config.get('TEMPLATE_FOLDER', None)
        app = flask.Flask(__name__, template_folder=template_folder)
        app.config.update(config)
        return app

    def buildout(self, builder):
        # TODO: Accept a builder for URL registration only.
        # TODO: Add url_for as a dependency.
        app = self.get_app()
        self.endpoints = {}
        for rule in builder.routes:
            fn, methods = builder.routes[rule]
            endpoint = fn.__name__
            self.endpoints[endpoint] = fn
            app.add_url_rule(
                rule,
                endpoint,
                self.handle_request,
                methods=methods)

    def handle_request(self, *a, **kw):
        request = flask.request._get_current_object()
        fn = self.endpoints[request.endpoint]
        with self.build_request_provider(request) as provider:
            return fn(provider)

    def build_request_provider(self, request=None):
        if request is None:
            request = flask.request._get_current_object()
        return self.request_provider_class(self, request)

    def get_test_client(self, *a, **kw):
        return self.get_app().test_client(*a, **kw)
