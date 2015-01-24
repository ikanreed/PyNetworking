from PyNetworking.data.datastructures import shared_object_list,shared_object_dictionary
from PyNetworking.data.netqueues import InboundThreadQueue,OutboundThreadQueue
from PyNetworking.data.event import add_item, global_change,attribute_updated,method_invoked,warmup_complete

from struct import pack

class localclient:
	server=None
	tracked=[]
	def __init__(self, server):
		self.filter=set()
		self.server=server
		self.tracked=shared_object_list(self)
		self.prefix=self.server.add_client(self)
		self.id=self.prefix
		self.globals=shared_object_dictionary(self)
		self.warmupcomplete=False
	def disconnect(self):
		self.server.disconnect()
	def notify_add(self, item):
		self.server.remote_add(self,item)
	def notify_remove(self,id):
		self.server.remote_remove(self, id)
	def notify_global_changed(self, key, value):
		self.server.remote_global_changed(self,key,value)
	def remote_add(self, sender,item):
		#a remote machine has added an item
		self.tracked.quiet_add(item)
	def remote_remove(self, sender,id):
		#we only get ids for delete operations
		self.tracked.removeId(id)
	def notify_attribute_updated(self,item,attribute_id, value):
		self.server.remote_attribute_updated(self, item,attribute_id, value)
	def remote_attribute_updated(self, sender, item,attribute_id, value):
		item.__quiet_setattr__(attribute_id, value)
	def remote_global_changed(self,sender, key,value):
		if(value is None):
			self.globals.quiet_del(key)
		else:
			self.globals.quiet_set(key, value)
	def get_by_id(self,id):
		return self.tracked.getById(id)
	def check_in_item(self, item,propogate):
		if item not in self.tracked:
			if propogate:
				self.tracked.append(item)
			else:
				self.tracked.quiet_add(item)
	def shared_method_invoked(self, item, method_id, args, kw):
		self.server.remote_method_invoked(self, item, method_id, args, kw)
	def remote_method_invoked(self,sender, item, method_id, args, kw):
		if sender.is_remote():
			item.__invoke_shared_method__(method_id,args,kw)
	
	def add_filter(self, filter):
		self.filter.add(filter)
		self.server.client_filter_added( filter)
	def remove_filter(self, filter):
		self.filter.remove(filter)
		self.server.client_filter_removed( filter)
	def finish_warmup(self):
		self.warmupcomplete=True
	def is_remote(self):
		return False
	
	def __str__(self):
		return 'local client(%i)'%self.prefix
	
	
		
class remoteclient:
	def __init__(self, server, connection):
		self.connection=connection
		self.connection.setblocking(True)
		self.server=server
		self.prefix=self.server.add_client(self)
		self.id=self.prefix
		self.filter=set()
		self.connection.send(pack('H',self.prefix))
		self.inbound=InboundThreadQueue(self, self.connection,True)
		self.outbound=OutboundThreadQueue(self,self.connection)
		self.inbound.start()
		self.outbound.start()
		self.warmupcomplete=False
		#send us everything we might have missed, dog
		self.server.warmup(self)
		
	def notify_add(self, item):
		self.server.remote_add(self,item)
	def notify_remove(self,id):
		self.server.remote_remove(self, id)
	def notify_global_changed(self, key, value):
		self.server.remote_global_changed(self,key,value)
	def remote_add(self, sender,item):
		self.outbound.add_event(add_item( item))
	def remote_remove(self, sender,id):
		#we only get ids for delete operations
		self.outbound.add_event(event.remove(sender, id))
	def remote_attribute_updated(self, sender, item, attribute, value):
		self.outbound.add_event(attribute_updated(item, attribute, value))
	def notify_attribute_updated(self, item, attribute_id, value):
		self.server.remote_attribute_updated(self, item, attribute_id, value)
	def remote_global_changed(self,sender, key,value):
		#sender is no longer of interest, remote system will propogate with our id remotely
		self.outbound.add_event(global_change(key, value))
	def get_by_id(self, id):
		return self.server.get_by_id(id)
	def check_in_item(self, item,propogate):
		self.server.check_in_item(item,propogate)
	def shared_method_invoked(self, item, method_id, args, kw):
		self.server.remote_method_invoked(self, item, method_id,args,kw)
	def remote_method_invoked(self, sender, item,method_id,args,kw):
		self.outbound.add_event(method_invoked(item,method_id,args,kw))
	def filter_added(self, filter):
		self.filter.add(filter)
		self.server.warmup(self,filter)
	def filter_removed(self, filter):
		self.filter.remove(filter)
	def finish_warmup(self):
		warmupcomplete=True
		self.outbound.add_event(warmup_complete())
	def is_remote(self):
		return True
	def __str__(self):
		return 'remote client(%i)'%self.prefix