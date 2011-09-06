#!/usr/bin/env bash

if [ $# -lt 1 ]; then
    echo "Usage: run-test.sh test_directory"
    exit 1
fi

# Bring us to this directory.
cd $(dirname $(readlink -f $0))

dir=$(readlink -f $1)
testname=$(basename $dir)

echo "Running test $testname"

eval $(python <<HEREDOC
import ConfigParser
f = ConfigParser.ConfigParser()
f.read('tests.ini')
for opt in f.options('$testname'):
  print '%s=%s' % (opt, repr(f.get('$testname', opt)))
HEREDOC
)

# Anything that fails after this point is a problem.
set -e

# Environment setup
echo "Setting up the environment:"
ENVBEFORE="`env`"
. ../setup-env.sh $dxrconfig $testname
ENVAFTER="`env`"

echo "Environment variables exported by setup-env.sh:"
diff <(echo "$ENVBEFORE") <(echo "$ENVAFTER") | sed -n 's/^> /  /gp'
echo

# Clean up any failing runs and then build everything
echo -e "\n\nBuilding:"
make -C $dir clean
make -C $dir

echo -e "\n\nIndexing:"
../dxr-index.py -f $dxrconfig -c xref

echo -e "\n\nChecking:"
python $verifier $testname
