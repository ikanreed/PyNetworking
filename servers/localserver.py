from threading import Lock
from PyNetworking.data.datastructures import shared_object_dictionary,shared_object_list


class localserver:
	def __init__(self):
		self.client_id=0
		self.prefix=255
		self.clients=[]
		self.tracked=shared_object_list(self)
		self.globals=shared_object_dictionary(self)
		self.clientLock=Lock()
	def add_client(self,client):
		with self.clientLock:
			self.client_id+=1
			self.clients.append(client)
		return self.client_id
	def warmup(self, client,filter=None):
		for item in self.tracked:
			#can we get away with this????????
			if filter is None or filter in item.__filter_list__():
				client.remote_add(self, item)
		for key in self.globals.keys():
			client.remote_global_changed(self,key, self.globals[key])
		client.finish_warmup()
	def remote_add(self, sender, item):
		self.tracked.quiet_add(item)
		with self.clientLock:
			for client in self.clients:
				if client!=sender and self.checkFilter(client, item):
					client.remote_add(sender,item)
	def remote_remove(self,sender, id):
		self.tracked.removeId(id)
	
	def checkFilter(self, client, item):
		filter=item.__filter_list__()
		return not filter or filter.intersection(client.filter)
	
	def notify_add(self, item):
		with self.clientLock:
			for client in self.clients:
				if self.checkFilter(client, item):
					client.remote_add(self,item)
	def notify_attribute_updated(self, item, attribute, value):
		if type(item) is int:
			item=self.tracked.getById(item)
		for client in self.clients:
			if self.checkFilter(client, item):
				client.remote_attribute_updated(self, item, attribute, value)
	def remote_attribute_updated(self, sender, item, attribute, value):
		if type(item) is int:
			item=self.tracked.getById(item)
		item.__quiet_setattr__(attribute, value)
		for client in self.clients:
			if client!=sender and self.checkFilter(client, item):
				client.remote_attribute_updated(sender, item, attribute, value)
	def notify_global_changed(self, key,value):
		with self.clientLock:
			for client in self.clients:
				client.remote_global_changed( self, key, value)
	def remote_global_changed(self, owner, key, value):
		with self.clientLock:
			for client in self.clients:
				if client!=owner:
					client.remote_global_changed(owner,key,value)
	def get_by_id(self, id):
		return self.tracked.getById(id)
	def check_in_item(self, item,propogate):
		if item not in self.tracked:
			if propogate:
				self.tracked.append(item)
			else:
				self.tracked.quiet_add(item)
	def shared_method_invoked(self,item, method_id, args, kw):
		for client in self.clients:
			if client.is_remote() and self.checkFilter(client, item):
				client.remote_method_invoked(self,item, method_id,args,kw)
	def remote_method_invoked(self, sender, item, method_id, args, kw):
		if sender.is_remote():
			item.__invoke_shared_method__(method_id, args, kw)
		for client in self.clients:
			if client!=sender and client.is_remote() and self.checkFilter(client, item):
				client.remote_method_invoked(sender,item,method_id, args, kw)
	def is_remote(self):
		return False
	def __str__(self):
		return 'local server (main)'
					

			