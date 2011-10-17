
# vi:set expandtab
# vi:set tabstop=4
# vi:set shiftwidth=4

from multiprocessing.pool import ThreadPool as Pool
from multiprocessing import cpu_count
import dxr
import getopt
import os
import shutil
import sqlite3
import string
import subprocess
import sys
import time

def WriteOpenSearch(name, hosturl, virtroot, wwwdir):
  try:
    fp = open(os.path.join(wwwdir, 'opensearch-' + name + '.xml'), 'w')
    try:
      fp.write("""<?xml version="1.0" encoding="UTF-8"?>
<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">
 <ShortName>%s</ShortName>
 <Description>Search DXR %s</Description>
 <Tags>mozilla dxr %s</Tags>
 <Url type="text/html"
      template="%s%s/search.cgi?tree=%s&amp;string={searchTerms}"/>
</OpenSearchDescription>""" % (name[:16], name, name, hosturl, virtroot, name))
    finally:
      fp.close()
  except IOError:
    print('Error writing opensearchfile (%s): %s' % (name, sys.exc_info()[1]))
    return None

def async_toHTML(treeconfig, srcpath, dstfile):
  """Wrapper function to allow doing this async without an instance method."""
  try:
    dxr.htmlbuilders.make_html(srcpath, dstfile, treeconfig, g_big_blob)
  except Exception, e:
    dxr.errorPrint( 'make_html failed for[%s] [%s]' % (srcpath,e) )
    import traceback
    traceback.print_exc()

def make_index(file_list, dbdir):
  # For ease of searching, we follow something akin to
  # <http://vocamus.net/dave/?p=138>. This means that we now spit out the whole
  # contents of the sourcedir into a single file... it makes grep very fast,
  # since we don't have the syscall penalties for opening and closing every
  # file.
  file_index = open(os.path.join(dbdir, "file_index.txt"), 'w')
  offset_index = open(os.path.join(dbdir, "index_index.txt"), 'w')
  for fname in file_list:
    offset_index.write('%s:%d\n' % (fname[0], file_index.tell()))
    f = open(fname[1], 'r')
    lineno = 1
    for line in f:
      if len(line.strip()) > 0:
        file_index.write(fname[0] + ":" + str(lineno) + ":" + line)
      lineno += 1
    if line[-1] != '\n':
      file_index.write('\n');
    f.close()
  offset_index.close()
  file_index.close()

def make_index_html(treecfg, dirname, fnames, htmlroot):
  genroot = os.path.relpath(dirname, htmlroot)
  if genroot.startswith('./'): genroot = genroot[2:]
  if genroot.startswith('--GENERATED--'):
    srcpath = treecfg.objdir
    genroot = genroot[len("--GENERATED--") + 1:]
  else:
    srcpath = treecfg.sourcedir
  srcpath = os.path.join(srcpath, genroot)
  of = open(os.path.join(dirname, 'index.html'), 'w')
  try:
    of.write(treecfg.getTemplateFile("dxr-header.html"))
    of.write('''<div id="maincontent" dojoType="dijit.layout.ContentPane"
      region="center"><table id="index-list">
        <tr><th></th><th>Name</th><th>Last modified</th><th>Size</th></tr>
      ''')
    of.write('<tr><td><img src="%s/images/icons/folder.png"></td>' %
      treecfg.virtroot)
    of.write('<td><a href="..">Parent directory</a></td>')
    of.write('<td></td><td>-</td></tr>')
    torm = []
    fnames.sort()
    dirs, files = [], []
    for fname in fnames:
      # Ignore hidden files
      if fname[0] == '.':
        torm.append(fname)
        continue
      fullname = os.path.join(dirname, fname)

      # Directory ?
      if os.path.isdir(fullname):
        img = 'folder.png'
        link = fname
        display = fname + '/'
        if fname == '--GENERATED--':
          stat = os.stat(treecfg.objdir) # Meh, good enough
        else:
          stat = os.stat(os.path.join(srcpath, fname))
        size = '-'
        add = dirs
      else:
        img = 'page_white.png'
        link = fname
        display = fname[:-5] # Remove .html
        stat = os.stat(os.path.join(srcpath, display))
        size = stat.st_size
        if size > 2 ** 30:
          size = str(size / 2 ** 30) + 'G'
        elif size > 2 ** 20:
          size = str(size / 2 ** 20) + 'M'
        elif size > 2 ** 10:
          size = str(size / 2 ** 10) + 'K'
        else:
          size = str(size)
        add = files
      add.append('<tr><td><img src="%s/images/icons/%s"></td>' %
        (treecfg.virtroot, img))
      add.append('<td><a href="%s">%s</a></td>' % (link, display))
      add.append('<td>%s</td><td>%s</td>' % (
        time.strftime('%Y-%b-%d %H:%m', time.gmtime(stat.st_mtime)), size))
      add.append('</tr>')
    of.write(''.join(dirs))
    of.write(''.join(files))
    of.flush()
    of.write(treecfg.getTemplateFile("dxr-footer.html"))

    for f in torm:
      fnames.remove(f)
  except:
    sys.excepthook(*sys.exc_info())
  finally:
    of.close()

def builddb(treecfg, dbdir):
  """ Post-process the build and make the SQL directory """
  global g_big_blob

  # We use this all over the place, cache it here.
  plugins = dxr.get_active_plugins(treecfg)

  # Building the database--this happens as multiple phases. In the first phase,
  # we basically collect all of the information and organizes it. In the second
  # phase, we link the data across multiple languages.
  print "Post-processing the source files..."
  g_big_blob = {}
  srcdir = treecfg.sourcedir
  objdir = treecfg.objdir
  for plugin in plugins:
    print "Build big_blob for:%s" % plugin.__name__
    g_big_blob[plugin.__name__] = plugin.post_process(srcdir, objdir)
    dxr.debugPrint(4, "g_big_blob:%s"%g_big_blob)

  # Save off the raw data blob
  dxr.store_big_blob(treecfg, g_big_blob)

  # Build the sql for later queries. This is a combination of the main language
  # schema as well as plugin-specific information. The pragmas that are
  # executed should make the sql stage go faster.
  dbname = treecfg.tree + '.sqlite'
  print "Building SQL...:%s" % dbname
  conn = sqlite3.connect(os.path.join(dbdir, dbname))
  conn.execute('PRAGMA synchronous=off')
  conn.execute('PRAGMA page_size=65536')
  # Safeguard against non-ASCII text. Let's just hope everyone uses UTF-8
  conn.text_factory = str

  # Import the schemata
  schemata = [dxr.languages.get_standard_schema()]
  for plugin in plugins:
    schemata.append(plugin.get_schema())
  dxr.debugPrint(4,'\n'.join(schemata))
  conn.executescript('\n'.join(schemata))
  conn.commit()

  # Load and run the SQL
  def sql_generator():
    for statement in dxr.languages.get_sql_statements():
      yield statement
    for plugin in plugins:
      if plugin.__name__ in g_big_blob:
        plugblob = g_big_blob[plugin.__name__]
        for statement in plugin.sqlify(plugblob):
          yield statement

  for stmt in sql_generator():
    if isinstance(stmt, tuple):
      #print "SQL:%s %s" % (stmt[0],stmt[1])
      try:
          conn.execute(stmt[0], stmt[1])
      except sqlite3.IntegrityError,e:
          dxr.errorPrint( "XXX: conn.execute fix me: %s [%s]" % (e,stmt) )
          raise
    else:
      conn.execute(stmt)
  conn.commit()
  conn.close()

def indextree(treecfg, do_xref, do_html, debugfile):
  def getOutputFiles():
    for regular in treecfg.getFileList():
      yield regular
    filelist = set()
    for plug in g_big_blob:
      dxr.debugPrint(4, "indextree blob:%s"%g_big_blob[plug]["byfile"].keys() )
      try:
        filelist.update(g_big_blob[plug]["byfile"].keys())
      except KeyError:
        print "ignoring KeyError exception"
        pass
    dxr.debugPrint(4, "jere:%s"%filelist)
    for filename in filelist:
      if filename.startswith("--GENERATED--/"):
        relpath = filename[len("--GENERATED--/"):]
        yield filename, os.path.join(treecfg.objdir, relpath)
  global g_big_blob
  print "indextree: %s %s" % (treecfg,treecfg.isdblive)

  # If we're live, we'll need to move -current to -old; we'll move it back
  # after we're done.
  if treecfg.isdblive:
    currentroot = os.path.join(treecfg.wwwdir, treecfg.tree + '-current')
    oldroot = os.path.join(treecfg.wwwdir, treecfg.tree + '-old')
    linkroot = os.path.join(treecfg.wwwdir, treecfg.tree)
    if os.path.isdir(currentroot):
      if os.path.isfile(os.path.join(currentroot, '.dxr_xref', '.success')):
        # Move current -> old, change link to old
        try:
          shutil.rmtree(oldroot)
        except OSError:
          pass
        try:
          shutil.move(currentroot, oldroot)
          os.unlink(linkroot)
          os.symlink(oldroot, linkroot)
        except OSError:
          pass
      else:
        # This current directory is bad, move it away
        shutil.rmtree(currentroot)

  # dxr xref files (index + sqlitedb) go in wwwdir/treename-current/.dxr_xref
  # and we'll symlink it to wwwdir/treename later
  htmlroot = os.path.join(treecfg.wwwdir, treecfg.tree + '-current')
  dbdir = os.path.join(htmlroot, '.dxr_xref')
  os.makedirs(dbdir, 0755)
  dbname = treecfg.tree + '.sqlite'

  retcode = 0
  if do_xref:
    dxr.debugPrint(2,"dbdir:%s"%dbdir)
    builddb(treecfg, dbdir)
    if treecfg.isdblive:
      f = open(os.path.join(dbdir, '.success'), 'w')
      f.close()
  elif treecfg.isdblive:
    # If the database is live, we need to copy database info from the old
    # version of the code
    oldhtml = os.path.join(treecfg.wwwdir, treecfg.tree + '-old')
    olddbdir = os.path.join(oldhtml, '.dxr_xref')
    shutil.rmtree(dbdir)
    shutil.copytree(olddbdir, dbdir)

  # Build static html
  if do_html:
    if not do_xref:
      g_big_blob = dxr.load_big_blob(treecfg)
    # Do we need to do file pivoting?
    for plugin in dxr.get_active_plugins(treecfg):
      dxr.debugPrint(4,"blob3:%s"%g_big_blob[plugin.__name__])
      if plugin.__name__ in g_big_blob:
        plugin.pre_html_process(treecfg, g_big_blob[plugin.__name__])
    dxr.htmlbuilders.build_htmlifier_map(dxr.get_active_plugins(treecfg))
    treecfg.database = os.path.join(dbdir, dbname)

    #n = cpu_count()
    n=1
    p = Pool(processes=n)

    print 'Building HTML files for %s...' % treecfg.tree

    debug = (debugfile is not None)

    index_list = open(os.path.join(dbdir, "file_list.txt"), 'w')
    file_list = []


    for f in getOutputFiles():
      # In debug mode, we only care about some files
      if debugfile is not None and f[0] != debugfile: continue

      index_list.write(f[0] + '\n')
      cpypath = os.path.join(htmlroot, f[0])
      srcpath = f[1]
      file_list.append(f)

      # Make output directory
      cpydir = os.path.dirname(cpypath)
      if not os.path.isdir(cpydir):
        os.makedirs(cpydir)

      p.apply_async(async_toHTML, [treecfg, srcpath, cpypath + ".html"])

    p.apply_async(make_index, [file_list, dbdir])

    index_list.close()
    p.close()
    p.join()

    # Generate index.html files
    # XXX: This wants to be parallelized. However, I seem to run into problems
    # if it isn't.
    def genhtml(treecfg, dirname, fnames):
      make_index_html(treecfg, dirname, fnames, htmlroot)
    os.path.walk(htmlroot, genhtml, treecfg)

  # If the database is live, we need to switch the live to the new version
  if treecfg.isdblive:
    try:
      os.unlink(linkroot)
      shutil.rmtree(oldroot)
    except OSError:
      pass
    os.symlink(currentroot, linkroot)

def pre_indexing(dxrconfig,tree):
    if not os.path.isdir( dxrconfig.wwwdir ):
        os.mkdir( dxrconfig.wwwdir )

    shutil.copy ('Doxyfile', tree.sourcedir )
    oldpwd=os.getcwd()
    os.chdir ( tree.sourcedir )

    p=subprocess.Popen('doxygen', stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    dox_log = open(os.path.join(oldpwd,"doxygen.log"), "w", 0) 
    dox_log.write( p.stdout.read() )
    dox_log.close()
    p.wait()

    os.remove( 'Doxyfile' )

    if os.path.isdir( tree.objdir ):
        shutil.rmtree ( tree.objdir )
    shutil.copytree( 'xml/', tree.objdir )
    shutil.rmtree( 'xml' )
    os.chdir( oldpwd )

#def post_indexing(dxrconfig):
#    shutil.copy( 'www/js', dxrconfig.wwwdir)
#    shutil.copy( 'www/images/', dxrconfig.wwwdir)
#    shutil.copy( 'www/*.css', dxrconfig.wwwdir)
#
#
#    CGI_BIN=${WWWDIR}/cgi-bin/
#    if [ ! -e "${CGI_BIN}" ]; then
#        mkdir "${CGI_BIN}"
#    fi
#    cp dxr.config $CGI_BIN
#    cp www/*.cgi $CGI_BIN

def parseconfig(filename, do_xref, do_html, trees, debugfile):
  # Build the contents of an html <select> and open search links
  # for all tree encountered.
  # Note: id for CSS, name for form "get" value in query
  browsetree = ''
  options = '<select id="tree" name="tree">'
  opensearch = ''

  print "Using config: %s" % filename
  if trees == None:
    dxr.debugPrint(2, "tree is None: Indexing all trees")
  dxrconfig = dxr.load_config(filename)

  tree_list=open(os.path.join(dxrconfig.wwwdir,"tree_list"),"r")
  indexed_trees=tree_list.read().splitlines()

  for treecfg in dxrconfig.trees:
      if trees != None:
        if treecfg.tree in trees:
            # if tree is set, only index/build this section if it matches
            pre_indexing(dxrconfig,treecfg)
            indextree(treecfg, do_xref, do_html, debugfile)
            indexed_trees.append(treecfg.tree)

  for treecfg in dxrconfig.trees:
    if treecfg.tree in indexed_trees:
        treecfg.virtroot = dxrconfig.virtroot
        browsetree += '<a href="%s">%s</a><br/>' % (treecfg.tree, treecfg.tree)
        options    += '<option value="' + treecfg.tree + '">' + treecfg.tree + '</option>'
        opensearch += '<link rel="search" href="opensearch-' + treecfg.tree + '.xml" type="application/opensearchdescription+xml" '
        opensearch += 'title="' + treecfg.tree + '" />\n'
        WriteOpenSearch(treecfg.tree, treecfg.hosturl, treecfg.virtroot, treecfg.wwwdir)

  # Generate index page with drop-down + opensearch links for all trees
  indexhtml = dxrconfig.getTemplateFile('dxr-index-template.html')
  indexhtml = string.Template(indexhtml).safe_substitute(**treecfg.__dict__)
  indexhtml = indexhtml.replace('$BROWSETREE', browsetree)

  if len(dxrconfig.trees) > 1:
    options += '</select>'
  else:
    options = '<input type="hidden" id="tree" value="' + treecfg.tree + '">'

  indexhtml = indexhtml.replace('$OPTIONS', options)
  indexhtml = indexhtml.replace('$OPENSEARCH', opensearch)
  index = open(os.path.join(dxrconfig.wwwdir, 'index.html'), 'w')
  index.write(indexhtml)
  index.close()

