#!/usr/bin/python2

import sqlite3
import sys
import os
import ConfigParser
import re
import getopt
import dxr

def like_escape(val):
  return 'LIKE "%' + val.replace("\\", "\\\\").replace("_", "\\_") \
    .replace("%", "\\%") + '%" ESCAPE "\\"'

def GetLine(loc):
  # Load the parts
  parts = loc.split(':')
  name, line = parts[0], int(parts[1])
  if name not in offset_cache:
    return 'Error: Cannot find file %s' % name

  # Open up the master file
  g_master_text.seek(offset_cache[name])

  #output = ('%s/%s.html %d %s') % (g_tree, name, line, loc)
  output = ('%s %d %s\n') % (name, line, loc)
  # Show [line - 1, line, line + 1] unless we see more
  read = [line - 1, line, line + 1]
  while True:
    line=g_master_text.readline()
    readname, readline, readtext = line.split(':', 2)
    line_num = int(readline)
    if readname != name or line_num > read[-1]:
      break
    if line_num not in read:
      continue
    output += ('%s %s %s [%s]\n') % (name, readline, readline, readtext.rstrip().lstrip())
  return output

def processString(string, path=None, ext=None):
  if ext is not None and ext[0] == '.':
    ext = ext[1:]
  def printSidebarResults(name, results):
    outputtedResults = False
    for res in results:
      # Make sure we're not matching part of the scope
      colon = res[0].rfind(':')
      if colon != -1 and res[0][colon:].find(string) == -1:
        continue
      fixloc = res[1].split(':')
      if path and not re.search(path, fixloc[0]):
        continue
      if not outputtedResults:
        outputtedResults = True
        print '%s' % name
      print '%s/%s %s %s' % ( g_tree, fixloc[0], fixloc[1], res[0])

  # Print smart sidebar
  config = [
    ('types', ['tname', 'loc', 'tname']),
    ('macros', ['name', 'loc', 'name']),
    ('functions', ['qualname', 'loc', 'name']),
    ('variables', ['name', 'loc', 'name']),
  ]
  for table, cols in config:
    results = []
    #print ('<pre>SELECT %s FROM %s WHERE %s %s;</pre>' % (', '.join(cols[:-1]), table, cols[0], like_escape(string)))
    for row in conn.execute('SELECT %s FROM %s WHERE %s %s;' % (
        ', '.join(cols[:-1]), table, cols[0], like_escape(string))).fetchall():
      results.append((row[0], row[1]))
    printSidebarResults(str.capitalize(table), results)

  # Print file sidebar
  printHeader = True
  filenames = dxr.readFile(os.path.join(g_dxrconfig.dbdir, 'file_list.txt'))
  if filenames:
    for filename in filenames.split('\n'):
      # Only check in leaf name
      pattern = '/([^/]*' + string + '[^/]*\.[^\.]+)$' if not ext else '/([^/]*' + string + '[^/]*\.' + ext + ')$'
      m = re.search(pattern, filename, re.IGNORECASE)
      if m:
        if printHeader:
          print 'Files'
          printHeader = False
        filename = vrootfix + '/' + g_tree + '/' + filename
        print '%s %s' % (filename, m.group(1))


  # Text search results
  prevfile, first = None, True
  g_master_text.seek(0)
  for line in g_master_text:
    # The index file is <path>:<line>:<text>
    colon = line.find(':')
    colon2 = line.find(':', colon)
    if path and line.find(path, 0, colon) == -1: continue # Not our file
    if line.find(string, colon2 + 1) != -1:
      # We have a match!
      (filepath, linenum, text) = line.split(':', 2)
      if filepath != prevfile:
        prevfile = filepath
        first = False
        print '%s/%s/%s %s' % (vrootfix, g_tree, filepath, filepath)

      print '%s/%s/%s %s %s %s' % (vrootfix, g_tree, filepath, linenum, linenum, text)

  if first:
    print 'No files match your search parameters.'

def processType(type, path=None):
  for type in conn.execute('select * from types where tname like "' + type + '%";').fetchall():
    tname = type['tname']
    if not path or re.search(path, type['loc']):
      info = type['tkind']
      if info == 'typedef':
        typedef = conn.execute('SELECT ttypedef FROM typedefs WHERE id=?',
            (type['id'],)).fetchone()[0]
        info += ' ' + typedef
      print '%s (%s)' % (tname, info)
      print GetLine(type['loc'])

def processDerived(derived, path=None):
  components = derived.split('::')
  if len(components) > 1:
    # Find out if the entire thing is a class or not
    num = conn.execute('SELECT COUNT(*) FROM types WHERE qualname LIKE ? ' +
      'OR qualname = ?', ('%::' + derived, derived)).fetchall()[0][0]
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
  try:
    tname, id = conn.execute('SELECT qualname, id FROM types WHERE ' + 'qualname LIKE ? OR qualname=?', ('%::' + base, base)).fetchall()[0]
  except:
    print "Empty 'types' table"
    return

  print 'Results for derived:%s\n' % (tname)
  # Find everyone who inherits this class
  types = conn.execute('SELECT qualname, id, loc, inhtype FROM impl ' +
    'LEFT JOIN types ON (tderived = id) WHERE tbase=? ORDER BY inhtype DESC',
    (id,)).fetchall()

  if func is None:
    for t in types:
      direct = 'Direct' if t[3] is not None else 'Indirect'
      if not path or re.search(path, t[2]):
        print '%s (%s)' % (t[0], direct)
        print GetLine(t[2])
  else:
    typeMaps = dict([(t[1], t[0]) for t in types])
    for method in conn.execute('SELECT scopeid, qualname, loc FROM functions'+
        ' WHERE scopeid IN (' + ','.join([str(t[1]) for t in types]) + ') AND' +
        ' name = ?', (func,)).fetchall():
      tname = typeMaps[method[0]]
      mname = method[1]
      if not path or re.search(path, method[2]):
        print '%s::%s' % (tname, mname)
        print GetLine(method[2])

def processMacro(macro):
  for m in conn.execute('SELECT * FROM macros WHERE name LIKE "' +
      macro + '%";').fetchall():
    mname = m['name']
    if m['args']:
      mname += m['args']
    mtext = m['text'] and m['text'] or ''
    print '%s %s' % (mname, mtext)
    print GetLine(m['loc'])

def processFunction(func):
  for f in conn.execute('SELECT * FROM functions WHERE qualname LIKE "%' + func + '%";').fetchall():
    print '> %s' % f['qualname']
    print GetLine(f['loc'])

def processVariable(var):
  for v in conn.execute('SELECT * FROM variables WHERE name LIKE "%' +
      var + '%";').fetchall():
    qual = v['modifiers'] and v['modifiers'] or ''
    print '%s %s %s' % (qual, v['vtype'], v['name'])
    print GetLine(v['loc'])

def processWarnings(warnings, path=None):
  # Check for * which means user entered "warnings:" and wants to see all of them.
  if warnings == '*':
    warnings = ''

  num_warnings = 0
  for w in conn.execute("SELECT wloc, wmsg FROM warnings WHERE wmsg LIKE '%" +
      warnings + "%' ORDER BY wloc COLLATE loc;").fetchall():
    if not path or re.search(path, w[0]):
      print '%s' % w[1]
      print GetLine(w[0])
      num_warnings += 1
  if num_warnings == 0:
    print 'No warnings found.'

def processCallers(caller, path=None, fid=None):
  # I could handle this with a single call, but that gets a bit complicated.
  # Instead, let's first find the function that we're trying to find.
  cur = conn.cursor()
  if fid is None:
    cur.execute('SELECT * FROM functions WHERE qualname %s' %
      like_escape(caller))
    funcinfos = cur.fetchall()
    if len(funcinfos) == 0:
      print 'No results found'
      return
    elif len(funcinfos) > 1:
      for funcinfo in funcinfos:
        print ('callers=%s id=%d g_tree=%s %s at %s') % (caller, funcinfo['id'], g_tree,
          funcinfo['qualname'], funcinfo['loc'])
      #return
    fid = funcinfos[0]['id']
  # We have two cases: direct calls or we're in targets
  cur = conn.cursor()
  for info in cur.execute(
      "SELECT functions.* FROM functions " +
      "LEFT JOIN callers ON (callers.callerid = id) WHERE targetid=? " +
      "UNION SELECT functions.* FROM functions LEFT JOIN callers " +
      "ON (callers.callerid = functions.id) LEFT JOIN targets USING " +
      "(targetid) WHERE targets.id=?", (fid, fid)):
    print "fid:%s" % info

    if not path or re.search(path, info['loc']):
      print 'CALL:%s' % info['qualname']
      print GetLine(info['loc'])

  if cur.rowcount == 0:
    print 'No results found'

# This makes results a lot more fun!
def collate_loc(str1, str2):
  parts1 = str1.split(':')
  parts2 = str2.split(':')
  for i in range(1, len(parts1)):
    parts1[i] = int(parts1[i])
  for i in range(2, len(parts2)):
    parts2[i] = int(parts2[i])
  return cmp(parts1, parts2)

def usage():
  print """Usage: search.py [options]
Options:
    -h, --help
    -c callers
    -d derived
    -f function
    -m macro
    -s string
    -t type
    -v variable
    -w warning"""


def main(argv):
    global treecfg
    global conn
    global offset_cache
    global g_dxrconfig
    global g_tree
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    g_tree = 'mozilla-central'
    g_dbname = g_tree + '.sqlite'
    g_dxrconfig = dxr.load_config('./dxr.config')

    for treecfg in g_dxrconfig.trees:
      if treecfg.tree == g_tree:
        g_dxrconfig = treecfg
        break
    else:
      g_dxrconfig = treecfg

    g_dxrdb = os.path.join(treecfg.dbdir, g_dbname)

    # Load the database
    if not os.path.isfile(g_dxrdb):
      raise BaseException("No such file %s" % g_dxrdb )

    conn = sqlite3.connect(g_dxrdb)
    conn.execute('PRAGMA temp_store = MEMORY;')

    # Master text index, load it
    global g_master_text
    g_master_text = open(os.path.join(g_dxrconfig.dbdir, 'file_index.txt'), 'r')
    f = open(os.path.join(g_dxrconfig.dbdir, 'index_index.txt'), 'r')
    offset_cache = {}
    try:
      for line in f:
        l = line.split(':')
        offset_cache[l[0]] = int(l[-1])
    finally:
      f.close()

    conn.create_collation("loc", collate_loc)
    conn.row_factory = sqlite3.Row

    searches = [
      ('type', processType, False, 'Types %s', ['path']),
      ('function', processFunction, False, 'Functions %s', []),
      ('variable', processVariable, False, 'Functions %s', []),
      ('derived', processDerived, False, 'Derived from %s', ['path']),
      ('macro', processMacro, False, 'Macros %s', []),
      ('warnings', processWarnings, False, 'Warnings %s', ['path']),
      ('callers', processCallers, False, 'Callers of %s', ['path', 'id']),
      ('string', processString, True, '%s', ['path', 'ext'])
    ]
    # Get the DXR installation point from dxr.config
    if not os.path.isfile('dxr.config'):
        print('Error reading %s: No such file or directory: dxr.config'  )
        raise IOError('Error reading %s: No such file or directory: dxr.config')

    config = ConfigParser.ConfigParser()
    config.read('dxr.config')
    sys.path.append(config.get('DXR', 'dxrroot'))

    try:
        opts, args = getopt.getopt(argv, "hc:d:f:m:s:t:v:w:",["help"])
    except getopt.GetoptError:
        usage()
        sys.exit(1)
    for a, o in opts:
        if a in ('-h', '--help'):
            usage()
            sys.exit(0)
        elif a in ('-c'):
            processCallers(o)
        elif a in ('-d'):
            processDerived(o)
        elif a in ('-f'):
            processFunction(o)
        elif a in ('-m'):
            processMacro(o)
        elif a in ('-s'):
            processString(o)
        elif a in ('-t'):
            processType(o)
        elif a in ('-v'):
            processVariable(o)
        elif a in ('-w'):
            processWarnings(o)


    g_master_text.close()

if __name__ == '__main__':
    main(sys.argv[1:])
