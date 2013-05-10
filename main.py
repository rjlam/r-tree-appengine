import jinja2
import datetime
import string
import random
import os

from django.utils import simplejson

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from google.appengine.api import channel, memcache
from google.appengine.ext import db

import bulkRTree
import rTree
import cPickle

from path import *

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
	meta = rTree.getMeta()
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
def normalizeList(entries, entries2 = None):
	l = []
	minX = 100000
	minY = 100000
	maxX = -100000
	maxY = -100000
	scalingFactor = 500
	isRect = None
	for e in entries :
		r = e
		if isRect is None : 
			try : 
				r = e.I
				isRect = False
			except : 
				r = e
				isRect = True
		elif not isRect : 
			r = e.I
		minX = min(minX, scalingFactor*r.boundingBoxMin[0])
		maxX = max(maxX, scalingFactor*r.boundingBoxMax[0])
		minY = min(minY, scalingFactor*(-r.boundingBoxMin[1]))
		maxY = max(maxY, scalingFactor*(-r.boundingBoxMax[1]))
	minX *= -1.0
	minY *= -1.0
	minX += 20
	minY += 20
	for e in entries : 
		r = e
		if not isRect : 
			r = e.I
		p = [r.boundingBoxMin[0],r.boundingBoxMin[1],r.boundingBoxMax[0],r.boundingBoxMax[1]]
		l.append([(scalingFactor*p[0])+minX, (scalingFactor*(-p[1]))+minY ,max(2,p[2]-p[0]),max(2,p[3]-p[1])])
	
	if entries2 is not None : 
		l2 = []
		isRect = None
		for e in entries2 : 
			r = e
			if isRect is None : 
				try : 
					r = e.I
					isRect = False
				except : 
					r = e
					isRect = True
			if not isRect : 
				r = e.I
			p = [r.boundingBoxMin[0],r.boundingBoxMin[1],r.boundingBoxMax[0],r.boundingBoxMax[1]]
			l2.append([(scalingFactor*p[0])+minX, (scalingFactor*(-p[1]))+minY ,max(5,p[2]-p[0]),max(5,p[3]-p[1])])
		return (l,l2, minX, minY)
	else : 
		return (l, minX, minY)
		
	
###
# Datastore model to keep track of channels
class ChannelPool(db.Model):
    client_id = db.StringProperty()
    token = db.StringProperty()
    in_use = db.BooleanProperty()
    expire = db.DateTimeProperty()

class HandleQuery(webapp.RequestHandler):
    def post(self):
        client_id = self.request.get('client_id')
        token = self.request.get('server_token')
        sPoint = self.request.get('startPoint')
        ePoint = self.request.get('endPoint')
        message = self.getRectangles(sPoint, ePoint)
        self.response.out.write(message);
        #channel.send_message(client_id, message)

    def formatResultList(self, lst):
        results = []
        for item in lst : 
           m = {"res":item}
           results.append(m)	
        return results

    def computePath(self, sPoint, ePoint, rtree, entryList):
        ## TODO: compute path from sPoint to ePoint using Entry objects in entryList
        #lst, mx, my = createTreeRects()
        # for now just normalize list and scale
        #lst, mx, my = normalizeList(entryList)
        resEntries = PathSearch(sPoint, ePoint, rtree, entryList)
        lst, lst2, mx, my = normalizeList(entryList, resEntries)
        print "Number results:" ,len(lst)		
        return (self.formatResultList(lst),self.formatResultList(lst2), mx, my)
        
    def getRectangles(self, sPoint, ePoint):
        # Hook into R-tree code here
        message_template = {
            'type': 'error',
            'message': 'ok',  
            'rect': '[]' # will be a list of rectangles
        }
        meta = rTree.getMeta()
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
        queryData = [sParts[0],sParts[1], eParts[0], eParts[1]]
        message_template['type'] = 'results'
        if memcache.get(str(queryData)+"-1") is None : 
        
            tree = rTree.RTree(None, None)
            minX = min(sParts[0], eParts[0])
            minY = min(sParts[1], eParts[1])
            maxX = max(sParts[0], eParts[0])
            maxY = max(sParts[1], eParts[1])
            sEntry = make_leaf(rTree.Rect([sParts[0],sParts[1]],[sParts[0], sParts[1]]), tree)
            eEntry = make_leaf(rTree.Rect([eParts[0],eParts[1]],[eParts[0], eParts[1]]), tree) 
            allRect = rTree.Entry(rTree.Rect([minX,minY],[maxX, maxY]))
            results = tree.search(allRect)
            print "RTree search completed. Number of results: ", len(results)
        else :
            d = memcache.get(str(queryData)+"-1")
            results = cPickle.loads(d)
        if len(results) > 10000 : 
            message_template['message'] = "Selected area too large for route computation. (Exceeding 10,000 rectangles)."
            lst,mx,my = normalizeList(results)
            message_template['grect'] = self.formatResultList(lst)
            message_template['rect'] = self.formatResultList(["0"])
            message_template['minVals'] = {'mx':mx, 'my':my}
            message_template['sp'] = {'x':sEntry.I.boundingBoxMin[0], 'y':sEntry.I.boundingBoxMin[1]}
            message_template['ep'] = {'x':eEntry.I.boundingBoxMin[0], 'y':eEntry.I.boundingBoxMin[1]}
        else :
            if memcache.get(str(queryData)+"-2") is not None : 
                res = memcache.get(str(queryData)+"-2")
                gRect,mxx,myy = normalizeList(res)
                mx = min(mxx, mx)
                my = min(myy, my)
            else :
                gRect, path, mx, my = self.computePath(sEntry, eEntry, tree, results)
            message_template['rect'] = path        
            message_template['grect'] = gRect
            message_template['minVals'] = {'mx':mx, 'my':my}
            message_template['sp'] = {'x':sEntry.I.boundingBoxMin[0], 'y':sEntry.I.boundingBoxMin[1]}
            message_template['ep'] = {'x':eEntry.I.boundingBoxMin[0], 'y':eEntry.I.boundingBoxMin[1]}
        return simplejson.dumps(message_template)
		
class DoBulkLoad(webapp.RequestHandler):
	def post(self):
		showBulk = "invisible"
		msg = "No bulk loading to do"
		meta = rTree.getMeta()
		rtData = memcache.get("rtree")
		where = self.request.get('upTo')
		if meta is None or memcache.get("complete") is None: 
			fn = "RTree.pickled.top" 
			try :
				f = open("RTree.pickled")
				fn = "RTree.pickled"
				f.close()
			except : 
				pass
			#fn = "CaStreet.ascii.10k" #"USclpoint.fnl"
			if rtData is not None : 
				rtree = cPickle.loads(rtData)
			else :
				rtree = bulkRTree.insertFromPickle(fn)
			print "Now saving to database."
			
			i = 0
			j = 0
			howMany = 20
			if where == "" : 
				where = 0
			else : 
				where = int(where)
			upTo = min(len(rtree.root.entries), where+howMany)
			for current in range(where, upTo): #e in rtree.root.entries : 
				e = rtree.root.entries[current]
				if (type(e.child) == str) : 
					f = open("RTree.pickled."+str(current))
					e.child = cPickle.load(f)
					f.close()
				decends = False
				for en in e.child.entries : 
					if type(en.child) == str : 
						decends = True
						f = open(en.child)
						en.child = cPickle.load(f)
						f.close()
						en.child = rtree.depthSaveTree(en.child)
				if decends : 
					rtree.root.entries[current].child = e.child.save()
				else : 
					rtree.root.entries[current].child = rtree.depthSaveTree(e.child)
				i+=1
			memcache.delete("rtree")
			memcache.add("rtree", cPickle.dumps(rtree))

			if (upTo == len(rtree.root.entries)): 
				rtree.rootKey = rtree.root.save()
				rtree.save()
				msg = "RTree bulk loading completed."
				memcache.add("complete", "true")
				ec = rTree.countEntries(rtree.root)
				print ec
			else : 
				perc = int(100.0/len(rtree.root.entries) * upTo)
				msg = "RTree bulk loading: "+str(perc)+" % completed... "
				js = {"upTo":str(upTo), "msg":msg}
				self.response.out.write(simplejson.dumps(js))
				return
		else :
			print msg
		
		template_values = {'id': self.request.get('client_id'), 'token': self.request.get('server_token'), 'showBulk': showBulk,'message':msg}
		template = JINJA_ENVIRONMENT.get_template('index.html')		
		self.response.out.write(template.render(template_values))		
		
		
	def get(self):		
		self.post()
			
class MainPage(webapp.RequestHandler):

    def randomSearch(self):
        meta = rTree.getMeta()
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
            
            ch = ChannelPool(key_name = client_id, client_id=client_id, token=token, in_use=True, expire=expire)
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
                
                ch = ChannelPool(key_name = client_id, client_id=client_id, token=token, in_use=True, expire=expire)
                ch.put() 
        showBulk = "visible"
        meta = rTree.getMeta()
        if meta is not None :       
            showBulk = "invisible"
        template_values = {'token': token,
                           'id': client_id,
                           'showBulk': showBulk
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


if __name__ == "__main__":
    main()
