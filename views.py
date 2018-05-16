import sys
import random
import string
import json
import requests

from flask import Flask
from flask import render_template, redirect, request, url_for, flash, jsonify

# Add CRUD operations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Topic, Article, User

from flask import session as login_session
from sqlalchemy.pool import StaticPool
# Add OAuth operations
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
from flask import make_response

# Create session, connect to db

data = 'sqlite:////var/www/helper/helper/helperwithusers.db'
engine = create_engine(data, connect_args={'check_same_thread': False}, poolclass=StaticPool)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__, static_folder='static')

# Load client_id for google oauth
CLIENT_ID = json.loads(
    open('/var/www/helper/helper/client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "css overflow app"


# Main page
@app.route('/')
@app.route('/topics/')
def showTopics():
    topics = session.query(Topic).order_by(Topic.name)
    return render_template('topics.html', topics=topics)


# Create new topic
@app.route('/topics/new/', methods=['GET', 'POST'])
def newTopic():
    if 'username' not in login_session:
        return redirect('/login')
    user_id = getUserId(login_session['email'])
    if request.method == 'POST':
        newTopic = Topic(name=request.form['name'],
                         user_id=user_id)
        session.add(newTopic)
        session.commit()
        return redirect(url_for('showTopic', topic_id=newTopic.id))
    else:
        topics = session.query(Topic).order_by(Topic.name)
        return render_template('newTopic.html', topics=topics)


# Show all topics
@app.route('/topics/<int:topic_id>/')
def showTopic(topic_id):
    topic = session.query(Topic).filter_by(id=topic_id).one()
    topics = session.query(Topic).order_by(Topic.name)
    articles = session.query(Article).filter_by(topic_id=topic_id).all()
    if 'username' in login_session:
        if login_session['user_id'] == topic.user_id:
            return render_template('topic.html', topic=topic, topics=topics,
                                   articles=articles, topic_id=topic_id)
        else:
            # If user is not owner of the topic, hide edit and delete buttons
            return render_template('publicTopic.html', topic=topic,
                                   topics=topics, articles=articles,
                                   topic_id=topic_id)
    else:
        return render_template('publicTopic.html', topic=topic,
                                   topics=topics, articles=articles,
                                   topic_id=topic_id)


# Edit topic
@app.route('/topics/<int:topic_id>/edit/', methods=['GET', 'POST'])
def editTopic(topic_id):
    if 'username' not in login_session:
        return redirect('/login')
    edited_topic = session.query(Topic).filter_by(id=topic_id).one()
    topics = session.query(Topic).order_by(Topic.name)
    # Check if user is allowed to modify topic
    if login_session['user_id'] != edited_topic.user_id:
        return "<script>function myFunction() { \
                alert('You are not authorized to edit this topic. \
                You can only edit topics you created.');\
            }</script><body onload='myFunction()'>"

    if request.method == 'POST':
        if request.form['name']:
            edited_topic.name = request.form['name']
            session.add(edited_topic)
            session.commit()
            # TODO: flash messages if successful
            return redirect(url_for('showTopic', topic_id=edited_topic.id))
    else:
        return render_template('editTopic.html', topics=topics,
                               topic=edited_topic)


# Delete topic
@app.route('/topics/<int:topic_id>/delete/', methods=['GET', 'POST'])
def deleteTopic(topic_id):
    if 'username' not in login_session:
        return redirect('/login')
    topics = session.query(Topic).order_by(Topic.name)
    topic_to_delete = session.query(Topic).filter_by(id=topic_id).one()
    # Check if user is allowed to delete topic, show js alert
    if login_session['user_id'] != topic_to_delete.user_id:
        return "<script>function myFunction() {\
                alert('You are not authorized to delete this topic. \
                You can only delete topics you created.');\
            }</script><body onload='myFunction()'>"

    if request.method == 'POST':
        session.delete(topic_to_delete)
        session.commit()
        # TODO: flash on success?
        return redirect(url_for('showTopics'))
    else:
        return render_template('deleteTopic.html', topics=topics,
                               topic=topic_to_delete)


# Create new article
@app.route('/topics/<int:topic_id>/articles/new/', methods=['GET', 'POST'])
def newArticle(topic_id):
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        user_id = getUserId(login_session['email'])
        new_article = Article(title=request.form['name'],
                              link=request.form['link'],
                              description=request.form['description'],
                              topic_id=topic_id, user_id=user_id)
        session.add(new_article)
        session.commit()
        # TODO: flash message on success?
        return redirect(url_for('showTopic', topic_id=topic_id))
    else:
        topics = session.query(Topic).order_by(Topic.name)
        return render_template('newArticle.html', topics=topics,
                               topic_id=topic_id)


# Article page
@app.route('/topics/<int:topic_id>/articles/<int:article_id>/')
def showArticle(topic_id, article_id):
    topic = session.query(Topic).filter_by(id=topic_id).one()
    topics = session.query(Topic).order_by(Topic.name)
    article = session.query(Article).filter_by(id=article_id).one()
    author = session.query(User).filter_by(id=article.user_id).one()
    author_name = author.name
    if 'username' in login_session:
        if login_session['user_id'] == article.user_id:
            return render_template('article.html', article=article,
                                   topic=topic, topics=topics)
        else:
            # hide edit and delete buttons if user is author of this article
            return render_template('publicArticle.html', article=article,
                                   topic=topic, topics=topics,
                                   author=author_name)
    else:
        return render_template('publicArticle.html', article=article,
                               topic=topic, topics=topics, author=author_name)


# Edit article
@app.route('/topics/<int:topic_id>/articles/<int:article_id>/edit/',
           methods=['GET', 'POST'])
def editArticle(topic_id, article_id):
    if 'username' not in login_session:
        return redirect('/login')
    edited_article = session.query(Article).filter_by(id=article_id).one()
    topics = session.query(Topic).order_by(Topic.name)
    topic = session.query(Topic).filter_by(id=topic_id).one()
    # check if user if allowed to modify the article
    if login_session['user_id'] != edited_article.user_id:
        return "<script>function myFunction() {\
            alert('You are not authorized to edit this article. \
            You can only edit articles you created.');\
            }</script><body onload='myFunction()'>"

    if request.method == 'POST':
        if request.form['title']:
            edited_article.title = request.form['title']
        if request.form['description']:
            edited_article.description = request.form['description']
        if request.form['link']:
            edited_article.link = request.form['link']
        return redirect(url_for('showArticle', topic_id=topic.id,
                        article_id=edited_article.id))
    else:
        return render_template('editArticle.html', topic_id=topic.id,
                               topics=topics, article=edited_article)


# Delete article
@app.route('/topics/<int:topic_id>/articles/<int:article_id>/delete/',
           methods=['GET', 'POST'])
def deleteArticle(topic_id, article_id):
    if 'username' not in login_session:
        return redirect('/login')
    article_to_delete = session.query(Article).filter_by(id=article_id).one()
    topics = session.query(Topic).order_by(Topic.name)
    topic = session.query(Topic).filter_by(id=topic_id).one()
    # check if user is allowed to delete article
    if login_session['user_id'] != article_to_delete.user_id:
        return "<script>function myFunction() {\
            alert('You are not authorized to delete this article. \
            You can only delete articles you created.');\
            }</script><body onload='myFunction()'>"

    if request.method == 'POST':
        session.delete(article_to_delete)
        session.commit()
        return redirect(url_for('showTopic', topic_id=topic.id))
    else:
        return render_template('deleteArticle.html', topic=topic,
                               topics=topics, article=article_to_delete)


# API endpoints
# List of topics (JSON)
@app.route('/topics/JSON')
def topicsJSON():
    topics = session.query(Topic).all()
    return jsonify(Topics=[i.serialize for i in topics])


# List of articles in topic (JSON)
@app.route('/topics/<int:topic_id>/JSON')
def topicJSON(topic_id):
    articles = session.query(Article).filter_by(topic_id=topic_id).all()
    return jsonify(Articles=[i.serialize for i in articles])


# Article (JSON)
@app.route('/topics/<int:topic_id>/article/<int:article_id>/JSON')
def articleJSON(topic_id, article_id):
    article = session.query(Article).filter_by(id=article_id).one()
    return jsonify(Article=article.serialize)


# Authentication and authorization
# Login page
@app.route('/login')
def showLogin():
    topics = session.query(Topic).all()
    # generate random state
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state, topics=topics)


# Profile page
@app.route('/profile')
def showProfile():
    topics = session.query(Topic).all()
    if 'username' in login_session:
        name = login_session['username']
        picture = login_session['picture']
        email = login_session['email']
        user_id = getUserId(email)
        articles = session.query(Article).filter_by(user_id=user_id).all()
        print articles
        print user_id
        return render_template('userInfo.html', topics=topics,
                               articles=articles, name=name, email=email,
                               picture=picture)
    else:
        return render_template('noUserInfo.html', topics=topics)


# Google OAuth
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('/var/www/helper/helper/client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
        print credentials
        print credentials.access_token
        print credentials.id_token['sub']
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response
    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    # Check if user is already connected
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        print 'user is in session already, update access token'
        # TODO: try to do disconnect with old token
        #url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' \
        #    % stored_access_token
        #h = httplib2.Http()
        #result = h.request(url, 'GET')[0]
        #print result
        #if result['status'] == '200':
        #    del login_session['access_token']
    else:
        login_session['gplus_id'] = gplus_id

        # Get user info
        userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        params = {'access_token': credentials.access_token, 'alt': 'json'}
        answer = requests.get(userinfo_url, params=params)

        data = answer.json()

        login_session['username'] = data['name']
        login_session['picture'] = data['picture']
        login_session['email'] = data['email']

        user_id = getUserId(login_session['email'])
        if not user_id:
            user_id = createUser(login_session)
        login_session['user_id'] = user_id

    # Store the access token in the session.
    login_session['access_token'] = credentials.access_token

    # Show info about user
    output = ''
    output += '<h3>Welcome, '
    output += login_session['username']
    output += '!</h3>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 100px; height: 100px;border-radius: 150px;\
        -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    return output


# Disconnect (Google OAuth)
@app.route("/gdisconnect")
def gdisconnect():
    topics = session.query(Topic).order_by(Topic.name)
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        status = "Current user not connected."
        return render_template('logout.html', topics=topics,
                               user_status=status)
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' \
        % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        status = "Successfully disconnected."
        return render_template('logout.html', topics=topics,
                               user_status=status)
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.'), 400
        )
        response.headers['Content-Type'] = 'application/json'
        status = "Failed to revoke token for given user."
        return render_template('logout.html', topics=topics,
                               user_status=status)


# API Endpoint: user info (JSON)
@app.route('/users/<int:user_id>/JSON')
def showUser(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return jsonify(User=user.serialize)


@app.route('/robots.txt')
def getRobotsTxt():
    return send_from_directory(app.static_folder, request.path[1:])


def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserId(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

app.secret_key = 'jdshfsklfhjdsflehfjLKJHBLKHNN*YI*YFNO&Iry3noi837rhyg&*&*$#*#*YR&*O#YR#Y$(POUFHLUHFDY'

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
