from struct import pack, unpack
from PyNetworking.data.decorators import build_shared_object,shared_object, classWrappers


class event:
	event_id=None
	isReplaceable=False
	def get_blob(self):
		raise Exception('root event does not have a blob')
	def unique_id(self):
		if hasattr(self.item, '__get_shared_id__'):
			return self.event_id, self.item.__get_shared_id__()
		return self.event_id, self.item
	
class global_change(event):
	event_id=1
	isReplaceable=True
	def __init__(self, key,value):
		#self.sender=sender
		self.key=key
		self.item=value
		self.value=value
	def getblob(self, translator):
		result= translator.pack_object(self.key)+translator.pack_object(self.value)
		return result
	def apply_to(self, target, notify):
		if notify:
			target.notify_global_changed(self.key, self.value)
		else:
			target.remote_global_changed(target, self.key, self.value)
	def unique_id(self):
		return self.event_id,self.key
		
class add_item(event):
	event_id=2
	isReplaceable=False
	def __init__(self,item):
		self.item=item
	def getblob(self,translator):
		return translator.pack_object(self.item)
	def apply_to(self, target, notify):
		if notify:
			target.notify_add(self.item)
		else:
			target.remote_add(target,self.item)

class attribute_updated(event):
	event_id=3
	isReplaceable=True
	def __init__(self, item, attribute, value):
		self.item=item
		self.attribute_id=attribute
		self.value=value
	def getblob(self,translator):
		#all newly added objects are ahead of us in the queue.  Probably
		return pack('H',self.attribute_id)+translator.pack_object(self.value)
	def apply_to(self, target, notify):
		if notify:
			target.notify_attribute_updated(self.item, self.attribute_id, self.value)
		else:
			target.remote_attribute_updated(target,self.item, self.attribute_id, self.value)
	def unique_id(self):
		return self.event_id,self.item.__get_shared_id__(), self.attribute_id

class method_invoked(event):
	event_id=4
	isReplaceable=False
	def __init__(self, item, method_id, args, kw):
		self.item=item
		self.args=args
		self.method_id=method_id
		self.kw=kw
	def getblob(self, translator):
		return pack('H',self.method_id)+translator.pack_list(self.args)+translator.pack_dictionary(self.kw)
	def apply_to(self, target, notify):
		if notify:
			target.shared_method_invoked(self.item, self.method_id, self.args, self.kw)
		else:
			target.remote_method_invoked(target,self.item, self.method_id, self.args, self.kw)
class filter_added(event):
	event_id=5
	isReplaceable=False
	def __init__(self, filter):
		self.item=filter
	def getblob(self, translator):
		return translator.pack_object(self.item)
	def apply_to(self, target, notify):
		target.filter_added(self.item)
class filter_removed(event):
	event_id=6
	isReplaceable=False
	def __init__(self, filter):
		self.item=filter
	def getblob(self, translator):
		return translator.pack_object(self.item)
	def apply_to(self, target, notify):
		target.filter_removed(self.item)
class warmup_complete(event):
	event_id=7
	isReplaceable=False
	def __init__(self):
		self.item=None
	def getblob(self, translator):
		return b''
	def apply_to(self, target, notify):
		target.finish_warmup()

class Translator:
	
	def __init__(self, owner):
		self.owner=owner
	def translate_event(self, event):
		if hasattr(event.item, '__get_shared_id__'):
			owner_id, colon, item_id=event.item.__get_shared_id__().partition(':')
			identity=pack('HHH', int(owner_id), int(item_id),event.event_id)
			result=identity+event.getblob(self)
			size=pack('H',len(result)+2)
			result=size+result
		else: 
			result=pack('HHH', 0,0,event.event_id)+event.getblob(self)
			size=pack('H',len(result)+2)
			result=size+result
			
		return result
	def pack_small(self, object):
		if type(object) in (int, float, str,list, dict, bool):
			return self.pack_object(object)
		owner_id, colon, item_id=object.__get_shared_id__().partition(':')
		result=pack('HHHH',8,object.__class_id__,int(owner_id),int(item_id))	
		return result
	def pack_list(self, thelist):
		result=pack('H', 3)
		for item in thelist:
			result+=self.pack_object(item)
		return pack('H', len(result)+2)+result
	def pack_dictionary(self, dictionary):
		result=pack('H',4)
		for key in dictionary:
			result+=self.pack_object(key)
			result+=self.pack_object(dictionary[key])
		return pack('H',len(result)+2)+result
	
	def pack_object(self, object,sentTogether=[]):
		if object is None:
			result=b''
		elif type(object) is int:
			if object>=2**31 or object<-2**31:
				raise Exception('Large ints not yet implemented')
			result=pack('H',0)+pack('l',object)
		elif type(object) is float:
			result=pack('H',1)+pack('d',object)
		elif type(object) is str:
			raw_data= bytes(object,'Utf-8')
			#string size is already implicitly part of the data structure
			result=pack('H',2)+raw_data
		elif type(object) is list:
			return self.pack_list(object)
		elif type(object) is dict:
			return self.pack_dictionary(object)
		elif type(object) is bool:
			result=pack('H',5)+(object and pack('l',1) or pack('l',0))
			"""
				Packed Full Object:
				HHHH(H[object])*
				HHHH=size, class, owner, id
					H=AttributeId
			"""
		elif hasattr(object, '__get_shared_id__'):
			self.owner.check_in_item(object, False)
			shared_id=object.__get_shared_id__()
			owner_id, colon, item_id=shared_id.partition(':')
			result=pack('HHH',object.__class_id__,int(owner_id),int(item_id))
			for key, value in object.__classWrapper__.shared_attributes.items():
				subobject=getattr(object,key)
				if hasattr(subobject, '__is_sent__') and subobject.__is_sent__ or subobject in sentTogether:
					result+=pack('H',value)+self.pack_small(subobject)
				else:
					result+=pack('H',value)+self.pack_object(subobject,sentTogether+[object])
		else:
			raise Exception("didn't know what to do with %s of type %s"%(object,type(object)))
		size=pack('H',len(result)+2)
		return size+result
	def unpack_list(self, listdata):
		realdata=listdata[4:]
		result=[]
		while realdata:
			object_length,=unpack('H',realdata[:2])
			result.append(self.unpack_object(realdata[:object_length]))
			realdata=realdata[object_length:]
		return result
	def unpack_dictionary(self, dictdata):
		realdata=dictdata[4:]
		result={}
		while realdata:
			key_length,=unpack('H',realdata[:2])
			key=self.unpack_object(realdata[:key_length])
			#if key is None:
			#	return result
			realdata=realdata[key_length:]
			value_length,=unpack('H',realdata[:2])
			value=self.unpack_object(realdata[:value_length])
			realdata=realdata[value_length:]
			result[key]=value
		return result
	def unpack_object(self, objectdata):
		if len(objectdata)==2:
			return None
		size, class_id=unpack('HH',objectdata[:4])
		internalVal=build_shared_object(class_id)
		if class_id==0:
			return unpack('l',objectdata[4:])[0]
		if class_id==1:
			return unpack('d',objectdata[4:])[0]
		if class_id==2:
			return internalVal+str(objectdata[4:],'Utf-8')
		if class_id==3:
			return self.unpack_list(objectdata)
		if class_id==4:
			return self.unpack_dictionary(objectdata)
		if class_id==5:
			val=unpack('l', objectdata[4:])[0]
			if val:
				return True
			return False
		owner_id,item_id=unpack('HH',objectdata[4:8])
		remainingdata=objectdata[8:]
		if not remainingdata:
			value=self.owner.get_by_id('%i:%i'%(owner_id,item_id))
			#we have it
			if value:
				return value
			#otherwise it might just be empty of shared_attributes
		result=self.owner.get_by_id('%i:%i'%(owner_id, item_id))
		if not result:
			result=shared_object(internalVal, class_id, classWrappers[class_id],'%i:%i'%(owner_id,item_id))

		while remainingdata:
			attribute_id,sectionlength=unpack('HH',remainingdata[:4])
			#include size when telling the next part what to do, they don't care, but it's assumed to be present
			value=self.unpack_object(remainingdata[2:2+sectionlength])
			attrname=result.__classWrapper__.reverse_shared_attributes[attribute_id]
			result.__quiet_setattr__(attrname, value)
			remainingdata=remainingdata[2+sectionlength:]
		#self.owner.check_in_item(result,False)
		result.__is_sent__=True
		self.owner.check_in_item(result, False)
		return result
		
	def translate_binary_event(self, eventdata):
		#caller already reduced this
		owner_id, item_id, event_id=unpack('HHH', eventdata[2:8])
		if event_id==global_change.event_id:
			objects=eventdata[8:]
			keysize,=unpack('H',objects[:2])
			key=self.unpack_object(objects[:keysize])
			value=self.unpack_object(objects[keysize:])
			return global_change(key,value)
		if event_id==add_item.event_id:
			object_data=eventdata[8:]
			item=self.unpack_object(object_data)
			return add_item(item)
		if event_id==attribute_updated.event_id:
			item=self.owner.get_by_id('%i:%i'%(owner_id,item_id))
			attributeId,=unpack('H', eventdata[8:10])
			#offset two more for the size of the chunk, which we know for sure to be the remainder
			value=self.unpack_object(eventdata[10:])
			return attribute_updated(item, attributeId, value)
		if event_id==method_invoked.event_id:
			item=self.owner.get_by_id('%i:%i'%(owner_id,item_id))
			method_id,=unpack('H',eventdata[8:10])
			listlength,=unpack('H', eventdata[10:12])
			args=self.unpack_list(eventdata[10:10+listlength])
			kw=self.unpack_dictionary(eventdata[10+listlength:])
			return method_invoked(item, method_id,args,kw)
		if event_id==filter_added.event_id:
			value=self.unpack_object(eventdata[8:])
			result= filter_added(value)
			return result
		if event_id==filter_removed.event_id:
			value=self.unpack_object(eventdata[8:])
			return filter_removed(value)
		if event_id==warmup_complete.event_id:
			return warmup_complete()
#translator=EventTranslator()