from cromulent import model, vocab
from cromulent.model import factory, DataError, OrderedDict, BaseResource
from cromulent.model import STR_TYPES

import json
import requests

class Reader(object):

	def __init__(self, validate_props=True, validate_profile=True):
		self.uri_object_map = {}
		self.forward_refs = []
		self.vocab_props = ['assigned_property']
		self.vocab_classes = {}
		self.validate_profile = validate_profile
		self.validate_props = validate_props

		for cx in dir(vocab):
			what = getattr(vocab, cx)
			# crying cat face -- type as a @property returns the function, not the value
			# when calling it on a class rather than an instance
			try:
				mytype = what._classhier[0].__name__
			except AttributeError:
				continue
			# find classes
			if (cx[0].isupper() and not hasattr(model, cx) and type(what) == type):
				# class
				self.vocab_classes[(mytype, what._classification[0].id)] = what

	def read(self, data):
		if not data:
			raise DataError("No data provided: %r" % data)
		elif type(data) in STR_TYPES:
			try:
				data = json.loads(data)
			except:
				raise DataError("Data is not valid JSON")
		if not data:
			raise DataError("No Data provided")
		self.uri_object_map = {}
		self.forward_refs = []
		try:
			what = self.construct(data)
			self.process_forward_refs()
			self.uri_object_map = {}
			self.forward_refs = []
			return what
		except:
			raise

	def process_forward_refs(self):
		for (what, prop, uri) in self.forward_refs:
			if uri in self.uri_object_map:
				setattr(what, prop, self.uri_object_map[uri])
			else:
				raise NotImplementedError("No class information for %s.%s = %s" % (what, prop, uri))

	def construct(self, js):
		# pass in json, get back object
		if '@context' in js:
			del js['@context']

		ident = js.get('id', '')
		typ = js.get('type', None)

		if typ == None:
			clx = BaseResource
		else:
			# Get class based on name
			try:
				clx = getattr(model, typ)
			except AttributeError:
				# No such class
				raise DataError("Resource %s has unknown class %s" % (ident, typ) )

		# now check vocab.ext_classes to try and refine
		trash = None 
		if 'classified_as' in js:
			for c in js['classified_as']:
				i = c.get('id', '')
				clx2 = self.vocab_classes.get((typ, i), None)
				if clx2 is not None:
					clx = clx2
					trash = c
					break

		what = clx(ident=ident)
		what._validate_profile = self.validate_profile
		self.uri_object_map[ident] = what

		if self.validate_props:
			propList = what.list_all_props()

		# sort data by KOH to minimize chance of bad backrefs
		itms = list(js.items())
		itms.sort(key=lambda x: factory.key_order_hash.get(x[0], 10000))

		for (prop, value) in itms:
			if prop in ['id', 'type']:
				continue

			if self.validate_props and not prop in propList:
				raise DataError("Unknown property %s on %s" % (prop, clx.__name__))

			# Climb looking for range
			rng = None
			for c in what._classhier:		
				if prop in c._all_properties:
					rng = c._all_properties[prop].range
					break

			if not rng:
				print(f"Couldn't find range for {prop} on {what}; trashing it")
				continue

			if type(value) != list:
				value = [value]
			for subvalue in value:
				if trash is not None and prop == 'classified_as' and subvalue == trash:
					continue
				if rng == str:
					setattr(what, prop, subvalue)				
				elif type(subvalue) == dict or isinstance(subvalue, OrderedDict):
					# recurse ...
					val = self.construct(subvalue)
					setattr(what, prop, val)
				elif type(subvalue) in STR_TYPES and prop in self.vocab_props:
					# keep as string
					setattr(what, prop, subvalue)
				elif type(subvalue) in STR_TYPES:
					# raw URI to be made into a class of type rng
					# or back reference
					if subvalue in self.uri_object_map:
						setattr(what, prop, self.uri_object_map[subvalue])
					elif rng in [model.Type, BaseResource]:
						# Always a X, often no more info
						setattr(what, prop, rng(ident=subvalue))
					else:
						self.forward_refs.append([what, prop, subvalue])
				else:
					# No idea!!
					raise DataError("Value %r is not expected for %s" % (subvalue, prop))

		return what


class NetworkedReader(Reader):
	# Read in data over the network, given a URI or JSON
	# Then traverse to n hops


	def __init__(self, validate_props=True, validate_profile=True):	
		Reader.__init__(self, validate_props, validate_profile)
		self.distances = {}
		self.results = {}
		self.ignore_props = ['access_point']


	def walk_for_refs(self, what, distance):
		props = what.list_my_props()
		if what.id and what.id.startswith('http') and not what.id in self.distances:
			self.distances[what.id] = distance
		for p in props:
			if not p in self.ignore_props:
				val = getattr(what, p)
				if isinstance(val, BaseResource):
					# walk
					self.walk_for_refs(val, distance)
				elif type(val) == list:
					for v in val:
						if isinstance(v, BaseResource):
							# walk
							self.walk_for_refs(v, distance)

	def read(self, data, hops=0):
		if type(data) in STR_TYPES and (data.startswith('http://') or \
				data.startswith('https://')):
			try:
				resp = requests.get(data)
				data = resp.json()				
			except:
				return DataError("Detected URI, but no data available")
		result = Reader.read(self, data)
		if hops:
			self.results[result.id] = result
			self.walk_for_refs(result, distance=hops-1)
			for uri in self.distances.keys():
				if not uri in self.results:
					self.read(uri, hops=hops-1)
		else:
			self.results[result.id] = result			
		return result
