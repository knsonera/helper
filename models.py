import random
import string
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import(TimedJSONWebSignatureSerializer as Serializer,
                         BadSignature, SignatureExpired)


Base = declarative_base()

secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits)
                     for x in xrange(32))


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'email': self.email,
            'picture': self.picture,
            'id': self.id,
        }


class Topic(Base):
    __tablename__ = 'topic'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
        }


class Article(Base):
    __tablename__ = 'article'

    title = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(500))
    link = Column(String(250))
    topic_id = Column(Integer, ForeignKey('topic.id'))
    topic = relationship(Topic)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'link': self.link,
        }


engine = create_engine('sqlite:///helperwithusers.db')

Base.metadata.create_all(engine)
