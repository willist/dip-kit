import sqlalchemy
import sqlalchemy.orm

from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class RelationalEngineMixin(object):
    def get_relational_engine(self):
        if hasattr(self, 'relational_engine'):
            return self.relational_engine
        config_key = 'SQLALCHEMY_DATABASE_URI'
        self.require_config_key(config_key)
        engine = sqlalchemy.create_engine(self.config[config_key])
        self.relational_engine = engine
        return self.relational_engine

    def get_relational_sessionmaker(self):
        if hasattr(self, 'relational_sessionmaker'):
            return self.relational_sessionmaker
        Session = sqlalchemy.orm.sessionmaker(self.get_relational_engine())
        self.relational_sessionmaker = Session
        return self.relational_sessionmaker


class RelationalQueryMixin(object):
    def get_relational_session(self):
        if hasattr(self, 'relational_session'):
            return self.relational_session
        Session = self.get_relational_sessionmaker()
        self.relational_session = Session()
        return self.relational_session

    def close_relational_session(self):
        if not hasattr(self, 'relational_session'):
            return
        self.relational_session.close()

    def get_relational_query(self):
        session = self.get_relational_session()
        return session.query
