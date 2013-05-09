import sys
import pickle
import DiPriQueue

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


def print_rect(r):
	print r.boundingBoxMin, r.boundingBoxMax


# never call this.
def find_overlaps(r, rs):
	res = []
	for s in rs:
		if r.overlaps(s):
			res.append(s)
	return res

# Given rectangles (ie, the return from the search query), make a graph of which rectangles overlap.
# g is the connectivity graph, and w is the weights to get from A to B.
#
# Note that "find_overlaps" is MISERABLE, because it makes everything quadratic.
# That should (hopefully) be replaced with R-tree search queries, which I've commented below.
def build_graph(rects):
    g = {}
    w = {}
    #i = 0
    for r in rects:
	#i += 1
	#if i % 100 == 0:
		#print i
        g[r] = []
	# for v in rtree.search(r):
	for v in find_overlaps(r, rects):
            g[r].append(v)

	    # add other direction when we loop around.
            w[(r,v)]= r.getVolume()
    return g, w

# given a rectangle s, find a rectangle that contains s
# (in other words, s may not actually be in the R-tree, so find the ``nearest'' actual node.
# this is yet-untested.
def make_leaf(s):
    d = 1
    while len(rtree.search(s)) == 0:
	s.boundingBoxMin = [s.boundingBoxMin[0]-d,s.boundingBoxMin[1]-d]
	s.boundingBoxMax = [s.boundingBoxMax[0]+d,s.boundingBoxMax[1]+d]
        d *=2 
    # ok, should get rid of this redundant call
    return rtree.search(r)[0]





# what's the shortest path from S to T?
# note: S and T MUST be actual rectangles in G (ie, leaves).
# to get S and T from arbitrary input, use "make_leaf"
def shortest_path(graph, w, s, t):
    Q = DiPriQueue.DiPriQueue()

    # to get to t, first we get to prev[t]
    prev = {}
    # surprisingly quick (~2 secs) for 20k graph.
    for v in graph:
        Q.add_task(v, float("inf"))
 
    Q.add_task(s, 0)

    while len(Q) > 0:
	udist, u = Q.pop_task()

	# if we found our target we're done.
        if u == t:
            return prev
        # if we could not find our target we're done.
        if udist == float("inf"):
            break

        # for every neighbor of our next-closest node, see
	# if that improves any of our best-paths computation.
        for v in graph[u]:
            alt = udist + w[(u,v)]
            if alt < Q.get_dist(v):
		Q.remove_task(v)
		Q.add_task(v, alt)
                prev[v] = u
    # return the chain of links we've generated.
    return prev

# work backwards from t to s.
# the list returned is the rectangle we want to "highlight".
# if length 1, that means we couldn't find a path.
def extract_path(p, s, t):
    path = []
    toprint = t
    while toprint != s:
	path.append(toprint)
	if toprint in p:
		toprint = p[toprint]
	else:
		# if we only have a partial path
		return path
    # if we have a full path.
    path.append(toprint)
    return path

# dead stupid.
def print_path(p):
	for r in p:
		print_rect(r)

# The first 4 lines (not counting comments) are untested, really just psuedocode.
# Sorry! :(
# Returns the list of rectangles comprising our path.
def PathSearch(s, t):
	# untested commands :(
	sleaf = make_leaf(s)
	rleaf = make_leaf(r)
	# that is to say, area_to_search is our "actual" search query.
	area_to_search = (s, t)
	graph_rectangles = rtree.search(area_to_search)

	# this and the following lines use tested code.
	g, w = make_graph(graph_rectangles)
	previous = shortest_path(g, w, sleaf, rleaf)

	# a list of rect objects.
	result = extract_path(previous, sleaf, rleaf)
	return result

if __name__ == "__main__":
	g = pickle.load(open('graphfile'))
	w = pickle.load(open('weightfile'))
	#some example rectangles:
	#R1 and R2 give a nice little path, and R3 is a failure example
	#Note: on failure, path is empty (just s).
	R1 = Rect([-122.259,37.8368],[-122.259,37.8374])
	R2 = Rect([-122.258,37.8344],[-122.258,37.8352])
	R3 = Rect([-121.704,37.6219],[-121.703,37.6219])
	print_path(extract_path(shortest_path(g, w, R1, R2), R1, R2))
