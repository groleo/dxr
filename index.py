#!/usr/bin/env python

import dxr
import dxr.htmlbuilders
import dxr.languages
import dxr.indexer
import getopt
import sys

# At this point in time, we've already compiled the entire build, so it is time
# to collect the data. This process can be viewed as a pipeline.
# 1. Each plugin post-processes the data according to its own design. The output
#        is returned as an opaque python object. We save this object off as pickled
#        data to ease HTML development, and as an SQL database for searching.
# 2. The post-processed data is combined with the database and then sent to
#        htmlifiers to produce the output data.
# Note that either of these stages can be individually disabled.

def usage():
        print """Usage: dxr-index.py [options]
Options:
    -h, --help                Show help information.
    -a, --apend               Add TREE w/o erasing the previous ones.
    -f, --file   FILE         Use FILE as config file (default is ./dxr.config).
    -t, --trees  TREES        Index and Build only section TREE (default is all).
    -c, --create [xref|html]  Create xref or html and index (default is all).
    -d, --debug  FILE         Only generate HTML for the file.
    -y, --yappi               Run through YAPPI profiller.
"""

g_big_blob = None



def main(argv):
    configfile = './dxr.config'
    doxref = True
    dohtml = True
    debugfile = None
    use_yappi = False

    try:
        opts, args = getopt.getopt(argv, "hc:f:t:d:D:y",
                ["help", "yappi", "create=", "file=", "trees=", "debug=","deblevel="])
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for a, o in opts:
        if a in ('-f', '--file'):
            configfile = o
        elif a in ('-c', '--create'):
            if o == 'xref':
                dohtml = False
            elif o == 'html':
                doxref = False
        elif a in ('-h', '--help'):
            usage()
            sys.exit(0)
        elif a in ('-y', '--yappi'):
            use_yappi=True
        elif a in ('-t', '--trees'):
            trees = o.split(',')
            print "TREES:%s " % trees
        elif a in ('-d', '--debug'):
            debugfile = o
        elif a in ('-D', '--deblevel'):
            dxr.debugLvl = int(o)

    if use_yappi == True:
        import yappi
        yappi.start()

    dxr.indexer.parseconfig(configfile, doxref, dohtml, trees, debugfile)

    if use_yappi == True:
        stats = yappi.get_stats(yappi.SORTTYPE_TSUB)
        for i in range(0,10):
            print "%s\n%s msec %s times\n" % (stats.func_stats[i].name, stats.func_stats[i].tsub, stats.func_stats[i].ncall)
        print "thread %s(id=%d) scheduled %d times." % (stats.thread_stats[0].name, stats.thread_stats[0].id, stats.thread_stats[0].sched_count)

if __name__ == '__main__':
    main(sys.argv[1:])

