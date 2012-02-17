#! /usr/bin/python
import xml.dom.minidom
from xml.dom.minidom import Node
import os
import re

def main():
	libs3d = xml.dom.minidom.parse("/home/mariusn/workspace/test-dox/xml/t_8c.xml")
	func = extract_functions(libs3d)
	struct= extract_structs(libs3d)
	typedef=extract_typedefs(libs3d)

	print "funcs:%s"%(func)
	print
	print "structs:%s"%(struct)
	print
	print "typedefs:%s"%(typedef)

#################################################
class struct_element:
	def __init__(self, node):
		self.element = {'type': '', 'name' : '', 'help': []}
		for node2 in node.childNodes:
			if node2.nodeName == "name":
				self.element['name'] = get_text(node2)

			if node2.nodeName == "type":
				self.element['type'] = get_text(node2)

			if node2.nodeName == 'detaileddescription':
				self.element['help'] = detaileddescription(node2)

	def dom_append(self, programlisting):
		create_append_text(programlisting, '\t'+self.element['type'])
		if self.element['type'][-1:] != "*":
			# dont add space between * and name
			create_append_text(programlisting, " ")
		create_append_text(programlisting, self.element['name']+';\n')

	def dom_append_help(self, variablelist):
		# ignore members with empty help texts
		if self.element['help'].isempty():
			return

		varlistentry = create_append(variablelist, 'varlistentry')
		term = create_append(varlistentry, 'term')
		create_append_text(term, self.element['name'])
		listitem = create_append(varlistentry, 'listitem')

		# add help to struct member
		self.element['help'].dom_append(listitem)


class detaileddescription:
	t = []

	def __init__(self, node):
		self.t = []
		self.__get_text_complex(node)
		self.__complex2simplearray()

	"""
	Generate linear list of text and section types
	"""
	def __get_text_complex(self, node):
		for node in node.childNodes:
			if node.nodeType == Node.TEXT_NODE:
				self.t.append(node.data)
			else:
				if node.nodeName == 'sp':
					self.t.append(" ")
				elif node.nodeName == 'para':
					self.t.append({'type': 'para', 'text': ''})
					self.__get_text_complex(node)
				elif node.nodeName == 'programlisting':
					self.t.append({'type': 'programlisting', 'text': ''})
					self.__get_text_complex(node)
					self.t.append({'type': 'para', 'text': ''})
				elif node.nodeName == 'simplesect':
					if node.attributes['kind'].nodeValue == 'remark':
						self.t.append({'type': 'warning', 'text': ''})
						self.__get_text_complex(node)
						self.t.append({'type': 'para', 'text': ''})
					else:
						self.t.append({'type': 'para', 'text': ''})
						self.__get_text_complex(node)
				else:
					self.__get_text_complex(node)

	"""
	Convert linear list of text and section types to list of section types with corresponding text
	"""
	def __complex2simplearray(self):
		cur_object = 0
		array = []
		for element in self.t:
			if type(element) != dict:
				# add text to last section type
				if cur_object == 0:
					array.append({'type': 'para', 'text': element})
					cur_object = array[0]
				else:
					cur_object['text'] += element
			else:
				# add new section type
				if element['type'] == 'para' and len(array) != 0 and array[-1]['type'] in ['warning']:
					# ignore para inside warning and add text to last section type
					cur_object['text'] += element['text']
				else:
					cur_object = element
					array.append(element)

		self.t = array

	"""
	Append complex help section to dom
	"""
	def dom_append(self, sect):
		for p in self.t:
			if p['text'] != '':
				if p['type'] in ['warning']:
					# add para in warning before adding help text
					extra_para = create_append(sect, p['type'])
					para = create_append(extra_para, 'para')
					create_append_text(para, p['text'])
				else:
					if p['text'].strip() == '':
						continue
					para = create_append(sect, p['type'])
					create_append_text(para, p['text'])

	def isempty(self):
		return (len(self.t) == 0) or (len(self.t) == 1 and self.t[0]['text'].strip() == '')



"""
Generate text from all childNodes
"""
def get_text(node):
	t = ''
	for node in node.childNodes:
		if node.nodeType == Node.TEXT_NODE:
			t += node.data
		else:
			t += get_text(node)
	return t


"""
Extract struct information from doxygen dom
"""
def extract_structs(dom):
	structlist = []
	# find refs (names of xml files) of structs
	for node in dom.getElementsByTagName("innerclass"):
		struct = {'name': '', 'id': '', 'ref': '', 'elements': [], 'brief': '', 'help': []}
		struct['name'] = get_text(node)
		struct['id'] = 'struct'+struct['name']
		struct['ref'] = node.attributes['refid'].nodeValue
		structlist.append(struct)

	# open xml files and extract information from them
	for struct in structlist:
		dom = xml.dom.minidom.parse("xml/"+struct['ref']+".xml")

		for node in dom.getElementsByTagName('compounddef')[0].childNodes:
			if node.nodeName == "briefdescription":
				struct['brief'] = get_text(node)

			if node.nodeName == 'detaileddescription':
				struct['help'] = detaileddescription(node)

		for node in dom.getElementsByTagName("memberdef"):
			struct['elements'].append(struct_element(node))

	return structlist
##########################################3
class function_param:
	def __init__(self, node):
		self.param = {'type' : '', 'declname' : '', 'array' : ''}
		for n in node.childNodes:
			if n.nodeName == 'type':
				self.param['type'] = get_text(n)

			if n.nodeName == 'declname':
				self.param['declname'] = get_text(n)

			if n.nodeName == 'array':
				self.param['array'] = get_text(n)

	def dom_append(self, funcprototype, intent = ""):
		paramdef = create_append(funcprototype, 'paramdef')

		create_append_text(paramdef, intent+self.param['type'])

		if self.param['declname'] != '':
			if self.param['type'][-1:] != "*":
				# dont add space between * and name
				create_append_text(paramdef, " ")
			parameter = create_append(paramdef, 'parameter')
			create_append_text(parameter, self.param['declname'])

		if self.param['array'] != '':
			create_append_text(paramdef, self.param['array'])

	def is_void(self):
		if self.param['type'] == 'void' and self.param['declname'] == '':
			return 1
		else:
			return 0

def remove_exportdefinitions(function_return):
	exports = ["S3DEXPORT", "S3DWEXPORT"]
	for export in exports:
		if function_return[:len(export)] == export:
			return function_return[len(export):].strip()


"""
Extract function information from doxygen dom
"""
def extract_functions(dom):
	functionlist = []
	for node in dom.getElementsByTagName("memberdef"):
		# find nodes with functions information
		if node.attributes['kind'].nodeValue != 'function':
			continue

		function = {'return': '', 'name': '', 'id': '', 'param': [], 'brief': '', 'help': [], 'location':[]}
		for node2 in node.childNodes:
			if node2.nodeName == "name":
				function['name'] = get_text(node2)
				function['id'] = function['name']

			if node2.nodeName == "type":
				function['return'] = remove_exportdefinitions(get_text(node2))

			if node2.nodeName == "param":
				function['param'].append(function_param(node2))

			if node2.nodeName == "briefdescription":
				function['brief'] = get_text(node2)

			if node2.nodeName == 'detaileddescription':
				function['help'] = detaileddescription(node2)

			if node2.nodeName == "location":
				function['location'].append(function_param(node2))

		functionlist.append(function)

	return functionlist
#########################333
"""
Extract typedef information from doxygen dom
"""
def extract_typedefs(dom):
	typedeflist = []
	for node in dom.getElementsByTagName("memberdef"):
		# find nodes with typedef information
		if node.attributes['kind'].nodeValue != 'typedef':
			continue

		typedef = {'name': '', 'id': '', 'definition': '', 'help': []}
		for node2 in node.childNodes:
			if node2.nodeName == 'name':
				typedef['name'] = get_text(node2)
				typedef['id'] = typedef['name']

			if node2.nodeName == 'definition':
				typedef['definition'] = get_text(node2)

			if node2.nodeName == 'detaileddescription':
				typedef['help'] = detaileddescription(node2)

		typedeflist.append(typedef)

	return typedeflist


if __name__ == '__main__':
	main()

