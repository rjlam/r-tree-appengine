import jinja2
import datetime
import string
import random

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from google.appengine.api import channel
from google.appengine.ext import db

# Datastore model to keep track of channels
class ChannelPool(db.Model):
    client_id = db.StringProperty()
    token = db.StringProperty()
    in_use = db.BooleanProperty()
    expire = db.DateTimeProperty()

class HandleQuery(webapp.RequestHandler):
    def post(self):
        client_id = self.request.get('client_id')
        query = self.request.get('query')
        message = self.getRectangles(query)
        channel.send_message(client_id, message)
        
    def getRectangles(self, queryString):
        # Hook into R-tree code here
        return ""

#
class MainPage(webapp.RequestHandler):
    def get(self):
        # Get channel from available pool
        q = ChannelPool.all().filter('in_use = ', False)
        ch = q.get()
        if not ch:
            client_id = getID();
            token = channel.create_channel(client_id, duration_minutes = 1440)
            expire = datetime.datetime.now() + datetime.timedelta(0, 1440)
            
            ch = ChannelPool(key_name = client_id, token, True, expire)
            ch.put()
        else:
            now = datetime.datetime.now()
            for ch in q.run():
                if ch.expire - now > 0:
                    reuse = True
                    break
                
            if reuse:
                client_id = ch.client_id
                token = ch.token
                ch.in_use = True
                ch.put()
            else:
                client_id = getID();
                token = channel.create_channel(client_id, duration_minutes = 1440)
                expire = datetime.datetime.now() + datetime.timedelta(0, 1440)
                
                ch = ChannelPool(key_name = client_id, token, True, expire)
                ch.put()
        
        template_values = {'token': token,
                           'id': client_id
                           }
        template = jinja2.Environment.get_template('index.html')
        self.response.out.write(template.render(template_values))
        self.response.out.write()

application = webapp.WSGIApplication([('/', MainPage)], debug=True)

def getID():
    chars=string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for x in range(10))

def main():
    run_wsgi_app(application)


if __name__ == "__main__":
    main()
