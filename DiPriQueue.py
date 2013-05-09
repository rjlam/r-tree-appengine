# largely copied from http://docs.python.org/2/library/heapq.html, modified slightly for our purposes (eg made a class)

import itertools
from heapq import *

class DiPriQueue:
	def __init__(self):
		self.pq = []                         # list of entries arranged in a heap
		self.entry_finder = {}               # mapping of tasks to entries
		self.REMOVED = '<removed-task>'      # placeholder for a removed task
		self.counter = itertools.count()     # unique sequence count
		self.dist = {}

	def add_task(self, task, priority=0):
		'Add a new task or update the priority of an existing task'
		if task in self.entry_finder:
			self.remove_task(task)
		count = next(self.counter)
		entry = [priority, count, task]
		self.entry_finder[task] = entry
		self.dist[task] = priority
		heappush(self.pq, entry)

	def remove_task(self, task):
		'Mark an existing task as REMOVED.  Raise KeyError if not found.'
		entry = self.entry_finder.pop(task)
		entry[-1] = self.REMOVED

	def pop_task(self):
		'Remove and return the lowest priority task. Raise KeyError if empty.'
		while self.pq:
			priority, count, task = heappop(self.pq)
			if task is not self.REMOVED:
				del self.entry_finder[task]
				return priority, task
		raise KeyError('pop from an empty priority queue')
	def get_dist(self, v):
		return self.dist[v]
	
	def __len__(self):
		return len(self.pq)
