"""Flask Kit: a jeni-based dependency injection implementation using Flask.

Usage:
  flask-kit call [-c COOKIE_JAR] [-d FORMDATA...] [-H HEADER...] BUILDER ROUTE
  flask-kit runserver [--host=HOST] [--port=PORT] [--no-debug] BUILDER
  flask-kit shell BUILDER
  flask-kit wsgi BUILDER

Commands:
  call       Directly call the handler at a given route (non-HTTP/non-WSGI).
  runserver  Run the Flask development server, i.e. app.run(...).
  shell      Run a Python interactive interpreter inside Flask app context.
  wsgi       Generate WSGI script to stdout for direct use with e.g. gunicorn.
             `flask-kit wsgi BUILDER > wsgi.py && gunicorn wsgi:app`

Arguments:
  BUILDER  Dotted path MODULE_NAME:VARIABLE_NAME referencing Builder instance.
  ROUTE    URL-like path to route of handler to call, starting with '/'.

Options:
  -h --help                              Show this help message, then exit.
  -c COOKIE_JAR --cookie-jar=COOKIE_JAR  Write cookies to this file.
  -d FORMDATA --data=FORMDATA            Set form key/value like HTTP POST.
  -H HEADER --header HEADER              Set HTTP-style header line.
  -t HOST --host=HOST                    Host address for TCP bind.
  -p PORT --port=PORT                    Port for TCP bind.
  --no-debug                             Disable debug mode.
"""

from __future__ import print_function

import code
import importlib
import re

# TODO: Establish a cookie jar or flatfile alternative for `call` sessions.
# try:
#     from http.cookiejar import FileCookieJar
# except ImportError:
#     from cookielib import FileCookieJar

import jeni

from docopt import docopt

from dip_kit.provider import ApplicationProvider, RequestProvider
from dip_kit.session import SessionMixin
from dip_kit.user import UserMixin


class CommandRequestProvider(SessionMixin, UserMixin, RequestProvider):
    # TODO: Implement non-Flask request provider using command-line arguments.
    # TODO: Set 'Accept: text/plain' header.
    pass


class CommandApplicationProvider(ApplicationProvider):
    # TODO: Implement non-Flask provider using command-line arguments.
    def buildout(self, builder):
        pass


class DocoptProvider(jeni.BaseProvider):
    accessor_re = re.compile(r'^get_(.*)')
    app_provider_class = CommandApplicationProvider

    def __init__(self, arguments):
        self.arguments = arguments

    def dispatch(self):
        arguments = self.arguments
        if arguments['call'] is True:
            self.apply(call)
        elif arguments['runserver'] is True:
            self.apply(runserver)
        elif arguments['shell'] is True:
            self.apply(shell)
        elif arguments['wsgi'] is True:
            self.apply(wsgi)
        else:
            raise ValueError('No command found in arguments.')

    def load_builder(self):
        if hasattr(self, 'builder'):
            return self.builder
        builder = self.get_builder()
        if ':' not in builder:
            msg = 'BUILDER does not include variable name: {}'.format(builder)
            raise ValueError(msg)
        modname, varname = builder.split(':', 1)
        module = importlib.import_module(modname)
        return getattr(module, varname)

    def get_app_provider(self):
        if hasattr(self, 'app_provider'):
            return self.app_provider
        self.app_provider = self.app_provider_class(self.load_builder())
        return self.app_provider

    def get_flask_app_provider(self):
        from flask_kit.web import FlaskApplicationProvider
        if hasattr(self, 'flask_app_provider'):
            return self.flask_app_provider
        self.flask_app_provider = FlaskApplicationProvider(self.load_builder())
        return self.flask_app_provider

    def build_accessor(self, argument):
        arguments = self.arguments
        optname = '--{}'.format(argument.replace('_', '-'))
        if argument in arguments:
            # Argument is a command boolean.
            value = arguments[argument]
        elif argument.upper() in arguments:
            # Argument is a positional argument.
            value = arguments[argument.upper()]
        elif optname in arguments:
            # Argument is an option flag.
            value = arguments[optname]
            if value is None:
                value = jeni.UNSET
        def accessor(value=value):
            return value
        return accessor

    def __getattr__(self, name):
        cls = jeni.BaseProvider
        if name in dir(self):
            # Attribute is defined on self.
            return cls.__getattr__(self, name)
        match = self.accessor_re.search(name)
        if match is None:
            # Do not attempt to build accessor.
            return cls.__getattr__(self, name)
        return self.build_accessor(match.group(1))


@DocoptProvider.annotate(
    'app_provider',
    'route',
    cookie_jar='cookie_jar',
    data='data',
    headers='header')
def call(app_provider, route, cookie_jar=None, data=None, headers=None):
    # TODO: Implement direct call from command line.
    print(app_provider)
    pass


@DocoptProvider.annotate(
    'flask_app_provider',
    host='host',
    port='port',
    no_debug='no_debug')
def runserver(flask_app_provider, host=None, port=None, no_debug=None):
    if no_debug is None:
        debug = None
    else:
        debug = not no_debug
    if port is not None:
        port = int(port)
    app = flask_app_provider.get_app()
    app.run(host=host, port=port, debug=debug)


@DocoptProvider.annotate('flask_app_provider')
def shell(app_provider):
    with app_provider:
        app = app_provider.get_app()
        with app.test_request_context():
            with app_provider.build_request_provider() as provider:
                code.interact(local=locals())


@DocoptProvider.annotate('builder')
def wsgi(path, file=None):
    if ':' not in path:
        msg = 'BUILDER does not include variable name: {}'.format(path)
        raise ValueError(msg)
    script = (
        "# WSGI script generated by {version_string}.\n"
        "\n"
        "import importlib\n"
        "\n"
        "from flask_kit import FlaskApplicationProvider\n"
        "\n"
        "\n"
        "builder_name = '{builder_name}'\n"
        "modname, varname = builder_name.split(':', 1)\n"
        "module = importlib.import_module(modname)\n"
        "builder = getattr(module, varname)\n"
        "app_provider = FlaskApplicationProvider(builder)\n"
        "app = app_provider.get_wsgi()").format(
            builder_name=path,
            version_string=build_version_string())
    if file is None:
        print(script, flush=True)
    else:
        print(script, file=file, flush=True)


def build_version_string(version=None):
    from flask_kit import __version__
    if version is None:
        version = __version__
    return 'flask-kit {}'.format(__version__)


def main(argv=None):
    import sys
    if argv is None:
        argv = sys.argv[1:]
    version = build_version_string()
    DocoptProvider(docopt(__doc__, argv=argv, version=version)).dispatch()
