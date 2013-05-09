import sys
import pickle
#from rTree import *

# pageSize = 100
# minEntries = 50
# 
# meta = DBMetaData.get_by_key_name("metadata")
# # not initialized yet 
# if not meta : 
# 	tree = RTree(pageSize, minEntries)
# 	tree.save()
# # we already have an RTree, grab the root
# else :
# 	tree = RTree(None, None)
# 
# print "About to insert"
# fileName = "CaStreet.ascii"
# # the file is assumed to be of the form "x_min\ty_min\tx_max\ty_max\n"
# insertFromTree(fileName, tree)
# print "Done inserting"
# 
# searchRec = Entry(Rect([6, 4],[10,6]))
# searchRec = Entry(Rect([-121.7,37.59], [122.2,37.8]))
# results = tree.search(searchRec)
# print results

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
	def __hash__(self):
		        return hash((tuple(self.boundingBoxMin), tuple(self.boundingBoxMax)))


def print_rect(r):
	print r.boundingBoxMin, r.boundingBoxMax

g = pickle.load(open('graphfile'))
w = pickle.load(open('weightfile'))

# given a point s, find a rectangle that contains s
def make_leaf(g, s):
    d = 1
    while len(rtree.search(s)) == 0:
	s.boundingBoxMin = [s.boundingBoxMin[0]-d,s.boundingBoxMin[1]-d]
	s.boundingBoxMax = [s.boundingBoxMax[0]+d,s.boundingBoxMax[1]+d]
        d *=2 
    # ok, should get rid of this redundant call
    return rtree.search(r)[0]




for r in g[Rect([-122.259,37.8368],[-122.259,37.8374])]:
	print_rect(r)
	print
	print "==========="
for r in g[Rect([-122.259,37.8362],[-122.259,37.8368])]:
	print_rect(r)
	print
print "==========="
for r in g[Rect([-122.259,37.8359],[-122.257,37.8362])]:
	print_rect(r)
	print
print "==========="
for r in g[Rect([-122.258,37.8352],[-122.257,37.8359])]:
	print_rect(r)
	print
print "==========="
for r in g[Rect([-122.258,37.8344],[-122.258,37.8352])]:
	print_rect(r)
	print


def mindist(Q, dist):
    distmap = [(a, dist[a]) for a in Q]
    minpair = distmap[0]
    for pair in distmap:
        #print pair, minpair
        if pair[1] < minpair[1]:
            #print pair
            minpair = pair
    return minpair[0]


def shortest_path(graph, w, s, t):
    dist = {}
    prev = {}
    for v in graph:
        dist[v] = float("inf")
 
    dist[s] = 0
    Q = map (lambda k : (dist[k], k), graph.keys())
    #Q = list(graph.keys())[:]

    while len(Q) > 0:
        u = mindist(Q,dist)
        #print u, Q
        Q.remove(u)
        #print Q

        if u == t:
            return prev
        if dist[u] == float("inf"):
            break

        for v in graph[u]:
            alt = dist[u] + w[(u,v)]
            if alt < dist[v]:
                dist[v] = alt
                prev[v] = u
    return prev

print "??????????????????????" 
def extract_path(p, s, t):
    print len(p)
    toprint = t
    #i = 0
    while toprint != s:
	i += 1
        print_rect(toprint)
	print
	if toprint in p:
	        toprint = p[toprint]
	else:
		break
    #print_rect(s)
    #print i

#extract_path(shortest_path(test_graph, test_w, 1, 5), 1, 5)

R1 = Rect([-122.259,37.8368],[-122.259,37.8374])
R2 = Rect([-122.258,37.8344],[-122.258,37.8352])
extract_path(shortest_path(g, w, R1, R2), R1, R2)
