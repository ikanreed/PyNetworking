from threading import Lock
next_object_id=0
id_lock=Lock()
class shared_object:
	def __init__(self, data, class_id, classWrapper, fullId=None):
		global next_object_id
		#thread safe global
		self.__full_id__=fullId
		self.__class_id__=class_id
		self.__classWrapper__=classWrapper
		self.__is_sent__=False
		if not self.__full_id__:
			with id_lock:
				vars(self)['__shared_id__']=next_object_id
				next_object_id+=1
		else:
			self.__shared_id__=None
		self.__data__=data
		self.__owner__=None
		data.__wrapper_backref__=self
	
	def __filter_list__(self):
		if hasattr(self.__data__,'__filter_list__'):
			result= self.__data__.__filter_list__()
			if result:
				return set(result)
		return set()
	
	def UnderlyingType(self):
		return self.__data__
	
	def __getattr__(self, attr):
		if(attr.startswith('__')) and attr in vars(self):
			return vars(self)[attr]
		return getattr(self.__data__,attr)
	def __quiet_setattr__(self, attr, value):
		if type(attr) is int:
			attr=self.__classWrapper__.reverse_shared_attributes[attr]
		setattr(self.__data__, attr, value)
	def __setattr__(self, attr,value):
		if(attr.startswith('__')):
			vars(self)[attr]=value
		else:
			if attr in self.__classWrapper__.shared_attributes and self.__owner__:
				#if hasattr(value,'__get_shared_id__') and not value.__is_sent__  and self.__owner__:
				#	self.__owner__.check_in_item(value,True)
				self.__owner__.notify_attribute_updated(self, self.__classWrapper__.shared_attributes[attr], value)
			setattr(self.__data__,attr,value)
	def __str__(self):
		return str(self.__data__)
	def __unicode__(self):
		return unicode(self.__data__)
	def __repr__(self):
		return 'Network Shared<%s>'%repr(self.__data__)
	def __get_shared_id__(self):
		if self.__full_id__:
			return self.__full_id__
		elif self.__owner__:
			return '%i:%i'%(self.__owner__.prefix,self.__shared_id__)
		else:
			return None
	def __hash__(self):
		return hash(self.__data__)
	def __eq__(self, other):
		if self is other:
			return True
		return self.__data__==other
	def __invoke_shared_method__(self,method_id,args,kw):
		methodName=self.__classWrapper__.reverse_shared_methods[method_id]
		methodVal=getattr(self.__data__,methodName)
		kw['__skip_call__']=True
		methodVal( *args, **kw)
		
	#def __str__(self):
	#	return 'Network Shared<%s>'%str(super(self).data)
	#def __unicode__(self):
	#	return 'Network Shared<%s>'%unicode(super(self).data)

def build_shared_object(class_id):
	#we won't allow constructors to work, I guess
	val=classRefs[class_id]()
	return val

classRefs={0:int,1:float,2:str,3:list,4:dict,5:bool}
classWrappers={}
class shared_class:
	def __init__(self, under_type):
		global classRefs
		global classWrappers
		#addition is to prevent collisions with default classrefs
		self.id=self.hash(under_type.__qualname__)%(2**16-6)+6
		self.shared_methods={}
		self.shared_attributes={}
		attribute_id=0
		method_id=0
		
		for attribute in dir(under_type):
			if not attribute.startswith('__'):
				
				val=getattr(under_type, attribute)
				if callable(val) and val.__name__=='shared_method_wrapper':
					self.shared_methods[attribute]=method_id
					method_id+=1
				elif type(val) is shared_attribute:
					self.shared_attributes[attribute]=attribute_id
					attribute_id+=1
					#they don't need to know we're doing anything weird, just let them have their defaults back
					setattr(under_type,attribute, val.default)
		self.reverse_shared_attributes={value:key for key, value in self.shared_attributes.items()}
		self.reverse_shared_methods={value:key for key, value in self.shared_methods.items()}
					
					
		if(self.id in classRefs):
			raise Exception('type hash collision, I felt it was unlikely enough not to warrant more than this')
		classRefs[self.id]=under_type
		classWrappers[self.id]=self
		self.underlying_type=under_type
		
	def __call__(self, *args, **kw):
		return shared_object(self.underlying_type(*args,**kw), self.id,self)
	def __repr__(self):
		return 'Network Shared<%s>'%repr(self.underlying_type)
	def hash(self, arg):
		result=0
		for val in arg:
			result+=ord(val)
			result*=7
		return result
		
class shared_attribute:
	def __init__(self, default):
		self.default=default

def shared_method(func):
	def shared_method_wrapper(self, *args, **kw):
		if '__skip_call__' in kw:
			del kw['__skip_call__']
		else:
			wrapper=self.__wrapper_backref__
			if(wrapper.__owner__):
				wrapClass=wrapper.__classWrapper__
				method_id=wrapClass.shared_methods[func.__name__]
				wrapper.__owner__.shared_method_invoked(wrapper,method_id,args, kw)
			
		func(self, *args, **kw)
	return shared_method_wrapper
	
"""
class shared_method:
	def __init__(self, method):
		self.method=method
	def __call__(self,*args,**kw):
		self.method(*args,**kw)"""
		
class server_attribute:
	def __init__(self, default):
		self.default=default
	
class server_method:
	def __init__(self, method):
		self.method=method
	def __call__(self,*args,**kw):
		self.method(*args,**kw)
		
		