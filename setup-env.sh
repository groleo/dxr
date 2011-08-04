#!/usr/bin/env bash

if [ -z "$2" ]; then
  name="${BASH_SOURCE[0]}"
  if [ -z "$name" ]; then
      name=$0
  fi
  echo "Usage: . $name <dxr.config> [<treename>]"
  return 1 &>/dev/null
  exit 1
fi
DXRCONFIG="$1"
TREENAME="$2"

function get_var()
{
echo $(PYTHONPATH=$DXRSRC:$PYTHONPATH python - <<HEREDOC
import dxr
dxrconfig=dxr.load_config("$DXRCONFIG")
found=False
for treecfg in dxrconfig.trees:
	if treecfg.tree != "$1":
		continue
	else:
		found=True
		break

if found == False:
	raise BaseException("Tree[$1] not found in config[$DXRCONFIG]")
else:
	try:
		print("%s"% treecfg.$2)
	except:
		raise BaseException("Variable[$2] not found in Tree[$1]")
HEREDOC
)
}


#######################

if [ -z "$DXRSRC" ]; then
  echo -n "Setting DXRSRC variable: "
  scriptsrc=${BASH_SOURCE[0]}
  if [ "`dirname $scriptsrc`" = "." ]; then
    export DXRSRC=$(pwd)
  else
    export DXRSRC=$(dirname $(readlink -f $scriptsrc))
  fi
  echo "$DXRSRC"
else
  echo "Using DXRSRC:$DXRSRC"
fi

OBJDIR=$(get_var "$TREENAME" "objdir")

MAKE=${MAKE:-make}

echo "Finding available DXR plugins..."
tools=( $(PYTHONPATH=$DXRSRC:$PYTHONPATH python - <<HEREDOC
import dxr
dxrconfig=dxr.load_config("$DXRCONFIG")
for treecfg in dxrconfig.trees:
	if treecfg.tree == "$TREENAME":
		files = [x.__file__ for x in dxr.get_active_plugins(treecfg, "$DXRSRC")]
		break
print ' '.join([x[:x.find('/indexer.py')] for x in files])
HEREDOC
) )

if [ "$?" != "0" ]; then
  echo "Error while looking for plugins"
  return &> /dev/null || exit 0
fi

if [ "$(seq 0 $((${#tools[@]} - 1)))" = "" ]; then
  echo "No plugins"
  return &> /dev/null || exit 0
else
  echo -n "Plugins found:"
  for plugin in $(seq 0 $((${#tools[@]} - 1))); do
    echo -n " dxr.$(basename ${tools[plugin]})"
  done
  echo ""
fi

for plugin in $(seq 0 $((${#tools[@]} - 1))); do
  echo -n "Prebuilding $(basename ${tools[plugin]})... "
  if [ -e ${tools[plugin]}/Makefile ]; then 
    $MAKE -s -C ${tools[plugin]} prebuild
    if [[ $? != 0 ]]; then
      echo "Bailing!"
      return 1
    fi
  fi
  echo "done!"
done

echo -n "Preparing environment... "
for plugin in $(seq 0 $((${#tools[@]} - 1))); do
  if [ -e "${tools[plugin]}/set-env.sh" ]; then
    . "${tools[plugin]}/set-env.sh"
  fi
done
echo "done!"

echo "DXR setup complete. You can now compile your source code in this shell."

# Check for . $0 instead of ./$0
return 0 &>/dev/null
echo -e "\n\n\n\n\e[1;31mYour environment is not correctly set up.\e[0m\n"
echo "You need to run the following command instead:"
echo ". $DXRSRC/setup-env.sh"
