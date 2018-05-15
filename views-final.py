import sys
import random
import string
import json
import requests

from flask import Flask
from flask import render_template, redirect, request, url_for, flash, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.pool import StaticPool

# Add CRUD operations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Topic, Article, User

from flask import session as login_session

# Add OAuth operations
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
from flask import make_response

app = Flask(__name__)

# Main page
@app.route('/')
@app.route('/topics/')
def showTopics():
    data = 'sqlite:////var/www/helper/helper/helperwithusers.db'
    engine = create_engine(data, connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    topics = session.query(Topic).order_by(Topic.name)
    session.close()
    return render_template('main.html', topics=topics)

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
