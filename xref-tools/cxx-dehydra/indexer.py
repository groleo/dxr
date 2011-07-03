import csv
import dxr.plugins
import os

def can_use(treecfg):
  # We need to have clang and llvm-config in the path
  return True

def make_blob():
  blob = {}
  return blob

# returns a blob
def post_process(srcdir, objdir):
  print "Post processing SQL files"
  blob = make_blob()
  return blob


schema = dxr.plugins.Schema({
  # Scope definitions: a scope is anything that is both interesting (i.e., not
  # a namespace) and can contain other objects. The IDs for this scope should be
  # IDs in other tables as well; the table its in can disambiguate which type of
  # scope you're looking at.
  "scopes": [
    ("scopeid", "INTEGER", False),   # An ID for this scope
    ("sname", "VARCHAR(256)", True), # Name of the scope
    ("sloc", "_location", True),     # Location of the canonical decl
    ("_key", "scopeid")
  ],
  # Type definitions: anything that defines a type per the relevant specs.
  "types": [
    ("tid", "INTEGER", False),            # Unique ID for the type
    ("scopeid", "INTEGER", False),        # Scope this type is defined in
    ("tname", "VARCHAR(256)", False),     # Simple name of the type
    ("tqualname", "VARCHAR(256)", False), # Fully-qualified name of the type
    ("tloc", "_location", False),         # Location of canonical decl
    ("tkind", "VARCHAR(32)", True),       # Kind of type (e.g., class, union)
    ("_key", "tid")
  ],
  # Inheritance relations: note that we store the full transitive closure in
  # this table, so if A extends B and B extends C, we'd have (A, C) stored in
  # the table as well; this is necessary to make SQL queries work, since there's
  # no "transitive closure lookup expression".
  "impl": [
    ("tbase", "INTEGER", False),      # tid of base type
    ("tderived", "INTEGER", False),   # tid of derived type
    ("inhtype", "VARCHAR(32)", True), # Type of inheritance; NULL is indirect
    ("_key", "tbase", "tderived")
  ],
  # Functions: functions, methods, constructors, operator overloads, etc.
  "functions": [
    ("funcid", "INTEGER", False),         # Function ID (also in scopes)
    ("scopeid", "INTEGER", False),        # Scope defined in
    ("fname", "VARCHAR(256)", False),     # Short name (no args)
    ("flongname", "VARCHAR(512)", False), # Fully qualified name, including args
    ("floc", "_location", True),          # Location of definition
    ("modifiers", "VARCHAR(256)", True),  # Modifiers (e.g., private)
    ("_key", "funcid")
  ],
  # Variables: class, global, local, enum constants; they're all in here
  # Variables are of course not scopes, but for ease of use, they use IDs from
  # the same namespace, no scope will have the same ID as a variable and v.v.
  "variables": [
    ("varid", "INTEGER", False),         # Variable ID
    ("scopeid", "INTEGER", False),       # Scope defined in
    ("vname", "VARCHAR(256)", False),    # Short name
    ("vloc", "_location", True),         # Location of definition
    ("vtype", "VARCHAR(256)", True),     # Full type (including pointer stuff)
    ("modifiers", "VARCHAR(256)", True), # Modifiers for the declaration
    ("_key", "varid")
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
  }
})
get_schema = dxr.plugins.make_get_schema_func(schema)

def sqlify(blob):
  return schema.get_data_sql(blob)

htmlifier = {}
def get_htmlifiers():
  return htmlifier

__all__ = dxr.plugins.required_exports()
