# Client ID:  993479094039-b9psgspck0ccgt5clbqqo58i87foggdn.apps.googleusercontent.com
# Client Secret:  YSpCV_P_fiye7wwBRqfktd0u

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask import session as login_session
from flask import make_response

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
 
from database_setup import Base, Restaurant, MenuItem, User
#from flask.ext.sqlalchemy import SQLAlchemy
from random import randint
import datetime
import random, string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(open('client_secrets.json','r').read())['web']['client_id']
APPLICATION_NAME = "Restaurants"

engine = create_engine('sqlite:///restaurantmenuwithusers.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


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
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
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

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# Disconnect the currently logged in user
@app.route('/gdisconnect')
def gdisconnect():
  # Only disconnect the current user
  access_token = login_session['credentials']
  print 'In gdisconnect access token is %s', access_token
  print 'User name is: '
  print login_session['username']
  if access_token is None:
    response = make_response(json.dumps('Current user not connected.'), 401)
    response.headers['Content-Type'] = 'application/json'
    return response
  # Execute HTTP GET request to revoke current token.
  url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
  h = httplib2.Http()
  result = h.request(url, 'GET')[0]
  print 'result is '
  print result

  if result['status'] == '200':
    # Reset the user's session.
    del login_session['credentials']
    del login_session['gplus_id']
    del login_session['username']
    del login_session['picture']

    response = make_response(json.dumps('Successfully disconnected'), 200)
    response.headers['Content-Type'] = 'application/json'
    return response
  else:
    response = make_response(json.dumps('Failed to revoke token for given user.', 400))
    response.headers['Content-Type'] = 'application/json'
    return response


# Produces a JSON formatted output of all the restaurants
@app.route('/restaurants/JSON')
def restaurantListingJSON():
    items = session.query(Restaurant).all()
    return jsonify(Restaurants=[i.serialize for i in items])

# Produces a JSON formatted output of all the menu items for a particular restaurant
@app.route('/restaurants/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])

# Produces a JSON formatted output of a particular menu item in a particular restaurant
@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(restaurant_id,menu_id):
    menuItem = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(MenuItem=menuItem.serialize)

# Web page that lists all of the restaurants allows the user to create, edit, or delete restaurants
@app.route('/restaurants/')
def restaurants():
    restaurantListing = session.query(Restaurant).all()
    return render_template('restaurants.html', items=restaurantListing)

# Web page where a new restaurant is created
@app.route('/restaurant/new', methods=['GET','POST'])
def newRestaurant():
  if 'username' not in login_session:
    return redirect('/login')
  if request.method == 'POST':
    newItem = Restaurant(name = request.form['name'])
    session.add(newItem)
    session.commit()
    flash("new restaurant created!")
    return redirect(url_for('restaurants'))
  else:
    return render_template('newRestaurant.html')

# Web page where a restaurant is edited
@app.route('/Restaurant/<int:restaurant_id>/edit', methods=['GET','POST'])
def editRestaurant(restaurant_id):
  if 'username' not in login_session:
    return redirect('/login')
  else:
    editedItem = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if request.method == 'POST':
      editedItem.name = request.form['name']
      session.add(editedItem)
      session.commit()
      flash("restaurant changed!")
      return redirect(url_for('restaurants'))
    else:
      return render_template('editRestaurant.html', restaurant_id=restaurant_id, item=editedItem)

# Web Page where a restaurant is deleted 
@app.route('/Restaurant/<int:restaurant_id>/delete', methods=['GET','POST'])
def deleteRestaurant(restaurant_id):
  if 'username' not in login_session:
    return redirect('/login')
  deletedItem = session.query(Restaurant).filter_by(id=restaurant_id).one()
  if request.method == 'POST':
    session.delete(deletedItem)
    session.commit()
    flash("restaurant deleted!")
    return redirect(url_for('restaurants'))
  else:
    return render_template('deleteRestaurant.html', restaurant_id=restaurant_id, item=deletedItem)

# Web page that lists all of the menu items for a particular restaurant and allows the user to create, edit, or delete menu items
@app.route('/restaurants/<int:restaurant_id>/')
def restaurantMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id)
    return render_template('menu.html', restaurant=restaurant, items=items)

# Web page where a new menu item is created
@app.route('/menuItem/<int:restaurant_id>/new', methods=['GET','POST'])
def newMenuItem(restaurant_id):
  if 'username' not in login_session:
    return redirect('/login')
  if request.method == 'POST':
    newItem = MenuItem(name = request.form['name'], restaurant_id=restaurant_id)
    session.add(newItem)
    session.commit()
    flash("new menu item created!")
    return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
  else:
    return render_template('newMenuItem.html', restaurant_id=restaurant_id)

# Web page where a menu item is edited
@app.route('/menuItem/<int:restaurant_id>/<int:menu_id>/edit', methods=['GET','POST'])
def editMenuItem(restaurant_id, menu_id):
  if 'username' not in login_session:
    return redirect('/login')
  editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
  if request.method == 'POST':
    editedItem.name = request.form['name']
    session.add(editedItem)
    session.commit()
    flash("menu item changed!")
    return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
  else:
    return render_template('editMenuItem.html', restaurant_id=restaurant_id, menu_id=menu_id, item=editedItem)

# Web Page where a menu item is deleted 
@app.route('/menuItem/<int:restaurant_id>/<int:menu_id>/delete', methods=['GET','POST'])
def deleteMenuItem(restaurant_id, menu_id):
  if 'username' not in login_session:
    return redirect('/login')
  deletedItem = session.query(MenuItem).filter_by(id=menu_id).one()
  if request.method == 'POST':
    session.delete(deletedItem)
    session.commit()
    flash("menu item deleted!")
    return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
  else:
    return render_template('deleteMenuItem.html', restaurant_id=restaurant_id, menu_id=menu_id, item=deletedItem)

def createUser(login_session):
  newUser = User(name = login_session['username'], email = login_session['email'], picture = login_session['picture'])
  session.add(newUser)
  session.commit()
  user = session.query(User).filter_by(email=login_session['email'].one())
  return user.id

def getUserInfo(user_id):
  user = session.query(User).filter_by(id = user_id).one()
  return user

def getUserID(email):
  try:
    user = session.query(User).filter_by(email = email).one()
    return user.id
  except:
    return None

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)