def name():
  return "cxx-dehydra"

def can_use(treecfg):
  # We need to have clang and llvm-config in the path
  return True
