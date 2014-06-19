======================================================================
 dip-kit provides an Application abstraction for dependency injection
======================================================================

Unstable.

dip-kit defines an `Application` class, tools for planning and running
`Application` instances, and provides injection of dependencies across
`Application` implementations. The `Application` class assumes a
request-response style interaction, but does not itself implement request
handling; this is left to concrete Application implementations.

1. Plan application functionality using builders.
2. Combine builders into crews if needed; crew configuration overrides builder.
3. Instantiate the Application for command-line, WSGI, or other service.

Based on `jeni <http://pypi.python.org/pypi/jeni>`_.
