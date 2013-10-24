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


class SessionModelMixin(object):
    """A login session keyed by uuid, distinct from web session."""
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(36), default=uid_factory, index=True)
    created = Column(DateTime, default=datetime.now)
    modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    data_modified = Column(DateTime, default=datetime.now)
    data = Column(JsonData, nullable=True)

    @classmethod
    @RequestProvider.annotate('relational_session')
    def start(cls, db, owner):
        session = cls()
        session.set_owner(owner)
        db.add(session)
        db.flush()
        session.data = {'uid': session.uid}
        return session

    @classmethod
    @RequestProvider.annotate('relational_query', 'session:uid')
    def end(cls, query, session_uid):
        rowcount = query(cls).filter_by(uid=session_uid).delete()
        if rowcount == 0:
            raise ValueError('No session records for {}.'.format(session_uid))
        return session_uid

    def set_owner(self, owner):
        raise NotImplementedError('Provide relationship setter in subclass.')


class Session(SessionModelMixin, Base):
    __tablename__ = 'dip_session'

    user_id = Column(Integer, ForeignKey(User.id), nullable=False, index=True)
    user = relationship(User, lazy='joined', join_depth=1, viewonly=True)

    def set_owner(self, owner):
        self.user_id = owner.id


class SessionMixin(object):
    def get_session_model(self):
        return Session

    @RequestProvider.annotate('relational_query')
    def load_session_record(self, query, session_uid):
        Session = self.get_session_model()
        session_record = query(Session).filter_by(uid=session_uid).first()
        if session_record is None:
            return jeni.UNSET
        return session_record

    @RequestProvider.annotate('relational_session', 'relational_query')
    def save_session(self, db, query, data):
        Session = self.get_session_model()
        session_record = query(Session).filter_by(uid=data['uid']).first()
        if session_record is None:
            session_record = Session(uid=data['uid'])
            db.add(session_record)
        session_record.data = data
        session_record.data_modified = datetime.now()
        db.commit()

    def get_session_uid(self):
        raise NotImplementedError('Get persisted session uid via application.')

    def set_session_uid(self, session_uid):
        raise NotImplementedError('Persist session uid via application.')

    def get_session(self, name=None):
        if not hasattr(self, 'session'):
            session_uid = self.get_session_uid()
            load_session_record = self.partial(self.load_session_record)
            self.session_record = load_session_record(session_uid)
            if self.session_record is jeni.UNSET:
                self.session = jeni.UNSET
            else:
                self.session = self.session_record.data
                self.session_start = self.session
        if self.session is jeni.UNSET:
            return jeni.UNSET
        if name is not None:
            return self.session.get(name, jeni.UNSET)
        return self.session

    def get_session_record(self):
        if hasattr(self, 'session_record'):
            return self.session_record
        self.get_session()
        return self.session_record

    def set_session(self, session):
        self.session = session

    def clear_session(self):
        self.session = jeni.UNSET

    def close_session(self):
        if not hasattr(self, 'session'):
            self.set_session_uid(None)
            return

        if self.session is jeni.UNSET:
            self.set_session_uid(None)
            return

        # Persist session data in Session model's table.
        if self.session != getattr(self, 'session_start', None):
            save_session = self.partial(self.save_session)
            save_session(self.session)

        self.set_session_uid(self.session['uid'])
