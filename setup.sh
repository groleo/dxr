#! /bin/bash -e


SRCDIR=/home/mariusn/workspace/mine/
WWWDIR=/home/mariusn/public_html/

rm -rf $WWWDIR/*

CGI_BIN=$WWWDIR/cgi-bin/
mkdir $CGI_BIN

. setup-env.sh $SRCDIR
cd $SRCDIR
$CXX 1167.cpp
cd -
./dxr-index.py

cp -r www/js $WWWDIR
cp -r www/images/ $WWWDIR
cp -r www/*.css $WWWDIR

cp dxr.config $CGI_BIN
cp www/search.cgi $CGI_BIN
cp www/getinfo.cgi $CGI_BIN
