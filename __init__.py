from PyNetworking.clients.client import localclient, remoteclient
from PyNetworking.servers.localserver import localserver
from PyNetworking.servers.remoteserver import remoteserver
from PyNetworking.data.decorators import shared_class, shared_attribute, shared_method, server_attribute, server_method
from PyNetworking.data.hosting import ClientListener
import time

def make_server(port):
	server=localserver()
	clientlistener=ClientListener(server, port)
	clientlistener.start()
	return server
def make_client(address, port):
	server=remoteserver(address,port)
	client=localclient(server)
	server.connect()
	#wait for warmup
	while not client.warmupcomplete:
		time.sleep(0.01)
	return client