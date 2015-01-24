from PyNetworking.data.event import Translator
import time
from threading import Lock, Thread, current_thread
from struct import pack, unpack

#parses and notifies server of changes
class InboundThreadQueue(Thread):
	def __init__(self, server, connection, notify=False):
		self.translator=Translator(server)
		super().__init__()
		self.creating_thread=current_thread()
		self.running=True
		self.server=server
		self.connection=connection
		self.buffer=b''
		self.notify=notify
		if self.connection is None:
			raise Exception('not connected')
	def run(self):
		try:
			while self.connection and self.creating_thread.isAlive():
				newdata=self.connection.recv(1024)
				if len(newdata)>0:
					self.buffer+=newdata
					self.clearbuffer()
				else:
					break
		except ConnectionResetError as e:
			pass
		except ConnectionAbortedError as e:
			pass
		#raise other exceptions, but let us die
		except:
			self.running=False
			raise
		self.running=False
	def clearbuffer(self):
		data=True
		while data and len(self.buffer)>2:
			expectedLength,=unpack('H',self.buffer[:2])
			if len(self.buffer)>=expectedLength:
				parsed_event=self.translator.translate_binary_event(self.buffer[:expectedLength])
				self.buffer=self.buffer[expectedLength:]
				parsed_event.apply_to(self.server,self.notify)
			else:
				data=False
class OutboundThreadQueue(Thread):
	def __init__(self, server, connection):
		super().__init__()
		self.server=server
		self.translator=Translator(server)
		self.creating_thread=current_thread()
		self.connection=connection
		self.itemqueue=[]
		self.pending={}
		self.queuelock=Lock()
		self.allsent=0
		if self.connection is None:
			raise Exception('not connected')
	
	def run(self):
		try:
			while self.server.connection and self.server.inbound.running and self.creating_thread.isAlive():
				#safe to read here, queue will never be emptied without our permission
				while self.itemqueue:
					item=None
					with self.queuelock:
						if self.itemqueue:
							item=self.dequeue()
					if item:
						self.send(item)
				time.sleep(0)
		except ConnectionResetError:
			pass
		except RuntimeError:
			pass
			

	def add_event(self, event):
		eventid=event.unique_id()
		with self.queuelock:
			if eventid in self.pending and event.isReplaceable:
				removed=self.pending[eventid]
				index=self.itemqueue.index(removed)
				self.itemqueue[index]=event
				self.pending[eventid]=event
			else:
				self.pending[eventid]=event
				self.itemqueue.append(event)
	def send(self, item):
		binary=self.translator.translate_event(item)
		sent=self.connection.send(binary)
		if sent==0:
			raise RunTimeError('connection lost')
		self.allsent+=sent
	def dequeue(self):
		item=self.itemqueue.pop(0)
		if item.unique_id() in self.pending:
			del self.pending[item.unique_id()]
		return item

		
