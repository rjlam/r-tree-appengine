import jinja2
import datetime
import string
import random

from django.utils import simplejson

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from google.appengine.api import channel
from google.appengine.ext import db

import bulkRTree
import rTree


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
        # rect = parseRectangles()
        message_template = {
            'type': 'results',
            'rect': ''  # will be a list of rectangles
        }
        return simplejson.dumps(message_template)

class MainPage(webapp.RequestHandler):
    def bulkLoad(self) : 
        meta = rTree.DBMetaData.get_by_key_name("metadata")
        if meta is None : 
            rtree = bulkRTree.RTree(100, 50)
            fn = "USclpoint.fnl"
            bulkRTree.insertFromTree(fn, rtree)
            rtree.save()

    def randomSearch(self):
        meta = rTree.DBMetaData.get_by_key_name("metadata")
        if meta is None :	
            return None	
        rtree = rTree.RTree(None, None)
        # just a random example for now
        e = rTree.Entry(rTree.Rect([-91.09, 45.15],[-90.07, 46.16])) 
        l = rtree.search(e)
        print "number of search results : ", len(l) , " "
        if len(l) > 0 :
            print l[0].I.boundingBoxMin, l[0].I.boundingBoxMax, l[0].nodeId
        print "Number of entries in tree: ", rTree.countEntries(rtree.root)	
		
    def get(self):
        # Get channel from available pool
        q = ChannelPool.all().filter('in_use = ', False)
        ch = q.get()
        if not ch:
            client_id = getID();
            token = channel.create_channel(client_id, duration_minutes = 1440)
            expire = datetime.datetime.now() + datetime.timedelta(0, 1440)
            
            ch = ChannelPool(key_name = client_id, token=token, in_use=True, expire=expire)
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
                
                ch = ChannelPool(key_name = client_id, token=token, in_use=True, expire=expire)
                ch.put()        
        template_values = {'token': token,
                           'id': client_id
                           }
        env = jinja2.Environment(loader=jinja2.PackageLoader('main', '.'))
        template = env.get_template('index.html')
        
        ## should be connected to a button
        self.bulkLoad()
        ## should follow after the actual search query
        self.randomSearch()
        self.response.out.write(template.render(template_values))

app = webapp.WSGIApplication([('/', MainPage)], debug=True)

def getID():
    chars=string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for x in range(10))

def main():
    run_wsgi_app(application)


if __name__ == "__main__":
    main()
