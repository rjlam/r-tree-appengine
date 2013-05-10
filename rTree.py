#!/usr/bin/env python
#
# Copyright Cathrin Weiss (cweiss@cs.wisc.edu), 2013
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#	 http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import sys
import os
from Queue import Queue
from google.appengine.api import memcache, users
from google.appengine.ext import db, webapp
import cPickle


class Rect :
	boundingBoxMin = []
	boundingBoxMax = []
	
#	def __init__(self):
#		self.boundingBoxMin = []
#		self.boundingBoxMax = []
		
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
		#if c is not None : 
		#	self.child = c.save()
 
	def getChild(self):
		if self.child is None : 
			return None
		if type(self.child) == type(Node(None)) : 
			return self.child
		dbn = memcache.get(str(self.child))
		wasMemcached = True
		if not dbn: 
			wasMemcached = False
			dbn = DBNode.get_by_id(self.child)
		if dbn is not None : 
			if not wasMemcached : 
				memcache.add(str(self.child), dbn, 3600)
			return Node(dbn)
		return None
		
#########				
class Node : 
	
	size = 0
	entries = []
	isRoot = False
	dbn = None
	
	def __init__(self, dbNode, s = None, root = False):
		if dbNode is None : 
			self.entries = []
			self.size = s
			self.isRoot = root
		else : 
			self.dbn = dbNode
			self.entries = cPickle.loads(dbNode.entries)
			self.size = dbNode.size
			self.isRoot = dbNode.isRoot	
		
	def search(self, s):
		l = []
		if len(self.entries) > 0 : 
			ent = Entry(self.entries[0].I, self.entries[0].nodeId, self.entries[0].child)
			if ent.getChild() is None : 
				for e in self.entries : 
					ent = Entry(e.I, e.nodeId, e.child)
					if ent.I.overlaps(s.I) : 
						l.append(ent)
			else : 
				for e in self.entries : 
					ent = Entry(e.I, e.nodeId, e.child)
					l2 = ent.getChild().search(s)
					for item in l2 : 
						l.append(item)
		return l
		
	def save(self):
		if self.dbn is None: 
			self.dbn = DBNode(size=self.size, isRoot=self.isRoot)		
		self.dbn.entries = cPickle.dumps(self.entries)
		self.dbn.put()
		memcache.add(str(self.dbn.key().id()), self.dbn, 3600)
		return self.dbn.key().id()
				
###########

class DBMetaData(db.Model):
	rootId = db.IntegerProperty()
	minEntries = db.IntegerProperty()
	curId = db.IntegerProperty()

def getMeta(): 
	dbm = memcache.get("metadata")
	if dbm is None : 
		dbm = DBMetaData.get_by_key_name("metadata")
		if dbm is None :
			return None
		memcache.add("metadata", dbm, 3600)
	return dbm
			
		
class RTree : 
	root = None
	minEntries = None
	curId = 0
	rootKey = None
	
	def __init__(self, pageSize = None , mE = None):
		if pageSize is None and mE is None : 
			dbm = getMeta()
			self.rootKey = dbm.rootId
			self.minEntries = dbm.minEntries
			self.curId = dbm.curId
			dbn =  memcache.get(str(self.rootKey))
			if dbn is None : 
				dbn = DBNode.get_by_id(self.rootKey)
			self.root = Node(dbn)
		else : 
			self.root = Node(None, pageSize, True)
			self.minEntries = mE
			self.curId = 0		
			self.root.save()		

	def save(self):
		if self.rootKey is None :
			self.rootKey = self.root.save()
		dbm = DBMetaData(rootId = self.rootKey, minEntries=self.minEntries, curId=self.curId, key_name="metadata")
		dbm.put()
		memcache.add("metadata", dbm, 3600)
	
	def chooseLeaf(self, newEntry, path, depth=-1):
		n = self.root
		d = 1		
		while True : 
			path.append(n)
			if len(n.entries) : 				
				if n.entries[0].getChild() is None : 
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
				n = curEntry.getChild()
					
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
		n.save()
		if n == self.root : 
			return (n,argNN)
			
		parent = path.pop()
		
		r = Rect(n.entries[0].I.boundingBoxMin, n.entries[0].I.boundingBoxMax)
		for j in range(1,len(n.entries)) :
			r.includeR(n.entries[j].I)
		for e in parent.entries : 
			if e.getChild() == n : 
				e.I.boundingBoxMin = r.boundingBoxMin
				e.I.boundingBoxMax = r.boundingBoxMax
				break
				
		if argNN is not None: 
			nEntry = Entry(Rect([],[]))
			childVal = argNN.save()
			nEntry.child = childVal
			nEntry.I = Rect(argNN.entries[0].I.boundingBoxMin, argNN.entries[0].I.boundingBoxMax)
			for j in range(1,len(argNN.entries)) :
				nEntry.I.includeR(argNN.entries[j].I)
			if len(parent.entries) < parent.size : 				
				parent.entries.append(nEntry)
			else : 
				newEntries = []
				newEntries.extend(parent.entries)
				newEntries.append(nEntry)
				g1, g2 = self.nodeSplit(newEntries)
				parent.entries = g1[1]
				newNode = Node(None, self.root.size)
				newNode.entries = g2[1]
			parent.save()
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
			newLeaf = Node(None, self.root.size, False)
			newLeaf.entries = g2[1]
		r, ar = self.adjustTree(path, leaf, newLeaf)
		if ar is not None : 
			root = Node(None, self.root.size, True)
			root.entries = []
			e1 = Entry(Rect([],[]))
			r.isRoot = False
			ar.isRoot = False
			e1.child = r.save()
			e1.I = Rect(r.entries[0].I.boundingBoxMin, r.entries[0].I.boundingBoxMax)
			for i in range(1,len(r.entries)) : 
				e1.I.includeR(r.entries[i].I)

			e2 = Entry(Rect([],[]))
			e2.child = ar.save()
			e2.I = Rect(ar.entries[0].I.boundingBoxMin, ar.entries[0].I.boundingBoxMax)
			for i in range(1,len(ar.entries)) : 
				e2.I.includeR(ar.entries[i].I)
			
			root.entries.append(e1)
			root.entries.append(e2)
			
		self.root = root
		self.rootKey = self.root.save()


	### DELETE
	
	def printLeaves(self, n):
		print "class leaf printing"
		if len(n.entries) == 0 : 
			print "empty!"
			return
		if n.entries[0].getChild() is None : 
			for e in n.entries : 
				print e.nodeId
				print e.I.boundingBoxMin
				print e.I.boundingBoxMax
		print "done"
		
	def findLeaf(self, path, n, rec):
		p = []
		p.extend(path)
		p.append(n)
		if len(n.entries) > 0 and n.entries[0].getChild() is None : 
			for e in n.entries : 
				if e.I == rec.I : 
					return (n,p)			
			return (None, None)

		for e in n.entries : 
			if e.I.overlaps(rec.I) :
				res = self.findLeaf(p,e.getChild(), rec)
				if res is not None : 
					l,lp = res
					if l is not None : 
						return (l,lp)
		return (None, None)
		
	def condenseTree(self, path, leaf):
		n = leaf
		depth = len(path)
		d = depth
		m = path.pop()
		assert(m==n)
		q = set()		
		while True : 
			if self.root == n : 
				break
			p = path.pop()
			en = None
			for e in p.entries : 
				if e.getChild() == n : 
					en = e
			if len(n.entries) < self.minEntries : 
				p.entries.remove(en)
				q.add((n,d))
			else : 
				en.I = Rect(n.entries[0].I.boundingBoxMin, n.entries[0].I.boundingBoxMax)
				for i in range(1,len(n.entries)) : 
					en.I.includeR(n.entries[i].I)
			n = p
			d -= 1
		for n,d in q : 
			print "here! in Q.", len(q)
			if d == depth : 
				print d, depth
				for e in n.entries : 
					print e.nodeId, e.I.boundingBoxMin, e.I.boundingBoxMax, " , ", d
					self.insertRecord(e)
					
			else : 
				print "other: ", len(n.entries), " , " 
				for e in n.entries : 
					print e.nodeId, e.I.boundingBoxMin, e.I.boundingBoxMax, " , ", d
					self.insertRecord(e, d)
					
	
				
			
	def deleteRecord(self, rec):
		path = []
		res = self.findLeaf(path, self.root, rec)
		if res is None or res[0] is None : 
			return False
		result = False
		leaf,lPath = res
		if leaf is not None: 
			for e in leaf.entries : 
				if e.I == rec.I : 
					leaf.entries.remove(e)
					result = True
					break
			self.condenseTree(lPath, leaf)
			if len(self.root.entries) == 1 and self.root.entries[0].getChild() is not None: 
				self.root.I = self.root.entries[0].getChild()
				self.root.isRoot = True
		return result
		
	### SEARCH
	def search(self, rec):
		return self.root.search(rec)
		
	def printTree(self):
		print "Level: 1 , Root"
		n = self.root
		i = 2
		l = Queue()
		l.put((self.root,1))
		level = 1
		s = "   "
		while not l.empty() :
			cur, lev = l.get()
			for i in range(0, lev): 
				s += "  "
			if lev > level: 
				print "Level: ", lev
				level = lev
			if len(cur.entries) > 0 : 
				for e in cur.entries : 
					if e.getChild() is not None : 
						l.put((e.getChild(), lev+1))
				entr = ""
				for e in cur.entries : 
					entr += str(e.I.boundingBoxMin) + "," +str(e.I.boundingBoxMax) + " ; "
				print s , "E:",len(cur.entries)	,entr
		
	
		
def printLeaves(n, depth=1):
	if n is None : 
		return
	if len(n.entries) == 0 : 
		print "empty!"
		return
	if n.entries[0].getChild() is None : 
		for e in n.entries : 
			print e.nodeId, " depth: ", depth
			print e.I.boundingBoxMin
			print e.I.boundingBoxMax
	else :
		for e in n.entries :
			printLeaves(e.getChild(), depth+1)

def countEntries(n):
	if n is None : 
		return 0
	if len(n.entries) == 0 : 
		return 0
	result = 0
	ent = Entry(n.entries[0].I, n.entries[0].nodeId, n.entries[0].child)
	if ent.getChild() is None : 
		return len(n.entries)
	else :
		for e in n.entries :
			ent = Entry(e.I, e.nodeId, e.child)
			result += countEntries(ent.getChild())
	return result

entryList = []	
def getEntries(n):	
	if n is None : 
		return
	if len(n.entries) == 0 : 
		return
	ent = Entry(n.entries[0].I, n.entries[0].nodeId, n.entries[0].child)
	if ent.getChild() is None : 
		for e in n.entries :
			entryList.append(Entry(e.I, e.nodeId, e.child))
	else :
		for e in n.entries :
			ent = Entry(e.I, e.nodeId, e.child)
			getEntries(ent.getChild())
	return
	
def insertFromTree(fname, tree):
	f = open(fname)
	for line in f : 
		xmin, ymin, xmax, ymax = map(float, line.strip().split("\t"))
		r = Rect([xmin,ymin], [xmax, ymax])
		rec = Entry(r)
		tree.insertRecord(rec)
	f.close()		


	
				
