import datetime
import string
import random

from django.utils import simplejson

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from google.appengine.api import channel
from google.appengine.ext import db
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

from rTree import *

# Datastore model to keep track of channels
class ChannelPool(db.Model):
    client_id = db.StringProperty()
    token = db.StringProperty()
    in_use = db.BooleanProperty()
    expire = db.DateTimeProperty()
    
class RTreeInterface :
    tree = None
    
    def __init__(self):
        pageSize = 100
        minEntries = 50
        
        meta = DBMetaData.get_by_key_name("metadata")
        if not meta:
            tree = RTree(pageSize, minEntries)
            tree.save()
        else:
            tree = RTree(None, None)
            
    def getRectString(self, queryString):
        # Parse string here. Can be changed depending on input string we expect.
        # Expected string = x1, y1, x2, y2
        coord = queryString.strip().split(string.whitespace.join(','))
        if len(coord) != 4:
            return None
        
        x1 = coord[0]
        y1 = coord[1]
        x2 = coord[2]
        y2 = coord[3]
        
        searchRec = Entry(Rect[x1, y1], [x2, y2])
        results = self.tree.search(searchRec)
        print results
    
        message_template = {
            'type': 'results',
            'rect': results     # will be a list of rectangles
        }
        return simplejson.dumps(message_template)
    
    def load(self, blob_info):
        blob_reader = blobstore.BlobReader(blob_info)
        insertFromTree(blob_reader, self.tree)

class HandleQuery(webapp.RequestHandler):
    def post(self):
        client_id = self.request.get('client_id')
        query = self.request.get('query')
        rtree = RTreeInterface()
        message = rtree.getRectangles(query)
        if message != None:
            channel.send_message(client_id, message)        
    
# Gives back a blobstore URL
class GetUploader(webapp.RequestHandler):
    def get(self):
        client_id = self.request.get('client_id')
        
        upload_url = blobstore.create_upload_url('/upload')
        message_template = {
            'type': 'upload',
            'url': upload_url     # will be a list of rectangles
        }
        message = simplejson.dumps(message_template)
        channel.send_message(client_id, message)

# Handles an upload
class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        upload_files = self.get_uploads('file')
        blob_info = upload_files[0]
        rtree = RTreeInterface()
        rtree.load(blob_info)

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
            
            ch = ChannelPool(key_name = client_id, 
                             client_id = client_id,
                             token = token, 
                             in_use = True, 
                             expire = expire)
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
                
                ch = ChannelPool(key_name = client_id,
                                 client_id = client_id,
                                 token = token, 
                                 in_use = True, 
                                 expire = expire)
                ch.put()
        
        template_values = {'token': token,
                           'id': client_id
                           }

        self.response.out.write(template.render('index.html',template_values))

app = webapp.WSGIApplication([('/', MainPage),
                                       ('/query', HandleQuery),
                                       ('/getURL', GetUploader),
                                       ('/upload', UploadHandler)], 
                                     debug=True)

def getID():
    chars=string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for x in range(10))

#def main():
#    run_wsgi_app(app)


#if __name__ == "__main__":
#    main()
