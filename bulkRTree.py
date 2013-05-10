import sys
import os
from Queue import Queue
from google.appengine.api import memcache, users
from google.appengine.ext import db, webapp
import cPickle
import time

class Rect :
	boundingBoxMin = []
	boundingBoxMax = []
	
	def __init__(self):
		self.boundingBoxMin = []
		self.boundingBoxMax = []
		
	def __init__(self, minVals, maxVals):
		self.boundingBoxMin = []
		self.boundingBoxMax = []		
		self.boundingBoxMin.extend(minVals)
		self.boundingBoxMax.extend(maxVals)	
	
	def __eq__(self, r) : 
		return (self.boundingBoxMin == r.boundingBoxMin and self.boundingBoxMax == r.boundingBoxMax)
		
	def getVolume(self):
		vol = 1
		for i in range(0,len(self.boundingBoxMin)) : 
			vol *= abs(self.boundingBoxMax[i] - self.boundingBoxMin[i])
		return vol
			
	def getExpandVolume(self, r):
		vol = 1
		for i in range(0,len(self.boundingBoxMin)) : 
			bMin = self.boundingBoxMin[i]
			bMax = self.boundingBoxMax[i]
			
			if r.boundingBoxMin[i] < bMin :
				bMin = r.boundingBoxMin[i]
			if r.boundingBoxMax[i] > bMax :
				bMax = r.boundingBoxMax[i]
				
			vol *= abs(bMax - bMin)
		return vol
			
	def overlaps(self, r):
		if (len(r.boundingBoxMin) != len(self.boundingBoxMin)) :
			return False		
		sz = len(self.boundingBoxMin)
		for i in range(0,sz) : 
			if (self.boundingBoxMin[i] > r.boundingBoxMax[i]) or (r.boundingBoxMin[i] > self.boundingBoxMax[i]) : 
				return False
		return True
		
	def includeR(self, r):
		for i in range(0, len(self.boundingBoxMin)) : 
			self.boundingBoxMin[i] = min(self.boundingBoxMin[i],r.boundingBoxMin[i])
			self.boundingBoxMax[i] = max(self.boundingBoxMax[i],r.boundingBoxMax[i])

	# added to make graph work.
	def __hash__(self):
		return hash((tuple(self.boundingBoxMin), tuple(self.boundingBoxMax)))


#########
class DBNode(db.Model):
	size = db.IntegerProperty()
	isRoot = db.BooleanProperty()
	entries = db.BlobProperty()


		
#########		
class Entry : 
	nodeId = None
	I = None
	child = None
	
	def __init__(self, r, nId = None, c = None) : 		
		self.I = r
		self.nodeId = nId
		self.child = c
		
	def getChild(self):
		if self.child is None : 
			return None
		if type(self.child) == type(Node(0)) : 
			return self.child	
		dbn = DBNode.get_by_id(self.child)
		if dbn is not None : 
			return Node(dbn)
		return None


#########				
class Node : 
	
	size = 0
	entries = []
	isRoot = False
	dbn = None
	
	def __init__(self, s, root = False):
		self.entries = []
		self.size = s
		self.isRoot = root
		
	def search(self, s):
		l = []
		if len(self.entries) > 0 : 
			if self.entries[0].child is None : 
				for e in self.entries : 
					if e.I.overlaps(s.I) : 
						l.append(e)
			else : 
				for e in self.entries : 
					l2 = e.child.search(s)
					for item in l2 : 
						l.append(item)
		return l

	def save(self):
		if self.dbn is None: 
			self.dbn = DBNode(size=self.size, isRoot=self.isRoot)		
		self.dbn.entries = cPickle.dumps(self.entries)
		assert(len(self.entries) > 0)
		self.dbn.put()
		memcache.add(str(self.dbn.key().id()), self.dbn, 3600)
		return self.dbn.key().id()


class DBMetaData(db.Model):
	rootId = db.IntegerProperty()
	minEntries = db.IntegerProperty()
	curId = db.IntegerProperty()				
		
class RTree : 
	root = None
	minEntries = None
	curId = 0
	rootKey = None
	
	def __init__(self, pageSize, mE):
		self.root = Node(pageSize, True)
		self.minEntries = mE
		self.curId = 0		

	def save(self):
		if self.rootKey is None :
			self.rootKey = self.depthSaveTree(self.root)
		dbm = DBMetaData(rootId = self.rootKey, minEntries=self.minEntries, curId=self.curId, key_name="metadata")
		dbm.put()
		memcache.add("metadata", dbm, 3600)
	
	def chooseLeaf(self, newEntry, path, depth=-1):
		n = self.root
		d = 1		
		while True : 
			path.append(n)
			if len(n.entries) : 				
				if n.entries[0].child is None : 
					return n
				if depth > 0 and d == depth : 
					return n
				minChange = None
				smallestArea = None
				curEntry = None
				for i in range(0, len(n.entries)) : 
					e = n.entries[i]
					area = e.I.getVolume()
					expandArea = e.I.getExpandVolume(newEntry.I)	
					diffArea = expandArea - area					
					if smallestArea is None or diffArea < smallestArea: 
						smallestArea = diffArea
						curEntry = e
					elif smallestArea == diffArea : 
						oArea = curEntry.I.getExpandVolume(newEntry.I)
						if expandArea < oArea : 
							curEntry = e
				n = curEntry.child
					
			else :
				return n
			d += 1
	###
	# Split Algos
	###
	
	
	def pickSeeds(self, allEntries):		
		i = 0
		maxVol = None
		curE1 = None
		curE2 = None
		while i < len(allEntries) : 
			j = i+1
			e1 = allEntries[i]
			while j < len(allEntries) : 
				e2 = allEntries[j]
				v1 = e1.I.getVolume()
				v2 = e2.I.getVolume()
				v3 = e1.I.getExpandVolume(e2.I)
				v3 = v3 - v1 - v2
				if maxVol is None or v3 > maxVol : 
					maxVol = v3
					curE1 = i
					curE2 = j
				j+=1			
			i+=1
			return (curE1, curE2)
			
	def pickNext(self, allEntries, g1, g2):
		g1Area = g1[0].getVolume()
		g2Area = g2[0].getVolume()
		maxDiff = None
		curEntry = None
		curGroup = None
		for e in allEntries : 
			g1Poss = g1[0].getExpandVolume(e.I) - g1Area
			g2Poss = g2[0].getExpandVolume(e.I) - g2Area
			diff = abs(g1Poss - g2Poss)
			if maxDiff is None or diff > maxDiff : 
				maxDiff = diff
				curEntry = e
				if g1Poss < g2Poss : 
					curGroup = g1
				elif g1Poss == g2Poss :
					if g1Area < g2Area : 
						curGroup = g1
					else : 
						curGroup = g2
				else : 
					curGroup = g2
			
				
		curGroup[1].append(curEntry)
		allEntries.remove(curEntry)
			

	def quadSplit(self, allEntries):
		group1 = (Rect([],[]),[])
		group2 = (Rect([],[]),[])
		i1,i2 = self.pickSeeds(allEntries)
		e1 = allEntries[i1]
		e2 = allEntries[i2]
		group1[1].append(e1)
		group2[1].append(e2)
		
		group1[0].boundingBoxMin.extend(e1.I.boundingBoxMin)		
		group1[0].boundingBoxMax.extend(e1.I.boundingBoxMax)
		group2[0].boundingBoxMin.extend(e2.I.boundingBoxMin)
		group2[0].boundingBoxMax.extend(e2.I.boundingBoxMax)
		
		allEntries.remove(e1)
		allEntries.remove(e2)
		
		while len(allEntries) > 0 : 
			if (len(group1) + len(allEntries)) == self.minEntries : 
				for e in allEntries : 
					group1[1].append(e)
				break

			if (len(group2) + len(allEntries)) == self.minEntries : 
				for e in allEntries : 
					group2[1].append(e)
				break
				
			self.pickNext(allEntries, group1, group2)
		return (group1, group2)
	
	# helper function to easily and quickly swap out split function
	def nodeSplit(self, allEntries):
		return self.quadSplit(allEntries)
							
	def adjustTree(self, path, argN, argNN=None):
		n = argN
		newNode = None
		
		if n == self.root : 
			return (n,argNN)
			
		parent = path.pop()
		
		r = Rect(n.entries[0].I.boundingBoxMin, n.entries[0].I.boundingBoxMax)
		for j in range(1,len(n.entries)) :
			r.includeR(n.entries[j].I)
		for e in parent.entries : 
			if e.child == n : 
				e.I.boundingBoxMin = r.boundingBoxMin
				e.I.boundingBoxMax = r.boundingBoxMax
				break
				
		if argNN is not None: 
			nEntry = Entry(Rect([],[]))
			nEntry.child = argNN
			nEntry.I = Rect(argNN.entries[0].I.boundingBoxMin, argNN.entries[0].I.boundingBoxMax)
			for j in range(1,len(argNN.entries)) :
				#print j, len(argNN.entries)
				nEntry.I.includeR(argNN.entries[j].I)
			if len(parent.entries) < parent.size : 				
				parent.entries.append(nEntry)

			else : 
				newEntries = []
				newEntries.extend(parent.entries)
				newEntries.append(nEntry)
				g1, g2 = self.nodeSplit(newEntries)
				parent.entries = g1[1]
				newNode = Node(parent.size, False)
				newNode.entries = g2[1]
		return self.adjustTree(path, parent, newNode)
			
	def insertRecord(self, rec, depth = -1) :
		root = self.root
		path = [] 
		if rec.nodeId is None : 
			rec.nodeId = self.curId
			self.curId += 1
				
		leaf = self.chooseLeaf(rec, path, depth)
		n = path.pop()
		assert(n == leaf)
		newLeaf = None
		if len(leaf.entries) < leaf.size : 
			leaf.entries.append(rec)		
		else : 
			l = [rec]
			l.extend(leaf.entries)
			g1, g2 = self.nodeSplit(l)
			leaf.entries = g1[1]
			newLeaf = Node(self.root.size, False)
			newLeaf.entries = g2[1]
		r, ar = self.adjustTree(path, leaf, newLeaf)
		if ar is not None : 
			root = Node(self.root.size, True)
			root.entries = []
			e1 = Entry(Rect([],[]))
			r.isRoot = False
			e1.child = r
			e1.I = Rect(r.entries[0].I.boundingBoxMin, r.entries[0].I.boundingBoxMax)
			for i in range(1,len(r.entries)) : 
				e1.I.includeR(r.entries[i].I)

			e2 = Entry(Rect([],[]))
			e2.child = ar
			e2.I = Rect(ar.entries[0].I.boundingBoxMin, ar.entries[0].I.boundingBoxMax)
			for i in range(1,len(ar.entries)) : 
				e2.I.includeR(ar.entries[i].I)
			
			root.entries.append(e1)
			root.entries.append(e2)
		self.root = root

		
	def depthSaveTree(self, n ):
		if n.entries[0].child is None : 
			return n.save()			
		for e in n.entries : 
			eChild = self.depthSaveTree(e.child)
			e.child = eChild
		return n.save()	
		
	
	def saveTree(self):		
		n = self.root
		l = Queue()
		l.put((None, self.root))
		allNodes = []
		while not l.empty() : 
			parEntry, cur = l.get()
			allNodes.append(cur)
				
			if len(cur.entries) > 0 : 
				for e in cur.entries : 
					if e.child is not None: 
						l.put((e, e.child))
						e.child = "0"
			if parEntry is not None : 
				parEntry.child = cur.save()
				if parEntry in self.root.entries : 
					print self.root.entries[0].child
		for n in allNodes : 
			n.save()
		self.save()	
		
	def doLoad(self, fn) : 
		f = open(fn)
		data = f.read()
		f.close()	
		#data = cPickle.dumps(self)
		cPickle.loads(data)
		#self = tree
			 			
			

def countEntries(n):
	if n is None : 
		return 0
	if len(n.entries) == 0 : 
		return 0
	result = 0
	if n.entries[0].child is None : 
		return len(n.entries)
	else :
		for e in n.entries :
			result += countEntries(e.child)
	return result

def insertFromTree(fname, tree):
	f = open(fname)
	for line in f : 
		xmin, ymin, xmax, ymax = map(float, line.strip().split("\t"))
		r = Rect([xmin,ymin], [xmax, ymax])
		rec = Entry(r)
		tree.insertRecord(rec)
	f.close()
	
def insertFromPickle(fname) :
	f = open(fname, "r")
	data = f.read()
	f.close()
	tree = cPickle.loads(data)
	return tree


def insertMain(fn) : 
	tree = RTree(100, 50)
	insertFromTree(fn, tree)
	print "Done inserting .. now pickling.. "
	f = open("RTree.pickled", "w")
	cPickle.dump(tree, f)
	f.close()
	print "all done"

def loadMain():
	f = open("RTree.pickled", "r")
	tree = cPickle.load(f)
	f.close()
	i = 0
	print len(tree.root.entries)
	r = countEntries(tree.root)
	print r
	for e in tree.root.entries : 
		f = open("RTree.pickled."+str(i), "w")
		cPickle.dump(e.child, f)
		f.close()
		print len(e.child.entries)
		e.child = str(i)
		i += 1
	f = open("RTree.pickled.top", "w")
	cPickle.dump(tree, f)
	f.close()
	
def splitFirst():
	f = open("Rtree.pickled.0")
	node = cPickle.load(f)
	f.close()
	i = 0
	for e in node.entries: 
		f = open("RTree.pickled.0."+str(i), "w")
		cPickle.dump(e.child, f)
		f.close()
		e.child = "RTree.pickled.0."+str(i)
		i += 1
	f = open("Rtree.pickled.0", "w")
	cPickle.dump(node, f)
	f.close()
	
