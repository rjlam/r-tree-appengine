import datetime
import string
import random
import os

from django.utils import simplejson

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from google.appengine.api import channel
from google.appengine.ext import db
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

from rTree import *

import bulkRTree
import rTree

JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))
###

## these two functions can be used to visualize from a file ... will not be used down the
## road, but it's good to have them around
def parseFile(fn) : 
	minX = 1000
	minY = 1000
	maxX = -1000
	maxY = -1000
	f = open(fn)
	for line in f :
		p = map(float, line.strip().split("\t"))
		minX = min(minX, p[0])
		maxX = max(maxX, p[2])
		minY = min(minY, -p[3])
		maxY = max(maxY, -p[1])	
	f.close()
	return (minX*(-1.0), minY*(-1.0), maxX, maxY)
	
def createRects(fn):
	minX, minY, maxX, maxY = parseFile(fn)
	print minX, minY, maxX, maxY
	minX += 20
	minY += 20
	l = []
	f = open(fn)
	for line in f :
		p = map(float, line.strip().split("\t"))
		l.append([p[0]+minX, -p[1]+minY ,max(1,p[2]-p[0]),max(1,p[3]-p[1])])
	f.close()
	return l

## these functions are used to actually visualize rectangles from the tree... 
## for now visualize the entire tree, but we'll eventually just visualize the result set.	
def parseTree() : 
	meta = rTree.DBMetaData.get_by_key_name("metadata")
	if meta is None :
		return (None,None, None, None)
	scalingFactor = 1
	tree = rTree.RTree(None, None)
	entries = []
	rTree.entryList = []
	rTree.getEntries(tree.root)
	entries = rTree.entryList
	minX = 1000
	minY = 1000
	maxX = -1000
	maxY = -1000
	for e in entries :
		minX = min(minX, scalingFactor*e.I.boundingBoxMin[0])
		maxX = max(maxX, scalingFactor*e.I.boundingBoxMax[0])
		minY = min(minY, scalingFactor*-e.I.boundingBoxMin[1])
		maxY = max(maxY, scalingFactor*-e.I.boundingBoxMax[1])	

	return (minX*(-1.0), minY*(-1.0), maxX, maxY)
	
def createTreeRects():
	minX, minY, maxX, maxY = parseTree()
	if minX is None : 
		return []
	scalingFactor = 1
	print minX, minY, maxX, maxY
	minX += 20
	minY += 20
	l = []
	tree = rTree.RTree(None, None)
	rTree.entryList = [];
	rTree.getEntries(tree.root)
	entries = rTree.entryList
	for e in entries : 
		p = [e.I.boundingBoxMin[0],e.I.boundingBoxMin[1],e.I.boundingBoxMax[0],e.I.boundingBoxMax[1]]
		l.append([(scalingFactor*p[0])+minX, (scalingFactor*-p[1])+minY ,max(1,p[2]-p[0]),max(1,p[3]-p[1])])
	return (l, minX, minY)

# normalize a list of entries and scale by a scaling factor
def normalizeList(entries):
	l = []
	minX = 1000
	minY = 1000
	maxX = -1000
	maxY = -1000
	scalingFactor = 100
	for e in entries :
		minX = min(minX, scalingFactor*e.I.boundingBoxMin[0])
		maxX = max(maxX, scalingFactor*e.I.boundingBoxMax[0])
		minY = min(minY, scalingFactor*(-e.I.boundingBoxMin[1]))
		maxY = max(maxY, scalingFactor*(-e.I.boundingBoxMax[1]))
	minX *= -1.0
	minY *= -1.0
	minX += 20
	minY += 20
	for e in entries : 
		p = [e.I.boundingBoxMin[0],e.I.boundingBoxMin[1],e.I.boundingBoxMax[0],e.I.boundingBoxMax[1]]
		l.append([(scalingFactor*p[0])+minX, (scalingFactor*(-p[1]))+minY ,max(1,p[2]-p[0]),max(1,p[3]-p[1])])
	return (l, minX, minY)
		
	
###
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
        token = self.request.get('server_token')
        sPoint = self.request.get('startPoint')
        ePoint = self.request.get('endPoint')
        message = self.getRectangles(sPoint, ePoint)
        self.response.out.write(message);
        #channel.send_message(client_id, message)

    def computePath(self, sPoint, ePoint, entryList):
        ## TODO: compute path from sPoint to ePoint using Entry objects in entryList
        #lst, mx, my = createTreeRects()
        # for now just normalize list and scale
        lst, mx, my = normalizeList(entryList)
        print "Number results:" ,len(lst)		
        results = []
        for item in lst : 
           m = {"res":item}
           results.append(m)
        return (results, mx, my)
        
    def getRectangles(self, sPoint, ePoint):
        # Hook into R-tree code here
        message_template = {
            'type': 'error',
            'message': 'ok',  # will be a list of rectangles
            'rect': '[]'
        }
        meta = rTree.DBMetaData.get_by_key_name("metadata")
        if meta is None :	
            message_template['message'] = "No RTree in database."
            return simplejson.dumps(message_template)
        
        try: 
            sParts = map(float, sPoint.split(','))
            eParts = map(float, ePoint.split(','))
        except:
            message_template['message'] = "Invalid input format"
            return simplejson.dumps(message_template)

        if len(sParts) != 2 or len(eParts) != 2 : 
            message_template['message'] = "Invalid input format"
            return simplejson.dumps(message_template)
        message_template['type'] = 'results'
        tree = rTree.RTree(None, None)
        minX = min(sParts[0], eParts[0])
        minY = min(sParts[1], eParts[1])
        maxX = max(sParts[0], eParts[0])
        maxY = max(sParts[1], eParts[1])
        allRect = rTree.Entry(rTree.Rect([minX,minY],[maxX, maxY]))
        results = tree.search(allRect)
        path, mx, my = self.computePath(sPoint, ePoint, results)
        message_template['rect'] = path        
        message_template['minVals'] = {'mx':mx, 'my':my}
        return simplejson.dumps(message_template)
		
class DoBulkLoad(webapp.RequestHandler):
	def post(self):
		msg = "No bulk loading to do"
		meta = rTree.DBMetaData.get_by_key_name("metadata")
		if meta is None : 
			rtree = bulkRTree.RTree(100, 50)
			fn = "CaStreet.ascii.10k" #"USclpoint.fnl"
			bulkRTree.insertFromTree(fn, rtree)
			print "Now saving to database."
			rtree.save()
			msg = "RTree bulk loading completed."
		else :
			print msg
			
		template_values = {'id': self.request.get('client_id'), 'token': self.request.get('server_token'), 'message':msg}
		template = JINJA_ENVIRONMENT.get_template('loaded.html')		
		self.response.out.write(template.render(template_values))
		
	def get(self):		
		self.post()
			
class MainPage(webapp.RequestHandler):

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

        template = JINJA_ENVIRONMENT.get_template('index.html')        
        self.response.out.write(template.render(template_values))

    def post(self):
        self.get()

app = webapp.WSGIApplication([('/bulk_load', DoBulkLoad),('/send_query', HandleQuery),('/', MainPage),], debug=True)

def getID():
    chars=string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for x in range(10))

def main():
    run_wsgi_app(app)


#if __name__ == "__main__":
#    main()
