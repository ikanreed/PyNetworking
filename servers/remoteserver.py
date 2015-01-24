from PyNetworking.servers.localserver import localserver
from PyNetworking.data.decorators import shared_object
from PyNetworking.data.event import add_item, global_change, attribute_updated, method_invoked
from PyNetworking.data.event import filter_added, filter_removed
from PyNetworking.data.netqueues import InboundThreadQueue,OutboundThreadQueue
from threading import Lock
import time
import socket

from struct import unpack

class remoteserver:
	#remote_add means we tell the remote server to (who views us as a remoteclient) that 
	#we want to add the item, but we do nothing ourselves
	#notify_add is the method that will be called when we get a parsed item from the REAL server.  
	#we then notify each client
	def __init__(self, host, port):
		self.clients=[]
		self.clientLock=Lock()
		self.prefix=255
		self.host=host#for reference if we care
		self.port=port#ditto
		self.connection=None
		self.address=(host,port)
		self.client_id=None
		#super().__init__()
	def connect(self):
		if(self.connection is None):
			self.connection=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.connection.connect(self.address)
			self.connection.setblocking(True)
			#always get our ID
			with self.clientLock:
				self.client_id,=unpack('H',self.connection.recv(2))
				for client in self.clients:
					client.prefix=self.client_id
					client.id=self.client_id
					
			self.inbound=InboundThreadQueue(self, self.connection)
			self.outbound=OutboundThreadQueue(self,self.connection)
			self.inbound.start()
			self.outbound.start()
		else:
			raise Exception('already connected, please be nice and disconnect first')
	def disconnect(self):
		if self.connection:
			time.sleep(0.01)
			self.connection.close()
	def add_client(self,client):
		#global client_id
		with self.clientLock:
			#client_id+=1
			self.clients.append(client)
			#TODO: warmup data to client
		return self.client_id
	def remote_add(self, sender, item):
		for client in self.clients:
			if client!=sender:
				client.remote_add(sender,item)
		if sender in self.clients:
			self.notify_add(item)
	def remote_global_changed(self, sender, key, value):
		for client in self.clients:
			if client!=sender:
				client.remote_global_changed(sender, key, value)
		if sender in self.clients:
			self.notify_global_changed(key,value)
	def notify_add(self, item):
		#super().notify_add(item)
		self.outbound.add_event(add_item(item))
	def notify_global_changed(self, key,value):
		#super().notify_add(item)
		self.outbound.add_event(global_change(key, value))
	def remote_attribute_updated(self, sender, item, attribute_id, value):
		for client in self.clients:
			if client!=sender:
				client.remote_attribute_updated(sender, item, attribute_id, value)
		if sender in self.clients:
			self.outbound.add_event(attribute_updated(item, attribute_id, value))
	def get_by_id(self, key):
		if self.clients:
			return self.clients[0].get_by_id( key)
	def check_in_item(self, item, propogate):
		#we don't have a list, let clients know instead
		for client in self.clients:
			client.check_in_item(item, False)
	def remote_method_invoked(self, sender, item, method_id, args, kw):
		for client in self.clients:
			if client!=sender:
				client.remote_method_invoked(sender, item, method_id, args, kw)
		if sender in self.clients:
			self.outbound.add_event(method_invoked(item, method_id, args, kw))
	def client_filter_added(self, filter):
		self.outbound.add_event(filter_added(filter))
	def client_filter_removed(self,filter):
		self.outbound.add_event(filter_removed(filter))
	def finish_warmup(self):
		for client in self.clients:
			client.warmupcomplete=True
	def is_remote(self):
		return True
	def __str__(self):
		return 'remote server (unknown)'
		
		