import json
import uuid

from datetime import datetime

import jeni

from sqlalchemy import Column, ForeignKey, TypeDecorator, TEXT
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import relationship

from .provider import RequestProvider
from .relational import Base
from .user import User


def uid_factory():
    return str(uuid.uuid4())


class JsonData(TypeDecorator):
    """Store arbitrary data as a json-encoded string."""
    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value


class Session(Base):
    """A login session keyed by uuid, distinct from web session."""
    __tablename__ = 'session'

    id = Column(Integer, primary_key=True)
    uid = Column(String(36), default=uid_factory)
    created = Column(DateTime, default=datetime.now)
    modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    data = Column(JsonData, nullable=True)

    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    user = relationship(User, lazy='joined', join_depth=1, viewonly=True)


@RequestProvider.annotate('relational_session')
def start_session(db, user, cls=Session):
    session = cls(user_id=user.id)
    db.add(session)
    db.flush()
    session.data = {'uid': session.uid}
    return session


@RequestProvider.annotate('relational_query', 'session:session_uid')
def end_session(query, session_uid, cls=Session):
    rowcount = query(cls).filter_by(uid=session_uid).delete()
    if rowcount == 0:
        raise ValueError('No session records for {}.'.format(session_uid))
    return rowcount


class SessionMixin(object):
    @RequestProvider.annotate('relational_query')
    def load_session(self, query, session_uid):
        session = query(Session).filter_by(uid=session_uid).first()
        if session is None:
            return jeni.UNSET
        return session.data

    @RequestProvider.annotate('relational_session', 'relational_query')
    def save_session(self, db, query, data):
        session = query(Session).filter_by(uid=data['uid']).first()
        if session is None:
            session = Session(uid=data['uid'])
            db.add(session)
        session.data = data
        db.commit()

    def get_session(self, name=None):
        if not hasattr(self, 'session'):
            # TODO: Add request-persisted session via extensible hooks.
            # flask_session = flask.session._get_current_object()
            # session_uid = flask_session.get('session_uid')
            # load_session = self.partial(self.load_session)
            session_uid = None
            self.session = load_session(session_uid)
        if self.session is jeni.UNSET:
            return jeni.UNSET
        if name is not None:
            return self.session.get(name, jeni.UNSET)
        self.session_start = None
        return self.session

    def set_session(self, session):
        self.session = session

    def close_session(self):
        if not hasattr(self, 'session'):
            return

        # TODO: Add request-persisted session via extensible hooks.
        # flask_session = flask.session._get_current_object()
        # flask_session['session_uid'] = self.session['uid']

        # Persist session data in Session model's table.
        if self.session != getattr(self, 'session_start', None):
            save_session = self.partial(self.save_session)
            save_session(self.session)
