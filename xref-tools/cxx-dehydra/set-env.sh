#!/bin/sh -x
HYDRA=dehydra
DXR_JS=$DXRSRC/xref-tools/cxx-dehydra/dxr.js

HYDRASO=$DXRSRC/tools/dehydra/gcc_${HYDRA}.so
export CC="gcc -fplugin=$HYDRASO -fplugin-arg-gcc_${HYDRA}-script=$DXR_JS"
export CXX="g++ -fplugin=$HYDRASO -fplugin-arg-gcc_${HYDRA}-script=$DXR_JS"

