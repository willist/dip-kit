import pprint

from flask_kit import Builder, FlaskApplicationProvider
from flask_kit import ApplicationProvider, RequestProvider
from flask_kit.render import relative_folder
from flask_kit.session import start_session
from flask_kit.user import User


builder = Builder()

@builder.route('/foo/<int:object_id>/')
def dispatch_foo(provider):
    return pprint.pformat(provider.apply(foo))

@RequestProvider.annotate(
    'user',
    'session',
    'args',
    'args:object_id',
    'form',
    'headers',
    'headers:Host',
    'config',
    'relational_engine',
    'relational_session',
    'relational_query',
    'render',
    'logger',
    'mailer',
    q='args:q')
def foo(*args, **kwargs):
    return args, kwargs


@builder.route('/login/')
def login(provider):
    login = provider.partial(start_session)
    query = provider.get_relational_query()
    user = query(User).first()
    session_record = login(user)
    session_record.data['spam'] = 'eggs'
    provider.get_relational_session().commit()
    provider.set_session(session_record.data)
    return 'You are user {}.'.format(user.id)


@builder.route('/session/set/')
def dispatch_session_set(provider):
    return pprint.pformat(provider.apply(session_set))


@RequestProvider.annotate('session', 'args')
def session_set(session, args):
    session.update(args.to_dict())
    return args


config = {
    'DEBUG': True,
    'SECRET_KEY': 'secret',
    'SQLALCHEMY_DATABASE_URI': 'sqlite://',
    'TEMPLATE_FOLDER': relative_folder(__file__),
}
builder.config.update(config)


if __name__ == '__main__':
    from flask_kit.relational import Base

    @ApplicationProvider.annotate('relational_engine')
    def create_tables(engine):
        Base.metadata.create_all(engine)

    app_provider = FlaskApplicationProvider(builder)
    app_provider.apply(create_tables)

    @ApplicationProvider.annotate('relational_session', 'relational_query')
    def create_user(db, query, commit=True):
        if query(User).count() > 0:
            return query(User).first()
        user = User(
            name='Example User',
            email='you@example.org',
            password='secret')
        db.add(user)
        if commit:
            db.commit()
        return user

    user = app_provider.apply(create_user)
    client = app_provider.get_test_client()

    def get(path, client=client):
        return client.get(path).data.decode('utf-8').strip()

    print(get('/login/'))
    print(get('/session/set/?one=1&two=2&three=3'))
    print(get('/foo/42/?q=bar'))

    import jeni

    class FakeProvider(jeni.BaseProvider):
        def __init__(self, provider_class):
            self.implement(provider_class)

        def __getattr__(self, name):
            if name.startswith('get_'):
                return lambda *a, **kw: name.replace('get_', '')
            return object.__getattribute__(self, name)

    fake_provider = FakeProvider(RequestProvider)
    pprint.pprint(fake_provider.apply(foo))
