from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import synonym
from werkzeug import check_password_hash, generate_password_hash

from .relational import Base
from .provider import RequestProvider

# TODO: Consider a non-Werkzeug password hash.


class User(Base):
    """A user login, with credentials and authentication."""
    # TODO: Make table name configurable.
    __tablename__ = 'dip_user'

    id = Column(Integer, primary_key=True)
    created = Column(DateTime, default=datetime.now)
    modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    name = Column('name', String(200))
    email = Column(String(100), unique=True, nullable=False)
    active = Column(Boolean, default=True)

    _password = Column('password', String(100))

    def _get_password(self):
        return self._password

    def _set_password(self, password):
        if password:
            password = password.strip()
        self._password = generate_password_hash(password)

    password_descriptor = property(_get_password, _set_password)
    password = synonym('_password', descriptor=password_descriptor)

    def check_password(self, password):
        if self.password is None:
            return False
        password = password.strip()
        if not password:
            return False
        return check_password_hash(self.password, password)

    @classmethod
    def authenticate(cls, query, email, password):
        email = email.strip().lower()
        user = query(cls).filter(cls.email==email).first()
        if user is None:
            return None, False
        if not user.active:
            return user, False
        return user, user.check_password(password)


class UserMixin(object):
    @RequestProvider.annotate('relational_query', user_id='session:user_id')
    def load_user(self, query, user_id=None):
        if user_id is None:
            return None
        return query(User).get(user_id)

    def get_user(self):
        if hasattr(self, 'user'):
            return self.user
        self.user = self.apply(self.load_user)
        return self.user
