import unittest
import sys
import threading
#these tests depend on sleep.  name of the game
import time

from PyNetworking import localclient, localserver, shared_class, shared_attribute, shared_method, server_attribute, server_method, remoteserver, ClientListener
#a client is a simple object that manages communication to the server.  It does all the heavy lifting of synchronizing data.
#a localserver is a server that is running on THIS machine.   It specifically ALSO does the work of updating the game model
#a shared_class is one that has shared_data 

@shared_class
class Channel:
	def __init__(self):
		self.backlog=[]
	@shared_method
	def send_message(self,sender,message):
		self.backlog.append((sender,message))

@shared_class
class Location:
	x=shared_attribute(None) 
	y=shared_attribute(None)
	def __init__(self,x=0,y=0):
		self.x=x
		self.y=y
	def __str__(self):
		return 'x:%i.y:%i'%(self.x,self.y)
@shared_class
class Rectangle:
	upperleft=shared_attribute(None)
	lowerright=shared_attribute(None)
	def __init__(self, upperleft=Location(0,0), lowerright=Location(0,0)):
		self.upperleft=upperleft
		self.lowerright=lowerright
	
	def __str__(self):
		return 'Rectangle[%s,%s]'%(str(self.upperleft),str(self.lowerright))

@shared_class
class Filterable:
	category=shared_attribute(None)
	data=shared_attribute(None)
	def __init__(self, category=None,data=None):
		self.category=category
		self.data=data
	def __filter_list__(self):
		if self.category:
			return (self.category, )
		return None

"""class TestLocalConnection(unittest.TestCase):
	def setUp(self):
		self.test_server=localserver()
		self.test_client1=localclient(self.test_server)
		self.test_client2=localclient(self.test_server)
	
	def test_shared_method(self):
		#begin the process of tracking a channel
		self.test_server.globals['Text_Channel']=Channel()
		self.test_client1.globals['Text_Channel'].send_message('test_client1','this was added to the chat')
		self.assertEqual(self.test_client2.globals['Text_Channel'].backlog[0],('test_client1','this was added to the chat'))
		del self.test_client2.globals['Text_Channel']
		self.assertEqual(len(self.test_client1.globals),0)
	
	def test_shared_data(self):
		added=Location(10,11)
		self.test_client1.tracked.append(added)
		self.assertEqual(self.test_client2.tracked[0].x,10)"""
		
		
class TestRemoteConnection(unittest.TestCase):
	def setUp(self):
		self.server=localserver()
		self.clientlistener=ClientListener(self.server, 3030)
		self.clientlistener.start()
		self.localconn=localclient(self.server)
		
		self.remoteconn=remoteserver('127.0.0.1',3030)
		self.remoteconnclient=localclient(self.remoteconn)
		self.remoteconn.connect()
	
	def test_channel(self):
		print('\nstarting test_channel\n')
		self.localconn.globals['Channel']=Channel()
		time.sleep(0.01)
		self.assertEqual(len(self.remoteconnclient.globals),1)
		self.assertEqual(self.remoteconnclient.globals['Channel'].backlog,[])
		self.remoteconnclient.globals['Channel2']=Channel()
		time.sleep(0.01)
		self.assertTrue('Channel2' in self.localconn.globals)
	def test_shared_data(self):
		print('\nstarting test_shared_data\n')
		added=Location(20,30)
		self.localconn.tracked.append(added)
		time.sleep(0.01)
		self.assertEqual(len(self.remoteconnclient.tracked),1)
		self.assertEqual(self.remoteconnclient.tracked[0].x,20)
		added.x=21
		time.sleep(0.01)
		self.assertEqual(self.remoteconnclient.tracked[0].x,21)
		self.remoteconnclient.tracked[0].x=24
		time.sleep(0.01)
		self.assertEqual(added.x,24)
		
	def test_tree_objects(self):
		print('\nstarting test_tree_objects\n')
		tested=Rectangle(Location(0,0),Location(1,2))
		self.localconn.globals['Rectangle']=tested
		time.sleep(0.01)
		self.assertEqual(self.remoteconnclient.globals['Rectangle'].lowerright.y,2)
		tested.upperleft=Location(-10,10)
		time.sleep(0.01)
		self.assertEqual(self.remoteconnclient.globals['Rectangle'].upperleft.x,-10)
		self.assertTrue(self.remoteconnclient.globals['Rectangle'].upperleft in self.remoteconnclient.tracked)
		self.remoteconnclient.globals['Rectangle'].upperleft.x=-9
		time.sleep(0.01)
		self.assertEqual(tested.upperleft.x,-9)
	
	def test_performance(self):
		print('\nstarting test performance\n')
		start=time.time()
		tested=Location()
		self.localconn.globals['Location']=tested
		time.sleep(0.01)
		for i in range(12000):
			tested.x=i
		while self.remoteconnclient.globals['Location'].x<999:
			pass
		duration=time.time()-start
		print(duration)
		self.assertTrue(duration<2)
		
	def test_shared_method(self):
		print('\nstarting test shared method\n')
		self.localconn.globals['Channel']=Channel()
		self.localconn.globals['Channel'].send_message('player 1', 'Hey turd breath')
		time.sleep(0.01)
		self.assertEqual(self.remoteconnclient.globals['Channel'].backlog[0],('player 1','Hey turd breath'))
		self.remoteconnclient.globals['Channel'].send_message('player 2','You are going to get turdally owned')
		time.sleep(0.01)
		self.assertEqual(self.localconn.globals['Channel'].backlog[1][0],'player 2')
	def test_server_instigation(self):
		print('\ntesting server instigation\n')
		self.server.globals['Rectangle']=Rectangle(Location(15,15),Location(12,12))
		time.sleep(0.01)
		self.assertEqual(self.remoteconnclient.globals['Rectangle'].upperleft.x,15)
		self.server.globals['Channel']=Channel()
		self.server.globals['Channel'].send_message('server','hello players')
		time.sleep(0.01)
		self.assertEqual(len(self.remoteconnclient.globals['Channel'].backlog),1)
		self.server.globals['Rectangle'].upperleft.x=20
		time.sleep(0.01)
		self.assertEqual(self.remoteconnclient.globals['Rectangle'].upperleft.x,20)
	
	def test_warmup(self):
		print('\nstarting test_warmup \n')
		self.server.globals['warmuppoint']=Location(14,18)
		newconn=remoteserver('127.0.0.1',3030)
		newclient=localclient(newconn)
		newconn.connect()
		time.sleep(0.01)
		self.assertEqual( len(newclient.globals), 1)
		self.assertEqual( newclient.globals['warmuppoint'].x, 14)
	
	def test_filters(self):
		print('\nstarting test_filters \n')
		f=Filterable('a','b')
		self.remoteconnclient.add_filter('a')
		time.sleep(0.01)
		self.server.globals['filterme']=f
		f.data='c'
		time.sleep(0.01)
		self.assertEqual(self.remoteconnclient.globals['filterme'].data,'c')
		self.remoteconnclient.remove_filter('a')
		time.sleep(0.01)
		f.data='d'
		time.sleep(0.01)
		self.assertNotEqual(self.remoteconnclient.globals['filterme'].data,self.server.globals['filterme'].data)
		l=Location(10,10)
		f.category=l
		self.server.globals['loc']=l
		time.sleep(0.01)
		self.assertNotEqual(self.remoteconnclient.globals['filterme'].category, self.server.globals['filterme'].category)
		self.remoteconnclient.add_filter(self.remoteconnclient.globals['loc'])
		time.sleep(0.01)
		self.assertEqual(self.server.globals['filterme'].category.x, 10)
		self.assertEqual(self.remoteconnclient.globals['filterme'].category.x, 10)
		
	def test_data_types(self):
		print('\nstarting test_data_types')
		added=Location(10,20)
		self.server.globals['a']=added
		time.sleep(0.01)
		added.x=False
		time.sleep(0.01)
		self.assertTrue(self.remoteconnclient.globals['a'].x is False)
		added.x=None
		time.sleep(0.01)
		self.assertTrue(self.remoteconnclient.globals['a'].x is None)
		added.x='hello'
		time.sleep(0.01)
		self.assertEqual(self.remoteconnclient.globals['a'].x , "hello")
		added.x={'z':True}
		time.sleep(0.01)
		self.assertEqual(self.remoteconnclient.globals['a'].x , {'z':True})
	
	def tearDown(self):
		#syncronously stop all the clients
		start=time.time()
		self.clientlistener.stop()
		stop=time.time()
		#print('shutting down took ', stop-start)
		

		
		


		
if __name__ == '__main__':
	try:
		unittest.main()
	finally:
		input('press enter to continue')

	
		