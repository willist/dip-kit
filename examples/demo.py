from dip_kit import Builder, Crew
from jeni import Injector as BaseInjector
from jeni import Provider, annotate


class Injector(BaseInjector):
    "Local namespace for injection."


@Injector.provider('hello')
class HelloProvider(Provider):
    def get(self, name=None):
        if name is None:
            name = 'world'
        return 'Hello, {}!'.format(name)


@Injector.factory('eggs')
def eggs():
    return 'eggs!'


builder = Builder()


@annotate
@builder.route('/')
def index(
        hello: 'hello',
        eggs: 'eggs'):
    return str((hello, eggs))


@builder.before_request
def before1():
    print('@builder.before_request')


@builder.route('/foo/')
def foo1():
    return "This is not the foo you're looking for."


other = Builder()


@annotate
@other.route('/other/')
def other_route(hello: 'hello:thing', eggs: 'eggs'):
    return str((hello, eggs))


@other.before_request
def before2():
    print('@other.before_request')


@other.route('/error/')
def error_route():
    raise Exception('Nope.')


crew = Crew(
    ('/', builder),
    ('/', other))


@crew.route('/foo/')
def foo0():
    return "This is the right foo."


@crew.before_request
def before3():
    print('@crew.before_request')


if __name__ == '__main__':
    # TODO: If dip-kit gets a reference implementation, use it here.
    from flask_kit import FlaskApplication
    class Application(FlaskApplication):
        injector_class = Injector
    application = crew.build_application(Application)
    application.app.run(debug=True)
