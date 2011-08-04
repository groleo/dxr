#!/usr/bin/env python2.6

import cgitb; cgitb.enable()
import cgi
import sqlite3
import sys
import os
import ConfigParser
import re
import subprocess

# Get the DXR installation point from dxr.config
if not os.path.exists('dxr.config'):
  print('Error reading %s: No such file or directory: dxr.config'  )
  raise IOError('Error reading %s: No such file or directory: dxr.config')

config = ConfigParser.ConfigParser()
config.read('dxr.config')
sys.path.append(config.get('DXR', 'dxrroot'))
import dxr

def like_escape(val):
  return 'LIKE "%' + val.replace("\\", "\\\\").replace("_", "\\_") \
    .replace("%", "\\%") + '%" ESCAPE "\\"'

def split_type(val):
    parts = val.split('::')
    # check for 'type' vs. 'type::member' vs. 'namespace::type::member' or 'namespace::namespace2::type::member'
    n = None
    t = None
    m = None

    if len(parts) == 1:
        # just a single string, stuff it in type
        t = val
    elif len(parts) == 2:
        t = parts[0]
        m = parts[1]
    else:
        m = parts[-1]
        t = parts[-2]
        # use the rest as namespace
        n = '::'.join(parts[0:-2])

    return n, t, m

def GetLine(loc):
    parts = loc.split(':')
    file = dxr.readFile(os.path.join(dxrconfig.wwwdir, tree, parts[0]))
    line = int(parts[1])
    if file:
        result  = '<div class="searchfile"><a href="%s/%s">%s</a></div><ul class="searchresults">' % (tree, parts[0] + '.html#l' + parts[1], loc)
        lines = file.split('\n')
        for i in [-1, 0, 1]:
            num = int(parts[1]) + i
            result += '<li class="searchresult"><a href="%s/%s">%s:</a>&nbsp;&nbsp;%s</li>' % (tree, parts[0] + '.html#l' + str(num), num, cgi.escape(lines[line+i-1]))

        result += '</ul>'
        return result
    else:
        return ''

def processString(string):
  vrootfix = dxrconfig.virtroot
  if vrootfix == '/':
    vrootfix = ''
  def printSidebarResults(name, results):
    if len(results) == 0:
      return
    print '<div class="bubble"><span class="title">%s</span><ul>' % name
    for res in results:
      # Make sure we're not matching part of the scope
      colon = res[0].rfind(':')
      if colon != -1 and res[0][colon:].find(string) == -1:
        continue
      fixloc = res[1].split(':')
      if path and not re.search(path, fixloc[0]):
        continue
      print '<li><a href="%s/%s/%s.html#l%s">%s</a></li>' % \
        (vrootfix, tree, fixloc[0], fixloc[1], res[0])
    print '</ul></div>'

  # Print smart sidebar
  print '<div id="sidebar">'
  config = [
    ('types', ['tname', 'tloc', 'tname']),
    ('macros', ['macroname', 'macroloc', 'macroname']),
    ('functions', ['fqualname', 'floc', 'fname']),
    ('variables', ['vname', 'vloc', 'vname']),
  ]
  for table, cols in config:
    results = []
    for row in conn.execute('SELECT %s FROM %s WHERE %s %s;' % (
        ', '.join(cols[:-1]), table, cols[0], like_escape(string))).fetchall():
      results.append((row[0], row[1]))
    printSidebarResults(str.capitalize(table), results)

  # Print file sidebar
  printHeader = True
  filenames = dxr.readFile(os.path.join(dxrconfig.wwwdir, tree, '.dxr_xref', 'file_list.txt'))
  if filenames:
    for filename in filenames.split('\n'):
      # Only check in leaf name
      pattern = '/([^/]*' + string + '[^/]*\.[^\.]+)$' if not ext else '/([^/]*' + string + '[^/]*\.' + ext + ')$'
      m = re.search(pattern, filename, re.IGNORECASE)
      if m:
        if printHeader:
          print '<div class=bubble><span class="title">Files</span><ul>'
          printHeader = False
        filename = filename.replace(dxrconfig.wwwdir, vrootfix)
        print '<li><a href="%s.html">%s</a></li>' % (filename, m.group(1))
    if not printHeader:
      print "</ul></div>"

  print '</div><div id="content">'

  # Check for strings like 'foo::bar'
  halves = string.split('::')
  if len(halves) == 2:
    count = processMember(halves[1], halves[0], True)
    if count > 0:
      # we printed results, so don't bother with a text search
      return

  # Text search results
  prevfile, first = None, True
  file_index = os.path.join(dxrconfig.wwwdir, tree, '.dxr_xref', 'file_index.txt')
  if not os.path.exists(file_index):
    raise BaseException("No such file %s" % file_index)

  index_file = open(file_index)
  for line in index_file:
    # The index file is <path>:<line>:<text>
    colon = line.find(':')
    colon2 = line.find(':', colon)
    if path and line.find(path, 0, colon) == -1: continue # Not our file
    if line.find(string, colon2 + 1) != -1:
      # We have a match!
      (filepath, linenum, text) = line.split(':', 2)
      text = cgi.escape(text)
      text = re.sub(r'(?i)(' + string + ')', '<b>\\1</b>', text)
      if filepath != prevfile:
        prevfile = filepath
        if not first:
          print "</ul>"
        first = False
        print '<div class="searchfile"><a href="%s/%s/%s.html">%s</a></div><ul class="searchresults">' % (vrootfix, tree, filepath, filepath)

      print '<li class="searchresult"><a href="%s/%s/%s.html#l%s">%s:</a>&nbsp;&nbsp;%s</li>' % (vrootfix, tree, filepath, linenum, linenum, text)

  if first:
    print '<p>No files match your search parameters.</p>'
  else:
    print '</ul>'

def processType(type, path=None):
  for type in conn.execute('select * from types where tname like "' + type + '%";').fetchall():
    tname = cgi.escape(type['tname'])
    if not path or re.search(path, type['tloc']):
      info = type['tkind']
      if info == 'typedef':
        typedef = conn.execute('SELECT ttypedef FROM typedefs WHERE tid=?',
            (type['tid'],)).fetchone()[0]
        info += ' ' + cgi.escape(typedef)
      print '<h3>%s (%s)</h3>' % (tname, info)
      print GetLine(type['tloc'])

def processDerived(derived):
  components = derived.split('::')
  if len(components) > 1:
    # Find out if the entire thing is a class or not
    num = conn.execute('SELECT COUNT(*) FROM types WHERE tqualname LIKE ? ' +
      'OR tqualname = ?', ('%::' + derived, derived)).fetchall()[0][0]
    if num == 0:
      base = '::'.join(components[:-1])
      func = components[-1]
    else:
      base = derived
      func = None
  else:
    base = derived
    func = None

  # Find the class in the first place
  tname, tid = conn.execute('SELECT tqualname, tid FROM types WHERE ' +
    'tqualname LIKE ? OR tqualname=?', ('%::' + base, base)).fetchall()[0]

  print '<h2>Results for %s:</h2>\n' % (cgi.escape(tname))
  # Find everyone who inherits this class
  types = conn.execute('SELECT tqualname, tid, tloc, inhtype FROM impl ' +
    'LEFT JOIN types ON (tderived = tid) WHERE tbase=? ORDER BY inhtype DESC',
    (tid,)).fetchall()

  if func is None:
    for t in types:
      direct = 'Direct' if t[3] is not None else 'Indirect'
      if not path or re.search(path, t[2]):
        print '<h3>%s (%s)</h3>' % (cgi.escape(t[0]), direct)
        print GetLine(t[2])
  else:
    typeMaps = dict([(t[1], t[0]) for t in types])
    for method in conn.execute('SELECT scopeid, fqualname, floc FROM functions'+
        ' WHERE scopeid IN (' + ','.join([str(t[1]) for t in types]) + ') AND' +
        ' fname = ?', (func,)).fetchall():
      tname = cgi.escape(typeMaps[method[0]])
      mname = cgi.escape(method[1])
      if not path or re.search(path, method[2]):
        print '<h3>%s::%s</h3>' % (tname, mname)
        print GetLine(method[2])

def processMacro(macro):
  for m in conn.execute('SELECT * FROM macros WHERE macroname LIKE "' +
      macro + '%";').fetchall():
    mname = m['macroname']
    if m['macroargs']:
      mname += m['macroargs']
    mtext = m['macrotext'] and m['macrotext'] or ''
    print '<h3>%s</h3><pre>%s</pre>' % (cgi.escape(mname), cgi.escape(mtext))
    print GetLine(m['macroloc'])

def processFunction(func):
  for f in conn.execute('SELECT * FROM functions WHERE fqualname LIKE "%' +
      func + '%";').fetchall():
    print '<h3>%s</h3>' % cgi.escape(f['fqualname'])
    print GetLine(f['floc'])

def processVariable(var):
  for v in conn.execute('SELECT * FROM variables WHERE vname LIKE "%' +
      var + '%";').fetchall():
    qual = v['modifiers'] and v['modifiers'] or ''
    print '<h3>%s %s %s</h3>' % (cgi.escape(qual), cgi.escape(v['vtype']),
      cgi.escape(v['vname']))
    print GetLine(v['vloc'])

def processWarnings(warnings, path=None):
  # Check for * which means user entered "warnings:" and wants to see all of them.
  if warnings == '*':
    warnings = ''

  for w in conn.execute("SELECT wloc, wmsg FROM warnings WHERE wmsg LIKE '%" +
      warnings + "%' ORDER BY wloc COLLATE loc;").fetchall():
    if not path or re.search(path, w[0]):
      print '<h3>%s</h3>' % w[1]
      print GetLine(w[0])

def processCallers(caller, path=None, funcid=None):
  # I could handle this with a single call, but that gets a bit complicated.
  # Instead, let's first find the function that we're trying to find.
  cur = conn.cursor()
  if funcid is None:
    cur.execute('SELECT * FROM functions WHERE fqualname %s' %
      like_escape(caller))
    funcinfos = cur.fetchall()
    if len(funcinfos) == 0:
      print '<h2>No results found</h2>'
      return
    elif len(funcinfos) > 1:
      print '<h3>Ambiguous function:</h3><ul>'
      for funcinfo in funcinfos:
        print ('<li><a href="search.cgi?callers=%s&funcid=%d&tree=%s">%s</a>' +
          ' at %s</li>') % (caller, funcinfo['funcid'], tree,
          funcinfo['fqualname'], funcinfo['floc'])
      print '</ul>'
      return
    funcid = funcinfos[0]['funcid']
  # We have two cases: direct calls or we're in targets
  cur = conn.cursor()
  for info in cur.execute("SELECT functions.* FROM functions " +
      "LEFT JOIN callers ON (callers.callerid = funcid) WHERE targetid=? " +
      "UNION SELECT functions.* FROM functions LEFT JOIN callers " +
      "ON (callers.callerid = functions.funcid) LEFT JOIN targets USING " +
      "(targetid) WHERE targets.funcid=?", (funcid, funcid)):
    if not path or re.search(path, info['floc']):
      print '<h3>%s</h3>' % info['fqualname']
      print GetLine(info['floc'])
  if cur.rowcount == 0:
    print '<h3>No results found</h3>'

# XXX: enable auto-flush on write - http://mail.python.org/pipermail/python-list/2008-June/668523.html
# reopen stdout file descriptor with write mode
# and 0 as the buffer size (unbuffered)
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

form = cgi.FieldStorage()

string = None
path = None
ext = None
type = ''
derived = ''
member = ''
tree = '' #mozilla-central' # just a default for now
macro = ''
callers = ''
callees = ''
warnings = ''

if form.has_key('string'):
    string = form['string'].value

if form.has_key('path'):
    path = form['path'].value

if form.has_key('ext'):
    ext = form['ext'].value
    # remove . if present
    ext = ext.replace('.', '')

if form.has_key('type'):
    type = form['type'].value

if form.has_key('derived'):
    derived = form['derived'].value

if form.has_key('member'):
    member = form['member'].value

if form.has_key('tree'):
    tree = form['tree'].value
if tree == '':
  raise BaseException("tree variable is void")

if form.has_key('macro'):
    macro = form['macro'].value

if form.has_key('callers'):
    callers = form['callers'].value

if form.has_key('callees'):
    callees = form['callees'].value

if form.has_key('warnings'):
    warnings = form['warnings'].value

htmldir = os.path.join('./', tree)

# TODO: kill off hard coded path
dxrconfig = dxr.load_config('./dxr.config')
for treecfg in dxrconfig.trees:
  if treecfg.tree == tree:
    dxrconfig = treecfg
    break

#wwwdir = config.get('Web', 'wwwdir')

dbname = tree + '.sqlite'
dxrdb = os.path.join(dxrconfig.wwwdir, tree, '.dxr_xref', dbname)
if not os.path.exists(dxrdb):
  raise BaseException("No such file %s" % dxrdb )

conn = sqlite3.connect(dxrdb)
def collate_loc(str1, str2):
  parts1 = str1.split(':')
  parts2 = str2.split(':')
  for i in range(1, len(parts1)):
    parts1[i] = int(parts1[i])
  for i in range(2, len(parts2)):
    parts2[i] = int(parts2[i])
  return cmp(parts1, parts2)
conn.create_collation("loc", collate_loc)

conn.execute('PRAGMA temp_store = MEMORY;')

if string:
  titlestr = string
else:
  titlestr = ''
print 'Content-Type: text/html\n'
print dxrconfig.getTemplateFile("dxr-search-header.html") % cgi.escape(titlestr)

# XXX... plugins!
searches = [
  ('type', processType, False, 'Types %s', ['path']),
  ('function', processFunction, False, 'Functions %s', []),
  ('variable', processVariable, False, 'Functions %s', []),
  ('derived', processDerived, False, 'Derived from %s', ['path']),
  ('macro', processMacro, False, 'Macros %s', []),
  ('warnings', processWarnings, False, 'Warnings %s', ['path']),
  ('callers', processCallers, False, 'Callers of %s', ['path', 'funcid']),
  ('string', processString, True, '%s', ['path', 'ext'])
]
for param, dispatch, hasSidebar, titlestr, optargs in searches:
  if param in form:
    titlestr = cgi.escape(titlestr % form[param])
    print dxrconfig.getTemplateFile("dxr-search-header.html") % titlestr
    if not hasSidebar:
      print '<div id="content">'
    kwargs = dict((k,form[k]) for k in optargs if k in form)
    dispatch(form[param], **kwargs)
    break
else:
    print '<div id="content">'
    if type:
        if member:
            processMember(member, type, True)
        else:
            processType(type)
    elif derived:
        processDerived(derived)
    elif member:
        processMember(member, type, True)
    elif macro:
        processMacro(macro)
    elif callers:
        processCallers(callers)
    elif callees:
        processCallees(callees)
    elif warnings:
      processWarnings(warnings)
print dxrconfig.getTemplateFile("dxr-search-footer.html")

