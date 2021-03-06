import marshal as cPickle
from ConfigParser import ConfigParser
from hashlib import sha1
import dxr.languages
import imp
import os, sys
import string
import pprint

g_pp = pprint.PrettyPrinter(depth=6)
debugLvl = None

def debugPrint(lvl,args):
    if lvl <= debugLvl:
        print "D:", args

def debugPPrint(lvl,args):
    if lvl <= debugLvl:
        g_pp.pprint( args )

def errorPrint(args):
    print "E:", args

def warningPrint(args):
    print "W:", args

###################
# Plugin handling #
###################

all_plugins = None
def get_active_plugins(tree=None, dxrsrc=None):
  """ Return all plugins that are used by the tree.
      If tree is None, then all usable plugins are returned. """
  global all_plugins
  if all_plugins is None:
    if dxrsrc is None and tree is not None:
      dxrsrc = tree.dxrroot
    all_plugins = load_plugins(dxrsrc)

  if tree is not None and 'plugins' in tree.__dict__:
    plugins = [x.strip() for x in tree.plugins.split(',')]
    pluglist = []
    for name in plugins:
      for plugin in all_plugins:
        if plugin.__name__ == name:
          pluglist.append(plugin)
          break
      else:
        print "Warning: plugin %s not found" % name
    return pluglist
  def plugin_filter(module):
    return module.can_use(tree)
  return filter(plugin_filter, all_plugins)

def load_plugins(dxrsrc=None):
  print "dxrsrc:%s" % dxrsrc
  if dxrsrc is None:
    dxrsrc = os.path.realpath(os.path.dirname(sys.argv[0]))
  print "dxrsrc:%s" % dxrsrc
  dirs = os.listdir(os.path.join(dxrsrc, 'xref-tools'))
  all_plugins = []
  for dirname in dirs:
    fullname = os.path.join(dxrsrc, 'xref-tools', dirname)
    try:
      m = imp.find_module('indexer', [fullname])
      module = imp.load_module('dxr.' + dirname, m[0], m[1], m[2])
      all_plugins.append(module)
      print "Loaded plugin:%s" % module
    except:
      print "Unable to load plugin %s" % dirname
      print sys.exc_info()
      raise
  return all_plugins

def store_big_blob(tree, blob):
  print "Store big_blob"
  htmlroot = os.path.join(tree.wwwdir, tree.tree + '-current')
  dbdir = os.path.join(htmlroot, '.dxr_xref')
  # Commented out code: serialize byfile stuff independently, to avoid memory
  # wastage on very very large systems.
  #byfile = {}
  #filelist = set()
  #for plug in blob:
  #  try:
  #    byfile[plug] = blob[plug].pop("byfile")
  #    filelist.update(byfile[plug].keys())
  #  except KeyError:
  #    pass
  f = open(os.path.join(dbdir, 'index_blob.dat'), 'wb')
  try:
    cPickle.dump((blob, dxr.languages.language_data), f, 2)
  finally:
    f.close()
  #for fname in filelist:
  #  datname = 'fileindex_%s.dat' % (sha1(fname).hexdigest())
  #  f = open(os.path.join(dbdir, datname), 'wb')
  #  fdir = dict((p, byfile[p][fname]) for p in byfile if fname in byfile[p])
  #  try:
  #    cPickle.dump(fdir, f, 2)
  #  finally:
  #    f.close()
  #for plug in byfile:
  #  blob[plug]["byfile"] = byfile[plug]

def load_big_blob(tree):
  print "Load big_blob"
  htmlroot = os.path.join(tree.wwwdir, tree.tree + '-current')
  dbdir = os.path.join(htmlroot, '.dxr_xref')
  f = open(os.path.join(dbdir, 'index_blob.dat'), 'rb')
  try:
    big_blob, dxr.languages.language_data = cPickle.load(f)
    return big_blob
  finally:
    f.close()

class DxrConfig(object):
  def __init__(self, config, tree=None):
    self._tree = tree
    self._loadOptions(config, 'DXR')
    self.templates = os.path.abspath(config.get('DXR', 'templates'))
    if config.has_option('DXR', 'dxrroot'):
      self.dxrroot = os.path.abspath(config.get('DXR', 'dxrroot'))
    else:
      self.dxrroot = None

    self.wwwdir = os.path.abspath(config.get('Web', 'wwwdir'))
    self.virtroot=config.get('Web','virtroot')
    if self.virtroot != '' and not self.virtroot.endswith('/'):
      self.virtroot += '/'
    self.hosturl = config.get('Web', 'hosturl')
    if not self.hosturl.endswith('/'):
      self.hosturl += '/'

    if tree is None:
      self.trees = []
      for section in config.sections():
        if section == 'DXR' \
        or section == 'Web' :
          continue
        self.trees.append(DxrConfig(config, section))

      for tree in self.trees:
          tree.dbdir = os.path.join(self.wwwdir, tree.tree + '-current', '.dxr_xref')
    else:
      self.tree = self._tree
      self._loadOptions(config, tree)
      if 'dbdir' not in self.__dict__:
        # Build the dbdir from [wwwdir]/tree
        self.dbdir = os.path.join(self.wwwdir, tree + '-current', '.dxr_xref')
      self.isdblive = self.dbdir.startswith(self.wwwdir)

  def _loadOptions(self, config, section):
      for opt in config.options(section):
        self.__dict__[opt] = config.get(section, opt)
        if opt.endswith('dir'):
          self.__dict__[opt] = os.path.abspath(self.__dict__[opt])

  def getOption(self, key):
    return self.__dict__[key]

  def getTemplateFile(self, name):
    tmpl = readFile(os.path.join(self.templates, name))
    tmpl = string.Template(tmpl).safe_substitute(**self.__dict__)
    return tmpl

  def getFileList(self):
    """ Returns an iterator of (relative, absolute) paths for the tree. """
    exclusions = self.__dict__.get("exclusions", ".hg\n.git\nCVS\n.svn")
    exclusions = exclusions.split()
    for root, dirs, files in os.walk(self.sourcedir, True):
      # Get the relative path to the source dir
      relpath = os.path.relpath(root, self.sourcedir)
      if relpath == '.':
        relpath = ''
      for f in files:
        # XXX: cxx-clang hack
        if f.endswith(".csv"): continue
        relfname = os.path.join(relpath, f)
        if any([f == ex for ex in exclusions]):
          continue
        yield (relfname, os.path.join(self.sourcedir, relfname))
      for ex in exclusions:
        if ex in dirs:
          dirs.remove(ex)

def readFile(filename):
  try:
    fp = open(filename,"r")
    try:
      return fp.read()
    finally:
      fp.close()
  except IOError:
    print('Error reading %s: %s' % (filename, sys.exc_info()[1]))
    raise IOError('Error reading %s: %s' % (filename, sys.exc_info()[1]))
    return None

def load_config(path):
  if not os.path.isfile(path):
    print('Error reading %s: Not a config file' % path)
    raise IOError('Error reading %s: Not a config file' % path)
    return None
  config = ConfigParser()
  config.read(path)

  return DxrConfig(config)

__all__ = ['get_active_plugins', 'store_big_blob', 'load_big_blob',
  'load_config', 'readFile']
