from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
 
from database_setup import Base, Restaurant, MenuItem
#from flask.ext.sqlalchemy import SQLAlchemy
from random import randint
import datetime
import random

class webserverHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		try:
			if self.path.endswith("/restaurants"):
				self.send_response(200)
				self.send_header('Content-type', 'text/html')
				self.end_headers()

				engine = create_engine('sqlite:///restaurantmenu.db')
				Base.metadata.bind = engine
				DBSession = sessionmaker(bind=engine)
				session = DBSession()

				output = ""
				output += "<html><body>"
				output += "<a href = '/restaurants/new' >Click here to create a new restaurant</a><br><br>"

				items = session.query(Restaurant).all()
				for item in items:
					output += item.name
					output += "<br>"
					output += "<a href = '/%s/edit'>Edit</a><br>" % item.id
					output += "<a href = '/%s/delete' >Delete</a><br><br>" % item.id
				output += "</body></html>"
				self.wfile.write(output)
				print output
				return
			if self.path.endswith("/restaurants/new"):
				self.send_response(200)
				self.send_header('Content-type', 'text/html')
				self.end_headers()

				output = ""
				output += "<form method='POST' enctype='multipart/form-data' action='/restaurants/new'><h2>What restaurant do you want to add?</h2><input name='message' type='text'><input type='submit' value='Submit'> </form>"
				output += "</body></html>"
				self.wfile.write(output)
				print output
				return
			if self.path.endswith("/edit"):
				self.send_response(200)
				self.send_header('Content-type', 'text/html')
				self.end_headers()

				engine = create_engine('sqlite:///restaurantmenu.db')
				Base.metadata.bind = engine
				DBSession = sessionmaker(bind=engine)
				session = DBSession()

				restaurant_id_path = self.path.split('/')[1]
				restaurantToBeChanged = session.query(Restaurant).filter_by(id = restaurant_id_path).one()

				output = ""
				output += "<form method='POST' enctype='multipart/form-data' action='/restaurants/%s/edit'>" % restaurant_id_path
				output += "<h2>Enter the new name for the restaurant</h2><input name='message' type='text' input type='submit' placeholder = '%s' >" % restaurantToBeChanged.name
				output += "<input type= 'submit' value= 'Rename'></form>"
				output += "</body></html>"
				self.wfile.write(output)
				print output
				return
			if self.path.endswith("/delete"):
				self.send_response(200)
				self.send_header('Content-type', 'text/html')
				self.end_headers()

				engine = create_engine('sqlite:///restaurantmenu.db')
				Base.metadata.bind = engine
				DBSession = sessionmaker(bind=engine)
				session = DBSession()

				restaurant_id_path = self.path.split('/')[1]
				restaurantToBeChanged = session.query(Restaurant).filter_by(id = restaurant_id_path).one()

				output = ""
				output += "<form method='POST' enctype='multipart/form-data' action='/restaurants/%s/delete'>" % restaurant_id_path
				output += "<h2>Are you sure you want to delete this restaurant? %s</h2>" % restaurantToBeChanged.name
				output += "<input type= 'submit' value= 'Delete'></form>"
				output += "</body></html>"
				self.wfile.write(output)
				print output
				return
		except IOError:
			self.send_error(404, "File Not Found %s" % self.path)

	def do_POST(self):
		try:
			if self.path.endswith("/edit"):
				ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
				if ctype == 'multipart/form-data':
					fields=cgi.parse_multipart(self.rfile, pdict)
					messagecontent = fields.get('message')

				engine = create_engine('sqlite:///restaurantmenu.db')
				Base.metadata.bind = engine
				DBSession = sessionmaker(bind=engine)
				session = DBSession()

				restaurant_id_path = self.path.split('/')[2]
				restaurantToBeChanged = session.query(Restaurant).filter_by(id = restaurant_id_path).one()
				restaurantToBeChanged.name = messagecontent[0]
				
				session.add(restaurantToBeChanged)
				session.commit()

				self.send_response(301)
				self.send_header('Content-type','text/html')
				self.send_header('Location','/restaurants')
				self.end_headers()

				self.wfile.write(output)
				print output
				return
			if self.path.endswith("/delete"):
				engine = create_engine('sqlite:///restaurantmenu.db')
				Base.metadata.bind = engine
				DBSession = sessionmaker(bind=engine)
				session = DBSession()

				restaurant_id_path = self.path.split('/')[2]
				restaurantToBeChanged = session.query(Restaurant).filter_by(id = restaurant_id_path).one()
				
				session.delete(restaurantToBeChanged)
				session.commit()

				self.send_response(301)
				self.send_header('Content-type','text/html')
				self.send_header('Location','/restaurants')
				self.end_headers()

				self.wfile.write(output)
				print output
				return
			if self.path.endswith("/restaurants/new"):
				ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
				if ctype == 'multipart/form-data':
					fields=cgi.parse_multipart(self.rfile, pdict)
					messagecontent = fields.get('message')

				engine = create_engine('sqlite:///restaurantmenu.db')
				Base.metadata.bind = engine
				DBSession = sessionmaker(bind=engine)
				session = DBSession()

				newRestaurant = Restaurant(name=messagecontent[0])
				session.add(newRestaurant)
				session.commit()

				self.send_response(301)
				self.send_header('Content-type','text/html')
				self.send_header('Location','/restaurants')
				self.end_headers()

				self.wfile.write(output)
				print output
				return

		except:
			pass

def main():
	try:
		port = 8080
		server = HTTPServer(('',port), webserverHandler)
		print "Web server running on port %s" % port
		server.serve_forever()
	except KeyboardInterrupt:
		print "^C entered, stopping web server..."
		server.socket.close()


if __name__ == '__main__':
		main()