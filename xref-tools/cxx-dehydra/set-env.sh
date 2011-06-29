#!/bin/sh -x

export CC="gcc -fplugin=$DXRSRC/xref-tools/cxx-dehydra/gcc_dehydra.so -fplugin-arg-gcc_dehydra-script=$DXRSRC/xref-tools/cxx-dehydra/dxr.js"
export CXX="g++ -fplugin=$DXRSRC/xref-tools/cxx-dehydra/gcc_dehydra.so -fplugin-arg-gcc_dehydra-script=$DXRSRC/xref-tools/cxx-dehydra/dxr.js"

