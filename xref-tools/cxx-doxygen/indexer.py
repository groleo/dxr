from dxr.languages import register_language_table
import dxr.plugins
import os
import xml.sax.handler
from xml.etree import cElementTree as ET

decl_master = {}
types = {}
typedefs = {}
functions = {}
inheritance = {}
variables = {}
references = {}
warnings = []
macros = {}
calls = {}


######################################
import xml.dom.minidom
from xml.dom.minidom import Node
import os
import re

#################################################
#class struct_element:
#	def __init__(self, node):
#		self.element = {'type': '', 'name' : '', 'help': []}
#		for node2 in node.getchildren():
#			if node2.tag == "name":
#				self.element['name'] = get_text(node2)
#
#			if node2.tag == "type":
#				self.element['type'] = get_text(node2)
#
#			if node2.tag == 'detaileddescription':
#				self.element['help'] = detaileddescription(node2)
#
#	def dom_append(self, programlisting):
#		create_append_text(programlisting, '\t'+self.element['type'])
#		if self.element['type'][-1:] != "*":
#			# dont add space between * and name
#			create_append_text(programlisting, " ")
#		create_append_text(programlisting, self.element['name']+';\n')
#
#	def dom_append_help(self, variablelist):
#		# ignore members with empty help texts
#		if self.element['help'].isempty():
#			return
#
#		varlistentry = create_append(variablelist, 'varlistentry')
#		term = create_append(varlistentry, 'term')
#		create_append_text(term, self.element['name'])
#		listitem = create_append(varlistentry, 'listitem')
#
#		# add help to struct member
#		self.element['help'].dom_append(listitem)
#
#
#class detaileddescription:
#	t = []
#
#	def __init__(self, node):
#		self.t = []
#		self.__get_text_complex(node)
#		self.__complex2simplearray()
#
#	"""
#	Generate linear list of text and section types
#	"""
#	def __get_text_complex(self, node):
#		for node in node.getchildren():
#			if node.nodeType == Node.TEXT_NODE:
#				self.t.append(node.data)
#			else:
#				if node.tag == 'sp':
#					self.t.append(" ")
#				elif node.tag == 'para':
#					self.t.append({'type': 'para', 'text': ''})
#					self.__get_text_complex(node)
#				elif node.tag == 'programlisting':
#					self.t.append({'type': 'programlisting', 'text': ''})
#					self.__get_text_complex(node)
#					self.t.append({'type': 'para', 'text': ''})
#				elif node.tag == 'simplesect':
#					if node.attributes['kind'].nodeValue == 'remark':
#						self.t.append({'type': 'warning', 'text': ''})
#						self.__get_text_complex(node)
#						self.t.append({'type': 'para', 'text': ''})
#					else:
#						self.t.append({'type': 'para', 'text': ''})
#						self.__get_text_complex(node)
#				else:
#					self.__get_text_complex(node)
#
#	"""
#	Convert linear list of text and section types to list of section types with corresponding text
#	"""
#	def __complex2simplearray(self):
#		cur_object = 0
#		array = []
#		for element in self.t:
#			if type(element) != dict:
#				# add text to last section type
#				if cur_object == 0:
#					array.append({'type': 'para', 'text': element})
#					cur_object = array[0]
#				else:
#					cur_object['text'] += element
#			else:
#				# add new section type
#				if element['type'] == 'para' and len(array) != 0 and array[-1]['type'] in ['warning']:
#					# ignore para inside warning and add text to last section type
#					cur_object['text'] += element['text']
#				else:
#					cur_object = element
#					array.append(element)
#
#		self.t = array
#
#	"""
#	Append complex help section to dom
#	"""
#	def dom_append(self, sect):
#		for p in self.t:
#			if p['text'] != '':
#				if p['type'] in ['warning']:
#					# add para in warning before adding help text
#					extra_para = create_append(sect, p['type'])
#					para = create_append(extra_para, 'para')
#					create_append_text(para, p['text'])
#				else:
#					if p['text'].strip() == '':
#						continue
#					para = create_append(sect, p['type'])
#					create_append_text(para, p['text'])
#
#	def isempty(self):
#		return (len(self.t) == 0) or (len(self.t) == 1 and self.t[0]['text'].strip() == '')
#"""
#Extract struct information from doxygen dom
#"""
#def extract_structs(dom):
#	structlist = []
#	# find refs (names of xml files) of structs
#	for node in dom.getElementsByTagName("innerclass"):
#		struct = {'name': '', 'id': '', 'ref': '', 'elements': [], 'brief': '', 'help': []}
#		struct['name'] = get_text(node)
#		struct['id'] = 'struct'+struct['name']
#		struct['ref'] = node.attributes['refid'].nodeValue
#		structlist.append(struct)
#
#	# open xml files and extract information from them
#	for struct in structlist:
#		dom = xml.dom.minidom.parse("xml/"+struct['ref']+".xml")
#
#		for node in dom.getElementsByTagName('compounddef')[0].getchildren():
#			if node.tag == "briefdescription":
#				struct['brief'] = get_text(node)
#
#			if node.tag == 'detaileddescription':
#				struct['help'] = detaileddescription(node)
#
#		for node in dom.getElementsByTagName("memberdef"):
#			struct['elements'].append(struct_element(node))
#
#	return structlist
##########################################3
#
#class function_param:
#	def __init__(self, node):
#		self.param = {'type' : '', 'declname' : '', 'array' : ''}
#		for n in node.getchildren():
#			if n.tag == 'type':
#				self.param['type'] = get_text(n)
#
#			if n.tag == 'declname':
#				self.param['declname'] = get_text(n)
#
#			if n.tag == 'array':
#				self.param['array'] = get_text(n)
#
#	def dom_append(self, funcprototype, intent = ""):
#		paramdef = create_append(funcprototype, 'paramdef')
#
#		create_append_text(paramdef, intent+self.param['type'])
#
#		if self.param['declname'] != '':
#			if self.param['type'][-1:] != "*":
#				# dont add space between * and name
#				create_append_text(paramdef, " ")
#			parameter = create_append(paramdef, 'parameter')
#			create_append_text(parameter, self.param['declname'])
#
#		if self.param['array'] != '':
#			create_append_text(paramdef, self.param['array'])
#
#	def is_void(self):
#		if self.param['type'] == 'void' and self.param['declname'] == '':
#			return 1
#		else:
#			return 0
############################
#"""
#Extract typedef information from doxygen dom
#"""
#def extract_typedefs(dom):
#	typedeflist = []
#	for node in dom.getElementsByTagName("memberdef"):
#		# find nodes with typedef information
#		if node.attributes['kind'].nodeValue != 'typedef':
#			continue
#
#		typedef = {'name': '', 'id': '', 'definition': '', 'help': []}
#		for node2 in node.getchildren():
#			if node2.tag == 'name':
#				typedef['name'] = get_text(node2)
#				typedef['id'] = typedef['name']
#
#			if node2.tag == 'definition':
#				typedef['definition'] = get_text(node2)
#
#			if node2.tag == 'detaileddescription':
#				typedef['help'] = detaileddescription(node2)
#
#		typedeflist.append(typedef)
#
#	return typedeflist
######################################

"""
Generate text from all childNodes
"""
def get_text(node):
	return node.text

"""
Extract function information from doxygen dom
"""
def process_function(node):
	if node.attrib['kind'] != 'function':
		return

	function = {'id':'', 'fname':'', 'fqualname':'', 'ftype':'', 'fargs':[], 'floc':'', 'extent':''}

	function['id'] = node.attrib['id']

	for node2 in node.getchildren():
		if node2.tag == "name":
			if get_text(node2) == '': return
			function['fname'] = get_text(node2)
			function['fqualname'] = get_text(node2)

		if node2.tag == "argsstring":
			function['fargs'] = get_text(node2)

		if node2.tag == "location":
			function['floc'] = node2.attrib['file']+':'+node2.attrib['line']

	print "Extracted: %s -> %s(%s)" % (function['floc'],function['fqualname'],function['id'])
	functions[(function['fqualname'], function['floc'])] = function

#class Handlers():
#  def process_includes(self,attrs):
#    print "Should process INCLUDES:%s"%attrs
#
#  name, defloc, declloc = args['name'], args['defloc'], args['declloc']
#  decl_master[(name, declloc)] = defloc
#  decl_master[(name, defloc)] = defloc
#
#def process_type(typeinfo):
#  types[(typeinfo['tqualname'], typeinfo['tloc'])] = typeinfo
#
#def process_typedef(typeinfo):
#  typedefs[(typeinfo['tqualname'], typeinfo['tloc'])] = typeinfo
#  typeinfo['tkind'] = 'typedef'
#
#def process_impl(info):
#  inheritance[info['tbname'], info['tbloc'], info['tcname'], info['tcloc']]=info
#
#def process_variable(varinfo):
#  variables[varinfo['vname'], varinfo['vloc']] = varinfo
#
#def process_ref(info):
#  # Each reference is pretty much unique, but we might record it several times
#  # due to header files.
#  references[info['varname'], info['varloc'], info['refloc']] = info
#
#def process_warning(warning):
#  warnings.append(warning)
#
#def process_macro(macro):
#  macros[macro['macroname'], macro['macroloc']] = macro
#  if 'macrotext' in macro:
#    macro['macrotext'] = macro['macrotext'].replace("\\\n", "\n").strip()
#
#def process_call(call):
#  if 'callername' in call:
#    calls[call['callername'], call['callerloc'],
#          call['calleename'], call['calleeloc']] = call
#  else:
#    calls[call['calleename'], call['calleeloc']] = call


def load_indexer_output(fname):
  context = ET.iterparse(fname, events=("start", "end"))
  for event, elem in context:
    if event == "start" and elem.tag == "includes":
      pass
    if event == "start" and elem.tag == "memberdef":
      process_function(elem)



file_names = []
def collect_files(arg, dirname, fnames):
  for name in fnames:
    if os.path.isdir(name): continue
    if not name.endswith(arg): continue
    file_names.append(os.path.join(dirname, name))

def make_blob():
  def canonicalize_decl(name, loc):
    return (name, decl_master.get((name, loc), loc))
  def recanon_decl(name, loc):
    decl_master[name, loc] = (name, loc)
    return (name, loc)

  # Produce all scopes
  scopes = {}
  typeKeys = set()
  for t in types:
    key = canonicalize_decl(t[0], t[1])
    if key not in types:
      key = recanon_decl(t[0], t[1])
    if key not in scopes:
      typeKeys.add(key)
      types[key]['tid'] = scopes[key] = dxr.plugins.next_global_id()
  # Typedefs need a tid, but they are not a scope
  for t in typedefs:
    typedefs[t]['tid'] = dxr.plugins.next_global_id()
  funcKeys = set()
  for f in functions:
    key = canonicalize_decl(f[0], f[1])
    if key not in functions:
      key = recanon_decl(f[0], f[1])
    if key not in scopes:
      funcKeys.add(key)
      functions[key]['funcid'] = scopes[key] = dxr.plugins.next_global_id()

  # Variables aren't scoped, but we still need to refer to them in the same
  # manner, so we'll unify variables with the scope ids
  varKeys = {}
  for v in variables:
    key = (v[0], v[1])
    if key not in varKeys:
      varKeys[key] = variables[v]['varid'] = dxr.plugins.next_global_id()

  for m in macros:
    macros[m]['macroid'] = dxr.plugins.next_global_id()

  # Scopes are now defined, this allows us to modify structures for sql prep

  # Inheritance:
  # We need to canonicalize the types and then set up the inheritance tree
  # Since we don't know which order we'll see the pairs, we have to propagate
  # bidirectionally when we find out more.
  def build_inherits(base, child, direct):
    db = { 'tbase': base, 'tderived': child }
    if direct is not None:
      db['inhtype'] = direct
    return db

  childMap, parentMap = {}, {}
  inheritsTree = []
  for infoKey in inheritance:
    info = inheritance[infoKey]
    try:
      base = types[canonicalize_decl(info['tbname'], info['tbloc'])]['tid']
      child = types[canonicalize_decl(info['tcname'], info['tcloc'])]['tid']
    except KeyError:
      continue
    inheritsTree.append(build_inherits(base, child, info['access']))

    # Get all known relations
    subs = childMap.setdefault(child, [])
    supers = parentMap.setdefault(base, [])
    # Use this information
    for sub in subs:
      inheritsTree.append(build_inherits(base, sub, None))
      parentMap[sub].append(base)
    for sup in supers:
      inheritsTree.append(build_inherits(sup, child, None))
      childMap[sup].append(child)

    # Carry through these relations
    newsubs = childMap.setdefault(base, [])
    newsubs.append(child)
    newsubs.extend(subs)
    newsupers = parentMap.setdefault(child, [])
    newsupers.append(base)
    newsupers.extend(supers)

  # Fix up (name, loc) pairs to ids
  def repairScope(info):
    if 'scopename' in info:
      try:
        info['scopeid'] = scopes[canonicalize_decl(info.pop('scopename'),
          info.pop('scopeloc'))]
      except KeyError:
        pass
    else:
      info['scopeid'] = 0

  for tkey in typeKeys:
    repairScope(types[tkey])

  for tkey in typedefs:
    repairScope(typedefs[tkey])

  for fkey in funcKeys:
    repairScope(functions[fkey])

  for vkey in varKeys:
    repairScope(variables[vkey])
  
  # dicts can't be stuffed in sets, and our key is very unwieldy. Since
  # duplicates are most likely to occur only when we include the same header
  # file multiple times, the same definition should be used each time, so they
  # should be equivalent pre-canonicalization
  refs = []
  for rkey in references:
    ref = references[rkey]
    canon = canonicalize_decl(ref.pop('varname'), ref.pop('varloc'))
    if canon in varKeys:
      ref['refid'] = varKeys[canon]
      refs.append(ref)
    elif canon in funcKeys:
      ref['refid'] = functions[canon]['funcid']
      refs.append(ref)
    elif canon in typeKeys:
      ref['refid'] = types[canon]['tid']
      refs.append(ref)
    elif canon in typedefs:
      ref['refid'] = typedefs[canon]['tid']
      refs.append(ref)
    elif canon in macros:
      ref['refid'] = macros[canon]['macroid']
      refs.append(ref)

  # Declaration-definition remapping
  decldef = []
  for decl in decl_master:
    defn = (decl[0], decl_master[decl])
    if defn != decl:
      tmap = [ ('types', types, 'tid'), ('functions', functions, 'funcid'),
        ('types', typedefs, 'tid'), ('variables', variables, 'varid') ]
      for tblname, tbl, key in tmap:
        if defn in tbl:
          declo = {"declloc": decl[1],"defid": tbl[defn][key],"table": tblname}
          if "extent" in tbl[decl]:
            declo["extent"] = tbl[decl]["extent"]
          decldef.append(declo)
          break

  # Callgraph futzing
  callgraph = []
  for callkey in calls:
    call = calls[callkey]
    if 'callername' in call:
      source = canonicalize_decl(call.pop("callername"), call.pop("callerloc"))
      call['callerid'] = functions[source]['funcid']
    else:
      call['callerid'] = 0
    target = canonicalize_decl(call.pop("calleename"), call.pop("calleeloc"))
    if target in functions:
      call['targetid'] = functions[target]['funcid']
    elif target in variables:
      call['targetid'] = variables[target]['varid']
    callgraph.append(call)

  overridemap = {}
  for func in funcKeys:
    funcinfo = functions[func]
    if "overridename" not in funcinfo:
      continue
    base = canonicalize_decl(funcinfo.pop("overridename"),
      funcinfo.pop("overrideloc"))
    if base not in functions:
      continue
    basekey = functions[base]['funcid']
    subkey = funcinfo['funcid']
    overridemap.setdefault(basekey, set()).add(subkey)

  rescan = [x for x in overridemap]
  while len(rescan) > 0:
    base = rescan.pop(0)
    childs = overridemap[base]
    prev = len(childs)
    temp = childs.union(*(overridemap.get(sub, []) for sub in childs))
    childs.update(temp)
    if len(childs) != prev:
      rescan.append(base)
  targets = []
  for base, childs in overridemap.iteritems():
    targets.append({"targetid": -base, "funcid": base})
    for child in childs:
      targets.append({"targetid": -base, "funcid": child})
  for call in callgraph:
    if call['calltype'] == 'virtual':
      targetid = call['targetid']
      call['targetid'] = -targetid
      if targetid not in overridemap:
        overridemap[targetid] = set()
        targets.append({'targetid': -targetid, 'funcid': targetid})

  # Ball it up for passing on
  blob = {}
  def mdict(info, key):
    return (info[key], info)
  blob["typedefs"] = [typedefs[t] for t in typedefs]
  blob["refs"] = refs
  blob["warnings"] = warnings
  blob["decldef"] = decldef
  blob["macros"] = macros
  blob["callers"] = callgraph
  blob["targets"] = targets
  # Add to the languages table
  register_language_table("native", "scopes", dict((scopes[s],
    {"scopeid": scopes[s], "sname": s[0], "sloc": s[1]}) for s in scopes))
  register_language_table("native", "types", (types[t] for t in typeKeys))
  register_language_table("native", "types", blob["typedefs"])
  register_language_table("native", "functions",
    dict(mdict(functions[f], "funcid") for f in funcKeys))
  register_language_table("native", "variables",
    dict(mdict(variables[v], "varid") for v in varKeys))
  register_language_table("native", "impl", inheritsTree)
  return blob

def post_process(srcdir, objdir):
  os.path.walk(objdir, collect_files, get_idx_ext())
  for f in file_names:
    load_indexer_output(f)
  blob = make_blob()
  return blob

def pre_html_process(treecfg, blob):
  blob["byfile"] = dxr.plugins.break_into_files(blob, {
    "refs": "refloc",
    "warnings": "wloc",
    "decldef": "declloc",
    "macros": "macroloc"
  })

def sqlify(blob):
  return schema.get_data_sql(blob)

def can_use(treecfg):
  # We need to have clang and llvm-config in the path
  if not dxr.plugins.in_path('clang'):
    raise BaseException("No 'clang' installed")

  if not dxr.plugins.in_path('llvm-config'):
    raise BaseException("No 'llvm-config' installed")

  return dxr.plugins.in_path('clang') and dxr.plugins.in_path('llvm-config')

schema = dxr.plugins.Schema({
  # Typedef information in the tables
  "typedefs": [
    ("tid", "INTEGER", False),           # The typedef's tid (also in types)
    ("ttypedef", "VARCHAR(256)", False), # The long name of the type
    ("_key", "tid")
  ],
  # References to functions, types, variables, etc.
  "refs": [
    ("refid", "INTEGER", False),      # ID of the identifier being referenced
    ("refloc", "_location", False),   # Location of the reference
    ("extent", "VARCHAR(30)", False), # Extent (start:end) of the reference
    ("_key", "refid", "refloc")
  ],
  # Warnings found while compiling
  "warnings": {
    "wloc": ("_location", False),   # Location of the warning
    "wmsg": ("VARCHAR(256)", False) # Text of the warning
  },
  # Declaration/definition mapping
  "decldef": {
    "defid": ("INTEGER", False),    # ID of the definition instance
    "declloc": ("_location", False) # Location of the declaration
  },
  # Macros: this is a table of all of the macros we come across in the code.
  "macros": [
     ("macroid", "INTEGER", False),        # The macro id, for references
     ("macroloc", "_location", False),     # The macro definition
     ("macroname", "VARCHAR(256)", False), # The name of the macro
     ("macroargs", "VARCHAR(256)", True),  # The args of the macro (if any)
     ("macrotext", "TEXT", True),          # The macro contents
     ("_key", "macroid", "macroloc"),
  ],
  # The following two tables are combined to form the callgraph implementation.
  # In essence, the callgraph can be viewed as a kind of hypergraph, where the
  # edges go from functions to sets of functions and variables. For use in the
  # database, we are making some big assumptions: the targetid is going to be
  # either a function or variable (the direct thing we called); if the function
  # is virtual or the target is a variable, we use the targets table to identify
  # what the possible implementations could be.
  "callers": [
    ("callerid", "INTEGER", False), # The function in which the call occurs
    ("targetid", "INTEGER", False), # The target of the call
    ("_key", "callerid", "targetid")
  ],
  "targets": [
    ("targetid", "INTEGER", False), # The target of the call
    ("funcid", "INTEGER", False),   # One of the functions in the target set
    ("_key", "targetid", "funcid")
  ]
})

get_schema = dxr.plugins.make_get_schema_func(schema)

import dxr
from dxr.tokenizers import CppTokenizer
class CxxHtmlifier:
  def __init__(self, blob, srcpath, treecfg):
    self.source = dxr.readFile(srcpath)
    self.srcpath = srcpath.replace(treecfg.sourcedir + '/', '')
    self.blob_file = blob["byfile"].get(self.srcpath, None)

  def collectSidebar(self):
    if self.blob_file is None:
      return
    def line(linestr):
      return linestr.split(':')[1]
    def make_tuple(df, name, loc, scope="scopeid", decl=False):
      if decl:
        img = 'images/icons/page_white_code.png'
      else:
        loc = df[loc]
        img = 'images/icons/page_white_wrench.png'
      if scope in df and df[scope] > 0:
        return (df[name], loc.split(':')[1], df[name], img,
          dxr.languages.get_row_for_id("scopes", df[scope])["sname"])
      return (df[name], loc.split(':')[1], df[name], img)
    for df in self.blob_file["types"]:
      yield make_tuple(df, "tqualname", "tloc", "scopeid")
    for df in self.blob_file["functions"]:
      yield make_tuple(df, "fqualname", "floc", "scopeid")
    for df in self.blob_file["variables"]:
      if "scopeid" in df and dxr.languages.get_row_for_id("functions", df["scopeid"]) is not None:
        continue
      yield make_tuple(df, "vname", "vloc", "scopeid")
    tblmap = { "functions": "fqualname", "types": "tqualname" }
    for df in self.blob_file["decldef"]:
      table = df["table"]
      if table in tblmap:
        yield make_tuple(dxr.languages.get_row_for_id(table, df["defid"]), tblmap[table],
          df["declloc"], "scopeid", True)
    for df in self.blob_file["macros"]:
      yield make_tuple(df, "macroname", "macroloc")

  def getSyntaxRegions(self):
    self.tokenizer = CppTokenizer(self.source)
    for token in self.tokenizer.getTokens():
      if token.token_type == self.tokenizer.KEYWORD:
        yield (token.start, token.end, 'k')
      elif token.token_type == self.tokenizer.STRING:
        yield (token.start, token.end, 'str')
      elif token.token_type == self.tokenizer.COMMENT:
        yield (token.start, token.end, 'c')
      elif token.token_type == self.tokenizer.PREPROCESSOR:
        yield (token.start, token.end, 'p')

  def getLinkRegions(self):
    if self.blob_file is None:
      return
    def make_link(obj, clazz, rid):
      start, end = obj['extent'].split(':')
      start, end = int(start), int(end)
      kwargs = {}
      kwargs['rid'] = rid
      kwargs['class'] = clazz
      return (start, end, kwargs)
    tblmap = {
      "variables": ("var", "varid"),
      "functions": ("func", "funcid"),
      "types": ("t", "tid"),
      "refs": ("ref", "refid"),
    }
    for tablename in tblmap:
      tbl = self.blob_file[tablename]
      kind, rid = tblmap[tablename]
      for df in tbl:
        if 'extent' in df:
          yield make_link(df, kind, df[rid])
    for decl in self.blob_file["decldef"]:
      if 'extent' not in decl: continue
      yield make_link(decl, tblmap[decl["table"]][0], decl["defid"])
    for macro in self.blob_file["macros"]:
      line, col = macro['macroloc'].split(':')[1:]
      line, col = int(line), int(col)
      yield ((line, col), (line, col + len(macro['macroname'])),
        {'class': 'm', 'rid': macro['macroid']})

  def getLineAnnotations(self):
    if self.blob_file is None:
      return
    for warn in self.blob_file["warnings"]:
      line = int(warn["wloc"].split(":")[1])
      yield (line, {"class": "lnw", "title": warn["wmsg"]})

def get_sidebar_links(blob, srcpath, treecfg):
  if srcpath not in htmlifier_store:
    htmlifier_store[srcpath] = CxxHtmlifier(blob, srcpath, treecfg)
  return htmlifier_store[srcpath].collectSidebar()
def get_link_regions(blob, srcpath, treecfg):
  if srcpath not in htmlifier_store:
    htmlifier_store[srcpath] = CxxHtmlifier(blob, srcpath, treecfg)
  return htmlifier_store[srcpath].getLinkRegions()
def get_line_annotations(blob, srcpath, treecfg):
  if srcpath not in htmlifier_store:
    htmlifier_store[srcpath] = CxxHtmlifier(blob, srcpath, treecfg)
  return htmlifier_store[srcpath].getLineAnnotations()
def get_syntax_regions(blob, srcpath, treecfg):
  if srcpath not in htmlifier_store:
    htmlifier_store[srcpath] = CxxHtmlifier(blob, srcpath, treecfg)
  return htmlifier_store[srcpath].getSyntaxRegions()
htmlifier_store = {}

htmlifier = {}
for f in ('.c', '.cc', '.cpp', '.h', '.hpp'):
  htmlifier[f] = {'get_sidebar_links': get_sidebar_links,
      'get_link_regions': get_link_regions,
      'get_line_annotations': get_line_annotations,
      'get_syntax_regions': get_syntax_regions}

def get_htmlifiers():
  return htmlifier

def get_idx_ext():
  return ".xml"

__all__ = dxr.plugins.required_exports()
