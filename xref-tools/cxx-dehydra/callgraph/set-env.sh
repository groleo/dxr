#!/bin/sh -x
HYDRA=treehydra
DXR_JS=$DXRSRC/xref-tools/cxx-dehydra/callgraph/callgraph_static.js

HYDRASO=$DXRSRC/tools/dehydra/gcc_${HYDRA}.so
export CC="gcc -fplugin=$HYDRASO -fplugin-arg-gcc_${HYDRA}-script=$DXR_JS"
export CXX="g++ -fplugin=$HYDRASO -fplugin-arg-gcc_${HYDRA}-script=$DXR_JS"

