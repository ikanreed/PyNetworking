from PyNetworking.data.decorators import shared_object
from threading import Lock


class shared_object_list:
	def __init__(self, owner):
		self.owner=owner
		self.items=[]
		self.indexes={}
		#self.types={}
		self.lock=Lock()
	def __getitem__(self, index):
		return self.items[index]
	def getById(self, id):
		if id in self.indexes:
			return self.items[self.indexes[id]]
	def __len__(self):
		return len(self.items)
	def extend(self, items):
		for item in items:
			self.append(item)
	def __iter__(self):
		return iter(self.items)
	def __contains__(self, item):
		return item.__get_shared_id__() in self.indexes
	def removeId(self, id):
		with self.lock:
			if id in self.indexes:
				item=self.items.pop(self.indexes[id])
				del self.indexes[id]
				i=0
				#gotta reindex, that sucks.  why'd you go and do that
				for item in self.items:
					self.indexes[item.__get_shared_id__()]=i
					i+=1
				"""if item.UnderlyingType() in self.types:
					self.types[item.UnderlyingType()].remove(item)"""
	def remove(self, item):
		if hasattr(item, '__get_shared_id__'):
			self.removeId( item.__get_shared_id__())
			self.owner.notify_remove(item.__get_shared_id__())
			
	def quiet_add(self, item):
		if item.__owner__ is None:
			item.__owner__=self.owner
		if item.__get_shared_id__() in self.indexes:
			return
		'''for key in item.__classWrapper__.shared_attributes:
			value=getattr(item, key)
			if hasattr(value, '__get_shared_id__') and value.__get_shared_id__ not in self.indexes:
				self.append(value)'''
		with self.lock:
			id=item.__get_shared_id__()
			location=len(self.items)
			self.items.append(item)
			self.indexes[id]=location
			"""if(type(item) in self.types):
				self.types[item.UnderlyingType()].append(item)
			else:
				self.types[item.UnderlyingType()]=[item]"""
	def append(self, item):
		if hasattr(item,'__get_shared_id__'):

			self.quiet_add(item)
			self.owner.notify_add(item)
		else:
			raise Exception('unable to store non-decorated objects')
	def pop(self, index):
		result=self[index]
		self.remove(result)
		return
	def __str__(self):
		return 'shared[%s]'%self.items

class shared_object_dictionary:
	def __init__(self, owner):
		self.list=owner.tracked
		self.dictionary={}
		self.owner=owner
	def __len__(self):
		return len(self.dictionary)
	def __getitem__(self, key):
		return self.dictionary[key]
	def get(self, arg, default=None):
		return self.dictionary.get(arg,default)
	def quiet_set(self, key, value):
		if key in self.dictionary:
			value=self.dictionary[key]
			#self.list.removed(value)
		if(value not in self.list):
			self.list.quiet_add(value)
		self.dictionary[key]=value
	def __setitem__(self, key,value):
		self.quiet_set(key,value)
		self.owner.notify_global_changed(key, value)
	def __contains__(self, arg):
		return arg in self.dictionary
	def keys(self):
		return self.dictionary.keys()
	def values(self):
		return self.dictionary.values()
	def items(self):
		return self.dictionary.items()
	def quiet_del(self,key):
		value=self.dictionary.get(key, None)
		del self.dictionary[key]
		if value:
			self.list.remove(value)
	def __delitem__(self, key):
		if key in self.dictionary:
			value=self.dictionary[key]
			self.quiet_del(key)
			self.owner.notify_global_changed(key, None)
		