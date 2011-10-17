from xml.etree import cElementTree as ET
from dxr.languages import register_language_table
import dxr.plugins
import os

g_decl_master = {}
g_types = {}
g_warnings = []
g_calls = {}
g_htmlifier_store = {}
g_htmlifier = {}
g_file_names = []
g_htmlifier_current = None
g_htmlifier_current_path = None
g_doxygenId={}
g_srcdir=''


def validate(o,ref):
  for r in ref:
    if r not in o:
      dxr.errorPrint("incomplete object:%s" % o )
      raise

class Macros:
  def __init__(self):
    self.macros={}
  def add(self,m):
    validate(m,['name','loc','text'])
    if m['text'] == None:
      m['text']=''
    self.macros[m['name'],m['loc']]=m
  def get(self):
    return self.macros
g_macros = Macros()

class References:
  def __init__(self):
    self.references={}
  def add(self,m):
    validate(m,['name','loc'])
    self.references[m['name'],m['loc']]=m
  def get(self):
    return self.references
g_references = References()

class Inheritances:
  def __init__(self):
    self.storage = {}
  def add(self,m):
    self.storage[m['tbid'], m['tbloc'], m['tcname'], m['tcloc']]=m
  def get(self):
    return self.storage
g_inheritance = Inheritances()


class Functions:
  def __init__(self):
    self.storage={}
  def add(self,m):
    validate(m,['id','name','qualname','type','args','loc','extent'])
    if m['name'] == None:
      raise Exception("Null function name:%s"%m)
    self.storage[(m['qualname'], m['loc'])] = m
  def get(self):
    return self.storage
g_functions = Functions()

class Variables:
  def __init__(self):
    self.storage = {}

  def add(self,m):
    validate(m,['name','loc','qualname'])
    self.storage[m['name'],m['loc']] = m

  def get(self):
    return self.storage

  def __contains__(self,v):
    return v in self.storage

g_variables = Variables()

class Typedefs:
  def __init__(self):
    self.storage = {}

  def add(self,m):
    validate(m,['name','loc','qualname'])
    self.storage[m['name'],m['loc']] = m
  def get(self):
    return self.storage
  def __contains__(self,v):
    return v in self.storage
g_typedefs = Typedefs()

if dxr.debugLvl is None:
        dxr.debugLvl=2

def get_text(node):
    return node.text

#def process_type(node,compoundname):
#    meta = { 'tname':'', 'qualname':'', 'loc':'', 'tkind':'enum','scopename':'' }
#    for chld in node.getchildren():
#            if chld.tag == "name":
#                    if get_text(chld) == '': return
#                    meta['tname'] = get_text(chld)
#                    meta['qualname'] = "%s::%s" % (compoundname,get_text(chld))
#            if chld.tag == "location":
#                    meta['loc'] = "%s:%s:%s" %( chld.attrib['file'],chld.attrib['line'],chld.attrib['column'])
#    meta['scopename']=compoundname
#    print "Extracted: Type %s(%s) -> %s" % (meta['qualname'],meta['scopename'],meta['loc'])
#    g_types[(meta['qualname'], meta['loc'])] = meta

def process_enum(node,compoundname):
    meta = { 'tname':None, 'qualname':None, 'loc':None, 'tkind':'enum','scopename':None}
    for chld in node.getchildren():
            if chld.tag == "name":
                    if get_text(chld) == '': return
                    meta['tname'] = get_text(chld)
                    meta['qualname'] = "%s::%s" % (compoundname,get_text(chld))
            if chld.tag == "location":
                    meta['loc'] = "%s:%s:%s" %( strip_srcdir(chld.attrib['file']),chld.attrib['line'],chld.attrib['column'])
    meta['scopename']=compoundname
    dxr.debugPrint(3, "Extracted: Type %s(%s) -> %s" % (meta['qualname'],meta['scopename'],meta['loc']) )
    g_types[(meta['qualname'], meta['loc'])] = meta

def process_compounddef(node):
    meta = { 'tname':None, 'qualname':None, 'loc':None, 'tkind':'enum','scopename':None }
    meta['tkind'] = node.attrib['kind']
    if meta['tkind'] != 'struct' and \
        meta['tkind'] != 'class':
        return

    for chld in node.getchildren():
        if chld.tag == 'compoundname':
            meta['tname'] = get_text(chld)
            meta['qualname'] = get_text(chld)
        if chld.tag == 'location':
            meta['loc'] = "%s:%s:%s" %( strip_srcdir(chld.attrib['file']),chld.attrib['line'],chld.attrib['column'])
    dxr.debugPrint(3,"Extracted: Compound %s -> %s" % (meta['qualname'],meta['loc']))
    g_types[(meta['qualname'], meta['loc'])] = meta



#def process_typedef(node):
#    meta = { 'qualname':'', 'loc':'', 'tkind':'typedef' }
#    for chld in node.getchildren():
#            if chld.tag == "name":
#                    if get_text(chld) == '': return
#                    meta['tname'] = get_text(chld)
#                    meta['qualname'] = get_text(chld)
#            if chld.tag == "location":
#                    meta['loc'] = "%s:%s:%s" %( chld.attrib['file'],chld.attrib['line'],chld.attrib['column'])
#    g_typedefs[(meta['qualname'], meta['loc'])] = meta

#def process_decldef(args):
#    name, defloc, declloc = args['name'], args['defloc'], args['declloc']
#    g_decl_master[(name, declloc)] = defloc
#    g_decl_master[(name, defloc)] = defloc
#    dxr.debugPrint(3,"Extracted: Declaration %s -> %s" % (meta['qualname'],meta['loc']))

#def process_call(call):
#    if 'callername' in call:
#        g_calls[call['callername'], call['callerloc'],
#                    call['calleename'], call['calleeloc']] = call
#    else:
#        g_calls[call['calleename'], call['calleeloc']] = call

def process_referencedby(m,node):
    # Each reference is pretty much unique,
    # but we might record it several times
    # due to header files.
    dxr.debugPrint(3,"REFERENCE:%s->%s" %(m['name'],get_text(node)))
    refid=node.attrib['refid']

    # XXX refloc is here, only so split_byfile can work.
    meta={ 'name': m['name'],
            'loc': m['loc'],
          'refid': refid,
         'extent': '1:10' } # XXX: Fix the extent
    g_references.add(meta)

    #XXX calltype proper
    call={'calleename':m['name'], 'calleeloc':m['loc'], 'calltype':'native'}
    g_calls[ m['name'], get_text(node), m['loc'], refid ] = call

def strip_srcdir(p):
    return p.replace(g_srcdir+'/','')

def process_function(node):
    meta = {'id':None, 'name': None, 'qualname':None, 'type':'', 'args':[], 'loc':None, 'extent':None}
    meta['id'] = node.attrib['id']
    decl=False
    try:
        for chld in node.getchildren():
            if chld.tag == "declaration":
                decl=True
            if chld.tag == "name":
                if get_text(chld) == '': return
                meta['name'] = get_text(chld)
                meta['qualname'] = get_text(chld)
            if chld.tag == "referencedby":
                if get_text(chld) == '': return
                process_referencedby(meta,chld)
            #if chld.tag == "references":
            #    if get_text(chld) == '': return
            #    process_references(meta,chld)
            if chld.tag == "argsstring":
                meta['args'] = get_text(chld)
            if chld.tag == "location":
                meta['loc'] = "%s:%s:%s" %( strip_srcdir(chld.attrib['file']),chld.attrib['line'],chld.attrib['column'])
                meta['extent']="%s:%d" % (chld.attrib['column'],int(chld.attrib['column'])+len(meta['name']))

        dxr.debugPrint(3,"Extracted: Function (%s,%s)" % (meta['qualname'],meta['loc']))
        g_functions.add(meta)
        g_doxygenId[meta['id']]=meta
    except Exception,e:
        raise Exception( "xml-error:%s"%e)
    if decl==True:
        name, defloc, declloc = meta['qualname'], meta['loc'], meta['loc']
        # XXX
        defloc = "test.cpp:48:1"
        g_decl_master[(name, declloc)] =defloc
        g_decl_master[(name, defloc)]  =defloc
        dxr.debugPrint(3, "Extracted: Function Decl %s -> %s" % (meta['qualname'],meta['loc']))


def process_inheritance(node):
    meta={'tbid':None,'tbloc':None,'tcname':None,'tcloc':None,'access':None}
    nodes={}
    dxr.debugPrint(3, "Process inheritance")
    for n1 in node.getchildren():
        if n1.tag == "node":
            id_=""
            for n2 in n1.getchildren():
                if n2.tag == "label":
                    id_=n1.attrib['id']
                    nodes[id_]=get_text(n2)
                if n2.tag == "childnode":
                    meta['access']=n2.attrib['relation']
                    meta['tbid']=n2.attrib['refid']
                    meta['tcname']=nodes[id_]
                    meta['tbloc']="test.cpp:29:1"
                    meta['tcloc']="test.cpp:39:1"
                    g_inheritance.add(meta)


def process_variable(node):
    meta = { 'name':None, 'loc':None}
    for chld in node.getchildren():
            if chld.tag == "name":
                    if get_text(chld) == '': return
                    meta['qualname'] = meta['name'] = get_text(chld)
            if chld.tag == "location":
                    meta['loc'] = "%s:%s:%s" %( strip_srcdir(chld.attrib['file']),chld.attrib['line'],chld.attrib['column'])
    dxr.debugPrint(3,"Extracted: Variable %s -> %s" % (meta['name'],meta['loc']))

    g_variables.add(meta)

def process_warning(warning):
    g_warnings.append(warning)

def process_define(node):
    meta = {'name':None, 'loc':None,'text':None}
    for chld in node.getchildren():
            if chld.tag == "name":
                    if get_text(chld) == '': return
                    meta['qualname'] = meta['name'] = get_text(chld)
            if chld.tag == "initializer":
                    meta['text'] = get_text(chld)
            if chld.tag == "location":
                    meta['loc'] = "%s:%s:%s" % ( strip_srcdir(chld.attrib['file']),chld.attrib['line'],chld.attrib['column'])
                    meta['extent']="%s:%d" % (chld.attrib['column'],int(chld.attrib['column'])+5)
    dxr.debugPrint(3, "Extracted: Macro %s -> %s" % (meta['name'],meta['loc']))
    g_macros.add(meta)
    if 'text' in meta:
        try:
            meta['text'] = meta['text'].replace("\\\n", "\n").strip()
        except Exception,e:
            raise Exception("define Error:%s"%e)

def load_indexer_output(name):
    context = ET.iterparse(name, events=("start", "end"))
    for event, elem in context:
        if event == "end" and elem.tag == "includes":
            pass
        if event == "end" and elem.tag == "compounddef":
            process_compounddef(elem)
        if event == "end" and elem.tag == "inheritancegraph":
            process_inheritance(elem)
        if event == "end" and elem.tag == "memberdef":
            if elem.attrib['kind'] == 'define':
                process_define(elem)
            if elem.attrib['kind'] == 'function':
                process_function(elem)
            if elem.attrib['kind'] == 'variable':
                process_variable(elem)
            if elem.attrib['kind'] == 'enum':
                process_enum(elem,"compoundname")
            #if elem.attrib['kind'] == 'typedef':
            #     process_typedef(elem)



def collect_files(arg, dirname, fnames):
    for name in fnames:
        if os.path.isdir(name): continue
        if not name.endswith(arg): continue
        g_file_names.append(os.path.join(dirname, name))

def make_blob():
    def canonicalize_decl(name, loc):
        return (name, g_decl_master.get((name, loc), loc))

    def recanon_decl(name, loc):
        g_decl_master[name, loc] = (name, loc)
        return (name, loc)

    # Inheritance:
    # We need to canonicalize the g_types
    # and then set up the inheritance tree.
    # Since we don't know which order
    # we'll see the pairs, we have to propagate
    # bidirectionally when we find out more.
    def build_inherits(base, child, direct):
        db = { 'tbase': base, 'tderived': child }
        if direct is not None:
            db['inhtype'] = direct
        return db

    # Fix up (name, loc) pairs to ids
    def repairScope(info):
        if 'scopename' in info:
            try:
                info['scopeid'] = scopes[canonicalize_decl(info.pop('scopename'),
                    info.pop('scopeloc'))]
            except KeyError:
                info['scopeid'] = 0
                pass
        else:
            info['scopeid'] = 0

    def mdict(info, key):
        return (info[key], info)

    # Produce all scopes
    scopes = {}
    typeKeys = set()
    for t in g_types:
        key = canonicalize_decl(t[0], t[1])
        if key not in g_types:
            key = recanon_decl(t[0], t[1])
        if key not in scopes:
            typeKeys.add(key)
            g_types[key]['id'] = scopes[key] = dxr.plugins.next_global_id()

    # Typedefs need a id, but they are not a scope
    for t in g_typedefs.get():
        g_typedefs[t]['id'] = dxr.plugins.next_global_id()

    funcKeys = set()
    for f in g_functions.get():
        key = canonicalize_decl(f[0], f[1])
        if key not in g_functions.get():
            key = recanon_decl(f[0], f[1])
        if key not in scopes:
            funcKeys.add(key)
            g_functions.get()[key]['id'] = scopes[key] = dxr.plugins.next_global_id()

    # Variables aren't scoped, but we still need to refer to them in the same
    # manner, so we'll unify variables with the scope ids
    varKeys = {}
    for v in g_variables.get():
        key = (v[0], v[1])
        if key not in varKeys:
            varKeys[key] = g_variables.get()[v]['id'] = dxr.plugins.next_global_id()

    for m in g_macros.get():
        g_macros.get()[m]['id'] = dxr.plugins.next_global_id()

    # Scopes are now defined,
    # this allows us to modify structures for sql prep

    childMap, parentMap = {}, {}
    inheritsTree = []
    for infoKey in g_inheritance.get():
        info = g_inheritance.get()[infoKey]
        dxr.debugPrint(2, "inherit base: %s" % (info['tbid']))
        try:
            base = g_types[canonicalize_decl(info['tbid'], info['tbloc'])]['id']
            child = g_types[canonicalize_decl(info['tcname'], info['tcloc'])]['id']
        except KeyError,(Error):
            dxr.errorPrint( "key-error%s"%Error )
            #raise
            #XXX choose btwn raise or continue
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

    for tkey in typeKeys:
        # XXX problem with the scopename/scopid in g_types
        repairScope(g_types[tkey])

    for tkey in g_typedefs.get():
        repairScope(g_typedefs.get()[tkey])

    for fkey in funcKeys:
        repairScope(g_functions.get()[fkey])

    for vkey in varKeys:
        repairScope(g_variables.get()[vkey])

    # dicts can't be stuffed in sets, and our key is very
    # unwieldy. Since duplicates are most likely to
    # occur only when we include the same header file
    # multiple times, the same definition should be used
    # each time, so they should be equivalent
    # pre-canonicalization
    blob_refs = []
    for rkey in g_references.get():
        ref = g_references.get()[rkey]
        dxr.debugPrint(5,"BEFORE:%s" % ref)
        canon = canonicalize_decl(ref['name'], ref['loc'])
        if canon in varKeys:
            ref['id'] = varKeys[canon]
            blob_refs.append(ref)
        elif canon in funcKeys:
            ref['id'] = g_functions.get()[canon]['id']
            blob_refs.append(ref)
        elif canon in typeKeys:
            ref['id'] = g_types[canon]['id']
            blob_refs.append(ref)
        elif canon in g_typedefs.get():
            ref['id'] = g_typedefs[canon]['id']
            blob_refs.append(ref)
        elif canon in g_macros.get():
            ref['id'] = g_macros.get()[canon]['id']
            blob_refs.append(ref)
        dxr.debugPrint(5,"AFTER:%s" % ref)

    # Declaration-definition remapping
    blob_decldef = []
    for decl in g_decl_master:
        defn = (decl[0], g_decl_master[decl])
        #print "(%s,g_decl:%s" %(decl[0],g_decl_master[decl])
        if defn == decl: continue
        tmap = [ ('types', g_types, 'id'),
                 ('types', g_typedefs, 'id'),
                 ('variables', g_variables, 'id'),
                 ('functions', g_functions.get(), 'id'),
               ]
        for (tname, tdict, tkey) in tmap:
            try:
                if defn in tdict:
                    ndecl = { "declloc":decl[1],
                              "defid":tdict[defn][tkey],
                              "table":tname
                            }
                    if "extent" in tdict[decl]:
                        ndecl["extent"] = tdict[decl]["extent"]
                    blob_decldef.append(ndecl)
                    break
            except:
                print "tname:%s" % tname
		raise

    callgraph = []
    if g_calls == {}:
        dxr.warningPrint( "Something is wrong, cause g_calls is empty" )
    for callkey in g_calls:
        call   = g_calls[callkey]
        dxr.debugPrint(4,"callkey:%s:%s:%s"% (callkey[0],callkey[1],callkey[2]))
	if callkey[3] not in g_doxygenId:
		raise Exception("id not found:%s"%callkey[3])
        caller = g_doxygenId[callkey[3]]
        call['callerid'] = g_functions.get()[(caller['name'],caller['loc'])]['id']
        #callee = canonicalize_decl(call.pop("calleename"), call.pop("calleeloc"))
        callee = (call["calleename"], call["calleeloc"])

        if callee in g_functions.get():
            call['targetid'] = g_functions.get()[callee]['id']
        elif callee in g_variables.get():
            call['targetid'] = g_variables.get()[callee]['id']
        else:
            dxr.errorPrint( "callee not found: (%s,%s)" % (callee[0],callee[1]) )
        if 'targetid' in call:
            callgraph.append(call)

    overridemap = {}
    for func in funcKeys:
        funcinfo = g_functions.get()[func]
        if "overridename" not in funcinfo:
            continue
        base = canonicalize_decl(funcinfo.pop("overridename"),
            funcinfo.pop("overrideloc"))
        if base not in g_functions.get():
            continue
        basekey = g_functions.get()[base]['id']
        subkey = funcinfo['id']
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
    blob_targets = []
    for base, childs in overridemap.iteritems():
        blob_targets.append({"targetid": -base, "id": base})
        for child in childs:
            blob_targets.append({"targetid": -base, "id": child})
    for call in callgraph:
        if call['calltype'] == 'virtual':
            targetid = call['targetid']
            call['targetid'] = -targetid
            if targetid not in overridemap:
                overridemap[targetid] = set()
                blob_targets.append({'targetid': -targetid, 'id': targetid})

    # Ball it up for passing on
    blob = {}
    blob["typedefs"] = [g_typedefs.get()[t] for t in g_typedefs.get()]
    blob["warnings"] = g_warnings
    blob["macros"]  = g_macros.get()
    blob["decldef"] = blob_decldef
    blob["callers"] = callgraph
    blob["refs"]    = blob_refs
    blob["targets"] = blob_targets
    blob["functions"] = dict(mdict(g_functions.get()[f], "id") for f in funcKeys)
    blob["variables"] = dict(mdict(g_variables.get()[v], "id") for v in varKeys)

    # Add to the languages table
    register_language_table("native", "functions", dict(mdict(g_functions.get()[f], "id") for f in funcKeys))
    register_language_table("native", "impl", inheritsTree)
    register_language_table("native", "scopes", dict((scopes[s], {"scopeid": scopes[s], "sname": s[0], "sloc": s[1]}) for s in scopes))
    register_language_table("native", "types", (g_types[t] for t in typeKeys))
    register_language_table("native", "types", blob["typedefs"])
    register_language_table("native", "variables", dict(mdict(g_variables.get()[v], "id") for v in varKeys))
    dxr.debugPrint(4,"CCC:%s"%blob)
    return blob

def post_process(srcdir, objdir):
    global g_srcdir
    g_srcdir=srcdir
    os.path.walk(objdir, collect_files, get_idx_ext())
    print "collecting indexer files from %s" % objdir
    for f in g_file_names:
        load_indexer_output(f)
    blob=make_blob()
    dxr.debugPrint(4,"BBBB%s"%blob)
    return blob

def pre_html_process(treecfg, blob):
    dxr.debugPrint(4,"blob2: %s" %blob)
    blob["byfile"] = dxr.plugins.break_into_files(
    blob, {
        "refs": "loc",
        "warnings": "wloc",
        "decldef": "declloc",
        "macros": "loc",
        "functions" : "loc",
        "variables" : "loc",
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
        ("id", "INTEGER", False),                     # The typedef's id (also in g_types)
        ("ttypedef", "VARCHAR(256)", False), # The long name of the type
        ("_key", "id")
    ],
    # References to functions, g_types, variables, etc.
    "refs": [
        ("id", "INTEGER", False),            # ID of the identifier being referenced
        ("loc", "_location", False),     # Location of the reference
        ("extent", "VARCHAR(30)", False), # Extent (start:end) of the reference
        ("_key", "id", "loc")
    ],
    # Warnings found while compiling
    "warnings": {
        "wloc": ("_location", False),     # Location of the warning
        "wmsg": ("VARCHAR(256)", False) # Text of the warning
    },
    # Declaration/definition mapping
    "decldef": {
        "defid": ("INTEGER", False),        # ID of the definition instance
        "declloc": ("_location", False) # Location of the declaration
    },
    # Macros: this is a table of all of the macros we come across in the code.
    "macros": [
         ("id", "INTEGER", False),                # The macro id, for references
         ("loc", "_location", False),         # The macro definition
         ("name", "VARCHAR(256)", False), # The name of the macro
         ("args", "VARCHAR(256)", True),    # The args of the macro (if any)
         ("text", "TEXT", True),                    # The macro contents
         ("_key", "id", "loc"),
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
        ("id", "INTEGER", False),     # One of the functions in the target set
        ("_key", "targetid", "id")
    ]
})

get_schema = dxr.plugins.make_get_schema_func(schema)

import dxr
from dxr.tokenizers import CppTokenizer
class CxxHtmlifier:
    def __init__(self, blob, srcpath, treecfg,conn):
        self.source = dxr.readFile(srcpath)
        self.srcpath = srcpath.replace(treecfg.sourcedir + '/', '')
        self.blob_file = blob["byfile"].get(self.srcpath, None)
        self.conn = conn
        #XXX: too verbose print "self.srcpath:%s" % blob["byfile"]

    def collectSidebar(self):
        if self.blob_file is None:
            return
        def line(linestr):
            return linestr.split(':')[1]
        imgMap= {
           "functions":'images/icons/flag_blue.png',
           "types":'images/icons/script_code.png',
           "macros":'images/icons/tag.png',
           "variables":'images/icons/page_white_code.png',
        }
        def make_tuple(t, df, name, loc, scope="scopeid", decl=False):
            if decl:
                img = 'images/icons/page_white_code.png'
            else:
                loc = df[loc]
                img = imgMap[t]

            if scope in df and df[scope] > 0:
                return (df[name], loc.split(':')[1], df[name], img,
                    dxr.languages.get_row_for_id("scopes", df[scope])["sname"])
            return (df[name], loc.split(':')[1], df[name], img)

        tblmap = [ "functions", "types", "macros", "variables" ]
        for tbl in tblmap:
            for df in self.blob_file[tbl]:
                yield make_tuple(tbl, df, "qualname", "loc", "scopeid")
        for df in self.blob_file["decldef"]:
            if df["table"] not in tblmap: continue
            row=dxr.languages.get_row_for_id(df["table"], df["defid"])
            yield make_tuple(row, "qualname", df["declloc"], "scopeid", True)
        #for df in self.blob_file["variables"]:
        #    if "scopeid" in df and dxr.languages.get_row_for_id("functions", df["scopeid"]) is not None:
        #        continue
        #    yield make_tuple(df, "name", "loc", "scopeid")

    def getSyntaxRegions(self):
        self.tokenizer = CppTokenizer(self.source)
        self.tokenCssClass = {
             self.tokenizer.KEYWORD:'k',
             self.tokenizer.STRING:'str',
             self.tokenizer.COMMENT:'c',
             self.tokenizer.PREPROCESSOR:'m' }
        for tk in self.tokenizer.getTokens():
            if tk.token_type in self.tokenCssClass:
                yield (tk.start,
                       tk.end,
                       self.tokenCssClass[tk.token_type]
                      )

    def getLinkRegions(self):
        if self.blob_file is None:
            dxr.errorPrint( "blob_file is None for %s" % self.srcpath )
            return
        def make_link(obj, clazz, rid):
            startC, endC = obj['extent'].split(':')
            startC, endC = int(startC), int(endC)
            try:
                startL=int(obj['loc'].split(':')[1])
            except:
                dxr.errorPrint( "Failed to get 'loc': %s<" % (obj) )
            kwargs = {}
            kwargs['rid'] = rid
            kwargs['class'] = clazz
            return ((startL,startC), (startL,endC), kwargs)
        tblmap = {
            "variables": ("var", "id"),
            "functions": ("func", "id"),
            "types": ("t", "id"),
            #XXX "refs": ("ref", "id"),
        }
        for tablename in tblmap:
            tbl = self.blob_file[tablename]
            kind, rid = tblmap[tablename]
            for df in tbl:
                if 'extent' in df:
                    yield make_link(df, kind, df[rid])
        for decl in self.blob_file["decldef"]:
            if 'extent' not in decl: continue
            #yield make_link(decl, tblmap[decl["table"]][0], decl["defid"])
            #XXX
            yield ( (46, 1), (46, 14),
                {'class': 'func', 'rid': decl['defid']})
        for macro in self.blob_file["macros"]:
            line, col = macro['loc'].split(':')[1:]
            line, col = int(line), int(col)
            yield ((line, col), (line, col + len(macro['name'])),
                {'class': 'm', 'rid': macro['id']})

    def getLineAnnotations(self):
        if self.blob_file is None:
            return
        for warn in self.blob_file["warnings"]:
            line = int(warn["wloc"].split(":")[1])
            yield (line, {"class": "lnw", "title": warn["wmsg"]})

def ensureHtmlifier(blob, srcpath, treecfg, conn=None, dbpath=None):
  global g_htmlifier_current_path
  global g_htmlifier_current

  if srcpath != g_htmlifier_current_path:
    g_htmlifier_current_path = srcpath

    if dbpath is None:
      dbpath = srcpath

    g_htmlifier_current = CxxHtmlifier(blob, dbpath, treecfg, conn)
    g_htmlifier_current.tokenizer = CppTokenizer(dxr.readFile(srcpath))

  return g_htmlifier_current

def get_sidebar_links(blob, srcpath, treecfg,conn=None,dbpath=None):
  g_htmlifier = ensureHtmlifier(blob, srcpath, treecfg, conn, dbpath)
  return g_htmlifier.collectSidebar()
def get_link_regions(blob, srcpath, treecfg, conn=None, dbpath=None):
  g_htmlifier = ensureHtmlifier(blob, srcpath, treecfg, conn, dbpath)
  return g_htmlifier.getLinkRegions()
def get_line_annotations(blob, srcpath, treecfg, conn=None, dbpath=None):
  g_htmlifier = ensureHtmlifier(blob, srcpath, treecfg, conn, dbpath)
  return g_htmlifier.getLineAnnotations()
def get_syntax_regions(blob, srcpath, treecfg, conn=None, dbpath=None):
  g_htmlifier = ensureHtmlifier(blob, srcpath, treecfg, conn, dbpath)
  return g_htmlifier.getSyntaxRegions()


for f in ('.c', '.cc', '.cpp', '.h', '.hpp'):
    g_htmlifier[f] = {
            'get_sidebar_links': get_sidebar_links,
            'get_link_regions': get_link_regions,
            'get_line_annotations': get_line_annotations,
            'get_syntax_regions': get_syntax_regions}

def get_htmlifiers():
    return g_htmlifier

def get_idx_ext():
    return ".xml"

__all__ = dxr.plugins.required_exports()
