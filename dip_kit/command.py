"""dip-kit: jeni-based dependency injection (dip) kit with common dependencies.

Usage:
  dip-kit call [-c COOKIE_JAR] [-d FORMDATA...] [-H HEADER...] BUILDER ROUTE
  dip-kit runserver [--host=HOST] [--port=PORT] [--no-debug] [-r] BUILDER
  dip-kit shell BUILDER
  dip-kit wsgi BUILDER

Commands:
  call       Directly call the handler at a given route (non-HTTP/non-WSGI).
  runserver  Run a development WSGI server with code-reloading & debugger.
  shell      Run Python interactive interpreter with a request provider.
  wsgi       Generate WSGI script to stdout for direct use with e.g. gunicorn.
             `dip-kit wsgi BUILDER > wsgi.py && gunicorn wsgi:app`

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
  -r --no-reload                         Disable code reloading.
"""

from __future__ import print_function

import code
import importlib
import re
import sys

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


DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8000


class CommandRequestProvider(SessionMixin, UserMixin, RequestProvider):
    # TODO: Implement non-web request provider using command-line arguments.
    # TODO: Set 'Accept: text/plain' header.
    pass


class CommandApplicationProvider(ApplicationProvider):
    # TODO: Implement non-web provider using command-line arguments.
    def buildout(self, builder):
        pass


class DocoptProvider(jeni.BaseProvider):
    accessor_re = re.compile(r'^get_(.*)')

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
        self.builder = getattr(module, varname)
        return self.builder

    def get_app_provider(self):
        if hasattr(self, 'app_provider'):
            return self.app_provider
        builder = self.load_builder()
        self.app_provider = builder.build_provider()
        return self.app_provider

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
        else:
            return None
        def accessor(value=value):
            return value
        return accessor

    def __getattr__(self, name):
        try:
            return jeni.BaseProvider.__getattr__(self, name)
        except AttributeError:
            match = self.accessor_re.search(name)
            if match is None:
                # Do not attempt to build accessor.
                return object.__getattribute__(self, name)
            accessor = self.build_accessor(match.group(1))
            if accessor is not None:
                return accessor
            return object.__getattribute__(self, name)


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
    'app_provider',
    host='host',
    port='port',
    no_debug='no_debug',
    no_reload='no_reload')
def runserver(provider, host=None, port=None, no_debug=None, no_reload=None):
    try:
        from werkzeug.serving import run_simple
    except ImportError:
        msg = 'runserver command requires werkzeug: pip install werkzeug'
        print(msg, file=sys.stderr)
        sys.exit(1)

    options = {}

    if no_debug is not None:
        options['use_debugger'] = not no_debug
    if no_reload is not None:
        options['use_reloader'] = not no_reload

    if host is None:
        host = DEFAULT_HOST
    if port is None:
        port = DEFAULT_PORT
    else:
        port = int(port)

    app = provider.get_wsgi()
    run_simple(host, port, app, **options)


def load_rlcompleter(context=None):
    try:
        import readline
    except ImportError:
        return False
    import rlcompleter
    if context is None:
        completer = rlcompleter.Completer()
    else:
        completer = rlcompleter.Completer(context)
    readline.set_completer(completer.complete)
    readline.parse_and_bind("tab: complete")
    return True


@DocoptProvider.annotate('app_provider')
def shell(app_provider, use_rlcompleter=True):
    with app_provider:
        app = app_provider.get_app()
        with app_provider.build_request_provider() as provider:
            context = locals()
            if use_rlcompleter:
                load_rlcompleter(context)
            code.interact(local=context)


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
        "\n"
        "builder_name = '{builder_name}'\n"
        "modname, varname = builder_name.split(':', 1)\n"
        "module = importlib.import_module(modname)\n"
        "builder = getattr(module, varname)\n"
        "app = builder.build_provider().get_wsgi()").format(
            builder_name=path,
            version_string=build_version_string())
    if file is None:
        print(script)
    else:
        print(script, file=file)
        file.flush()


def build_version_string(version=None):
    from dip_kit import __version__
    if version is None:
        version = __version__
    return 'dip-kit {}'.format(__version__)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    version = build_version_string()
    DocoptProvider(docopt(__doc__, argv=argv, version=version)).dispatch()


if __name__ == '__main__':
    main()
