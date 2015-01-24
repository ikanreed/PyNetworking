from PyNetworking.clients.client import remoteclient
from threading import Thread,Lock,current_thread
import socket
import time

class ClientListener(Thread):
	def __init__(self, server, port):
		super().__init__()
		self.runlock=Lock()
		self.connection=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.connection.bind( ('', port) )	
		self.connection.settimeout(1)
		self.server=server
		self.connection.listen(1)
		self.closableconnections=[]
		self.creating_thread=current_thread()
	def stop(self):
		with self.runlock:
			#self.connection.shutdown(socket.SHUT_RDWR)
			self.connection.close()
			self.connection=None
			for connection in self.closableconnections:
				try:
					connection.close()
				except:
					raise
	def run(self):
		while self.connection and self.creating_thread.isAlive():
			try:
				with self.runlock:
					if self.connection:
						conn, addr=self.connection.accept()
						added=remoteclient(self.server, conn)
						self.closableconnections.append(conn)
			except socket.timeout:
				pass