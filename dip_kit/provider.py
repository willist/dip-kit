import jeni

from werkzeug.datastructures import ImmutableDict

from .log import LoggerMixin
from .mail import MailerMixin
from .relational import RelationalEngineMixin, RelationalQueryMixin
from .render import RenderMixin


class ApplicationProvider(
        LoggerMixin,
        MailerMixin,
        RelationalEngineMixin,
        RelationalQueryMixin,
        RenderMixin,
        jeni.BaseProvider):

    def __init__(self, builder=None, app=None):
        self.builder = builder
        self.app = app
        if builder is not None:
            self.buildout(builder)

    @property
    def config(self):
        if self.builder is None:
            return ImmutableDict()
        return self.builder.config

    def require_config_key(self, key, config=None):
        """Methods requiring config should use this. Raises KeyError."""
        if config is None:
            config = self.config
        if key not in config:
            msg = '{} is missing in ApplicationProvider config'.format(key)
            raise KeyError(msg)

    def build_app(self, config):
        raise NotImplementedError('Implement app in subclass.')

    def buildout(self, builder):
        raise NotImplementedError("Implement Builder's buildout in subclass.")

    def get_app(self):
        if self.app is None:
            self.app = self.build_app(self.config)
        return self.app

    def get_config(self, name=None):
        if name is not None:
            return self.config.get(name, jeni.UNSET)
        return self.config


class RequestProvider(RelationalQueryMixin, jeni.BaseProvider):
    def __init__(self, app_provider, request):
        self.request = request
        self.extend(app_provider)

    def get_user(self):
        raise NotImplementedError('request user')

    def get_session(self, name=None):
        raise NotImplementedError('request session')

    def get_args(self, name=None):
        raise NotImplementedError('request args')

    def get_form(self, name=None):
        raise NotImplementedError('request form')

    def get_headers(self, name=None):
        raise NotImplementedError('request headers')
