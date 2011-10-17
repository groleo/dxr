#!/usr/bin/python2.7

import json
import cgitb; cgitb.enable()
import cgi
import sqlite3
import ConfigParser
import os

def locUrl(loc):
  path, line = loc.split(':')[:2]
  return '%s%s/%s.html#l%s' % (virtroot, tree, path, line)

def getDeclarations(defid):
  cur = conn.execute("SELECT declloc FROM decldef WHERE defid=?",(defid,))
  decls = []
  for declloc, in cur:
    decls.append({ "label": "Declared at %s" % (declloc),
      "icon": "icon-decl",
      "url": locUrl(declloc)
    })
  return decls

def getType(typeinfo, refs=[], deep=False):
  if isinstance(typeinfo, int):
    typeinfo = conn.execute("SELECT * FROM types WHERE id=?",
      (typeinfo,)).fetchone()
  typebase = {
    "label": '%s %s' % (typeinfo['tkind'], typeinfo['qualname']),
    "icon": "icon-type",
    "children": [{
      "label": 'Definition at %s' % (typeinfo['loc']),
      "icon": "icon-def",
      "url": locUrl(typeinfo['loc'])
    }]
  }
  for typedef in conn.execute("SELECT * FROM typedefs WHERE id=?",
      (typeinfo['id'],)):
    typebase['children'].append({
      "label": 'Real value %s' % (typedef['ttypedef']),
      'icon': 'icon-def'
    })
  typebase['children'].extend(getDeclarations(typeinfo['id']))
  if not deep:
    return typebase
  members = {
    "label": "Members",
    "icon": "icon-member",
    "children": []
  }
  id = typeinfo['id']
  cur = conn.cursor()
  cur.execute("SELECT id, 't' FROM types WHERE scopeid=? UNION " +
    "SELECT id, 'f' FROM functions WHERE scopeid=? UNION " +
    "SELECT id, 'v' FROM variables WHERE scopeid=?", (id,id,id))
  for memid, qual in cur:
    if qual == 't':
      member = getType(memid)
    elif qual == 'f':
      member = getFunction(memid)
    elif qual == 'v':
      member = getVariable(memid)
    members["children"].append(member)
  if len(members["children"]) > 0:
    typebase["children"].append(members)

  basenode = {
    "label": "Bases",
    "icon": "icon-base",
    "children": []
  }
  derivednode = {
    "label": "Derived",
    "icon": "icon-base",
    "children": []
  }
  cur.execute("SELECT * FROM impl WHERE tbase=?", (id,))
  for derived in cur:
    sub = getType(derived['tderived'])
    sub['label'] = '%s %s' % (sub['label'],
      derived['inhtype'] is None and "(indirect)" or "")
    derivednode["children"].append(sub)
  cur.execute("SELECT * FROM impl WHERE tderived=?", (id,))
  for base in cur:
    sub = getType(base['tbase'])
    sub['label'] = '%s %s' % (sub['label'],
      base['inhtype'] is None and "(indirect)" or base['inhtype'])
    basenode["children"].append(sub)

  if len(basenode["children"]) > 0:
    typebase["children"].append(basenode)
  if len(derivednode["children"]) > 0:
    typebase["children"].append(derivednode)
  
  refnode = {
    "label": "References",
    "children": []
  }
  for ref in refs:
    refnode['children'].append({
      "label": ref["loc"],
      "icon": "icon-def",
      "url": locUrl(ref["loc"])
    })
  if len(refnode['children']) > 0:
    typebase['children'].append(refnode)
  return typebase

def getVariable(varinfo, refs=[]):
  if isinstance(varinfo, int):
    varinfo = conn.execute("SELECT * FROM variables WHERE id=?",
      (varinfo,)).fetchone()
  varbase = {
    "label": '%s %s' % (varinfo['vtype'], varinfo['name']),
    "icon": "icon-member",
    "children": [{
      "label": 'Definition at %s' % (varinfo['loc']),
      "icon": "icon-def",
      "url": locUrl(varinfo['loc'])
    }]
  }
  varbase['children'].extend(getDeclarations(varinfo['id']))
  refnode = {
    "label": "References",
    "children": []
  }
  for ref in refs:
    refnode['children'].append({
      "label": ref["loc"],
      "icon": "icon-def",
      "url": locUrl(ref["loc"])
    })
  if len(refnode['children']) > 0:
    varbase['children'].append(refnode)
  return varbase

def getCallee(targetid):
  cur = conn.cursor()
  cur.execute("SELECT * FROM functions WHERE id=?", (targetid,))
  if cur.rowcount > 0:
    return getFunction(cur.fetchone())
  cur.execute("SELECT * FROM variables WHERE id=?", (targetid,))
  if cur.rowcount > 0:
    return getVariable(cur.fetchone())
  cur.execute("SELECT id FROM targets WHERE targetid=?", (targetid,))
  refnode = { "label": "Dynamic call", "children": [] }
  for row in cur:
    refnode['children'].append(getFunction(row[0]))
  return refnode

def getFunction(funcinfo, refs=[], useCallgraph=False):
  if isinstance(funcinfo, int):
    funcinfo = conn.execute("SELECT * FROM functions WHERE id=?",
      (funcinfo,)).fetchone()
  funcbase = {
    "label": '%s %s%s' % (funcinfo['type'], funcinfo['qualname'], funcinfo['args']),
    "icon": "icon-member",
    "children": [{
      "label": 'Definition at %s' % (funcinfo['loc']),
      "icon": "icon-def",
      "url": locUrl(funcinfo['loc'])
    }]
  }
  # Reimplementations
  for row in conn.execute("SELECT * FROM functions LEFT JOIN targets ON " +
      "targets.id = functions.id WHERE targetid=? AND " +
      "targets.id != ?",
      (-funcinfo['id'], funcinfo['id'])):
    funcbase['children'].append({
      "label": 'Reimplemented by %s%s at %s' % (row['qualname'], row['args'],
        row['loc']),
      "icon": "icon-def",
      "url": locUrl(row['loc'])
    })
  funcbase['children'].extend(getDeclarations(funcinfo['id']))


  # References
  refnode = {
    "label": "References",
    "children": []
  }
  for ref in refs:
    refnode['children'].append({
      "label": ref["loc"],
      "icon": "icon-def",
      "url": locUrl(ref["loc"])
    })
  if len(refnode['children']) > 0:
    funcbase['children'].append(refnode)

  # Callgraph
  if useCallgraph:
    caller = { "label": "Calls", "children": [] }
    callee = { "label": "Called by", "children": [] }
    # This means that we want to display callee/caller information
    for info in conn.execute("SELECT callerid FROM callers WHERE targetid=? " +
        "UNION SELECT callerid FROM callers LEFT JOIN targets " +
        "ON (callers.targetid = targets.targetid) WHERE id=?",
        (funcinfo['id'], funcinfo['id'])):
      callee['children'].append(getFunction(info[0]))
    for info in conn.execute("SELECT targetid FROM callers WHERE callerid=?",
        (funcinfo['id'],)):
      caller['children'].append(getCallee(info[0]))
    if len(caller['children']) > 0:
      funcbase['children'].append(caller)
    if len(callee['children']) > 0:
      funcbase['children'].append(callee)
  return funcbase

def printError():
  print """Content-Type: text/html

<div class="info">Um, this isn't right...</div>"""

def printMacro():
  value = conn.execute('select * from macros where id=?;', (id,)).fetchone()
  text = value['text'] and value['text'] or ''
  args = value['args'] and value['args'] or ''
  print """Content-Type: text/html

<div class="info">
<div>%s%s</div>
<pre style="margin-top:5px">
%s
</pre>
</div>
""" % (value['name'], args, cgi.escape(text))

def printType():
  row = conn.execute("SELECT * FROM types WHERE id=?", (id,)).fetchone()
  refs = conn.execute("SELECT * FROM refs WHERE id=?", (id,))
  printTree(json.dumps(getType(row, refs, True)))

def printVariable():
  row = conn.execute("SELECT * FROM variables WHERE id=?",
    (id,)).fetchone()
  refs = conn.execute("SELECT * FROM refs WHERE id=?",(id,))
  printTree(json.dumps(getVariable(row, refs)))

def printFunction():
  row = conn.execute("SELECT * FROM functions" +
    " WHERE id=?", (id,)).fetchone()
  refs = conn.execute("SELECT * FROM refs WHERE id=?",(id,))
  printTree(json.dumps(getFunction(row, refs, True)))

def printReference():
  val = conn.execute("SELECT 'var' FROM variables WHERE id=?" +
    " UNION SELECT 'func' FROM functions WHERE id=?" +
    " UNION SELECT 't' FROM types WHERE id=?" +
    " UNION SELECT 'm' FROM macros WHERE id=?",
    (id,id,id,id)).fetchone()[0]
  return dispatch[val]()

def printTree(jsonString):
  print """Content-Type: application/json

%s
""" % (jsonString)


form = cgi.FieldStorage()

type = ''
tree = ''
virtroot = ''

if form.has_key('type'):
  type = form['type'].value

if form.has_key('tree'):
  tree = form['tree'].value

if form.has_key('virtroot'):
  virtroot = form['virtroot'].value

if form.has_key('rid'):
  id = form['rid'].value

config = ConfigParser.ConfigParser()
config.read('dxr.config')

dxrdb = os.path.join(config.get('Web', 'wwwdir'), tree, '.dxr_xref', tree  + '.sqlite');
htmlsrcdir = os.path.join('/', virtroot, tree) + '/'

conn = sqlite3.connect(dxrdb)
conn.execute('PRAGMA temp_store = MEMORY;')
conn.row_factory = sqlite3.Row

dispatch = {
    'var': printVariable,
    'func': printFunction,
    't': printType,
    'm': printMacro,
    'ref': printReference,
}
dispatch.get(type, printError)()
