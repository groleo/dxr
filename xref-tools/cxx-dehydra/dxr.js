/* Notes:
 *  ------
 * process_function()
 * - gives a member's definition (mdef) IF the normalized loc is rooted in something other than /dist/include
 *
 * process_type() (actually, print_members() called via process_type)
 * - gives a member's declaration (mdecl) IF loc is normalized and not rooted in /dist/include
 * - NOTE: process_function/print_members will give the same loc if the member is defined/declared in the same place, for example:
 *  nsAccessible.h 138: static PRUint32 State(nsIAccessible *aAcc) { PRUint32 state = 0; if (aAcc) aAcc->GetFinalState(&state, nsnull); return state; }
 *  nsAccessible process_function() mtname=nsAccessible mname=State(nsIAccessible*) loc=/home/dave/mozilla-central/src/accessible/src/base/nsAccessible.h:138
 *  nsAccessible print_members() mtname=nsAccessible mname=State(nsIAccessible*) loc=/home/dave/mozilla-central/src/accessible/src/base/nsAccessible.h:138
 *
 * - NOTE: data members will have nothing in process_function, and only appear in print_members(), for example:
 *
 *  253: PRInt32 mAccChildCount; // protected data member
 *  nsAccessible print_members() mtname=nsAccessible mname=mAccChildCount loc=/home/dave/mozilla-central/src/accessible/src/base/nsAccessible.h:253
 */

// Change this to your src root
// TODO: get this working with this.arguments
var srcroot = "/src/dxr/";
var srcRegex = new RegExp("^" + srcroot);

//var sql = [];
var csv = [];

//////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////


function process_decl(d) {
    // skip things like /home/dave/dxr/tools/gcc-dehydra/installed/include/c++/4.3.0/exception
    if (srcRegex.test(d.loc.file)) return;

    if (!d.isFunction) return;

    // Skip things we don't care about
    if ((/:?:?operator.*$/.exec(d.name)) || /* overloaded operators */ (/^D_[0-9]+$/.exec(d.name)) || /* gcc temporaries */ (/^_ZTV.*$/.exec(d.name)) || /* vtable vars */ (/.*COMTypeInfo.*/.exec(d.name)) || /* ignore COMTypeInfo<int> */ ('this' == d.name) || (/^__built_in.*$/.exec(d.name))) /* gcc built-ins */
    return;

    // Treat the decl of a func like one of the statements in the func so we can link params
    var vfuncname = d.name;
    fix_path(d.loc);
    var vfuncloc = d.loc.file + ":" + d.loc.line.toString() + ":" + d.loc.column.toString();

    // Treat the actual func decl as a statement so we can easily linkify it
    var vtype = '';
    var vname = d.name;

    if (/::/.exec(vname)) {
        var parts = parse_name(d);
        vtype = parts.mtname || vtype;
        vname = parts.mname || vname;
    }

    var vshortname = vname.replace(/\(.*$/, '');
    var vlocf = d.loc.file;
    var vlocl = d.loc.line;
    var vlocc = d.loc.column;
    var vtloc = '';

    if (d.memberOf && d.memberOf.loc) {
        fix_path(d.memberOf.loc);
        vtloc = d.memberOf.loc.file + ":" + d.memberOf.loc.line.toString();
    }

    //sql.push (
    //insert_sql_stmt("stmts", ['vfuncname','vfuncloc','vname','vshortname','vlocf','vlocl','vlocc','vtype','vtloc','visFcall','visDecl'],
    //                      [vfuncname, vfuncloc, vname, vshortname, vlocf, vlocl, vlocc, vtype, vtloc,-1,1])
    //);
    csv.push(
    insert_csv_stmt("function", ['flongname', 'floc', 'fname', 'fshortname', 'vlocf', 'vlocl', 'vlocc', 'vtype', 'vtloc', 'visFcall', 'visDecl'], [vfuncname, vfuncloc, vname, vshortname, vlocf, vlocl, vlocc, vtype, vtloc, -1, 1]));

    if (!d.parameters) return;

    // Keep track of all params in the function
    for (var i = 0; i < d.parameters.length; i++) {
        vname = d.parameters[i].name;

        // we'll skip |this| and treat it as a keyword instead
        if ('this' == vname) continue;

        vshortname = vname.replace(/\(.*$/, ''); // XXX: will vname not always be the same in this case?
        vlocf = d.loc.file;
        vlocl = d.loc.line;
        d.loc.column++ // col is never accurate, but indicates "further"
        vlocc = d.loc.column;
        vtype = '';
        vtloc = '';
        if (d.parameters[i].type) {
            vtype = d.parameters[i].type.name;
            vtloc = d.parameters[i].type.loc ? d.parameters[i].type.loc.file + ":" + d.parameters[i].type.loc.line.toString() : '';
        }

        //sql.push (insert_sql_stmt("stmts", ['vfuncname','vfuncloc','vname','vshortname','vlocf','vlocl','vlocc','vtype','vtloc', 'visFcall', 'visDecl'],
        //                      [vfuncname, vfuncloc, vname, vshortname, vlocf, vlocl, vlocc, vtype, vtloc, -1, 1]));
        csv.push(insert_csv_stmt("function", ['flongname', 'floc', 'fname', 'vshortname', 'vlocf', 'vlocl', 'vlocc', 'vtype', 'vtloc', 'visFcall', 'visDecl'], [vfuncname, vfuncloc, vname, vshortname, vlocf, vlocl, vlocc, vtype, vtloc, -1, 1]));
    }
}


//////////////////////////////////////////////////////////////////////////////
// DECLs
//////////////////////////////////////////////////////////////////////////////


function process_type(c) {
    if (!srcRegex.test(c.loc.file) && /^[^\/]+\.cpp$/.exec(c.loc.file) && /dist\/include/.exec(c.loc.file)) return;
    //TODO - what to do about other types?
    if (c.typedef) process_typedef(c);
    else if (/class|struct/.exec(c.kind)) process_RegularType(c);
    else if (c.kind == 'enum') process_EnumType(c);
    // TODO: what about other types?

    function process_typedef(c) {
        // Normalize path and throw away column info -- we just care about file + line for types.
        fix_path(c.loc);
        var tloc = c.loc.file + ":" + c.loc.line.toString();
        var ttypedefname = c.typedef.name || '';
        var ttypedefloc = '';
        if (c.typedef.loc) {
            var vloc = c.typedef.loc;
            fix_path(vloc);
            ttypedefloc = vloc.file + ":" + vloc.line.toString();
        }

        var ttemplate = '';
        if (c.template) ttemplate = c.template.name;

        var tignore = 0;

        //sql.push(
        //  insert_sql_stmt("types", ['tname','tloc','ttypedefname','ttypedefloc','tkind','ttemplate','tignore','tmodule'],
        //                        [c.name, tloc, ttypedefname, ttypedefloc, 'typedef', ttemplate, tignore, 'fixme'])
        //);
        csv.push(
        insert_csv_stmt("type", ['tqualname', 'tloc', 'tname', 'ttypedefloc', 'tkind', 'ttemplate', 'tignore', 'tmodule'], [c.name, tloc, ttypedefname, ttypedefloc, 'typedef', ttemplate, tignore, 'fixme']));
    }

    function process_EnumType(c) {
        if (!c.name || c.name.toString() == 'undefined') return;

        // Normalize path and throw away column info -- we just care about file + line for types.
        fix_path(c.loc);
        var tloc = c.loc.file + ":" + c.loc.line.toString();

        // 'fixme' will be corrected in post-processing.  Can't do it here, because I need to follow
        // symlinks to get full paths for some files.
        //sql.push(insert_sql_stmt("types", ['tname','tloc','tkind','tmodule'],
        //                        [c.name, tloc, c.kind, 'fixme']));
        csv.push(
        insert_csv_stmt("type", ['tname', 'tloc', 'tkind', 'tmodule'], [c.name, tloc, c.kind, 'fixme']));

        if (c.members) {
            for (var i = 0; i < c.members.length; i++) {
                // XXX: use tloc for mtloc, mdecl, mdef, since they are essentially the same thing.
                var mshortname = c.members[i].name.replace(/\(.*$/, '');
                var mstatic = c.members[i].isStatic ? 1 : -1;
                var maccess = c.members[i].access || '';
                //sql.push(insert_sql_stmt("members", ['mtname','mtloc','mname','mshortname','mdecl','mdef','mvalue','maccess','mstatic'], [c.name,tloc,c.members[i].name,mshortname,tloc,tloc,c.members[i].value,maccess,mstatic]));
                csv.push(insert_csv_stmt("members", ['mtname', 'mtloc', 'mname', 'mshortname', 'mdecl', 'mdef', 'mvalue', 'maccess', 'mstatic'], [c.name, tloc, c.members[i].name, mshortname, tloc, tloc, c.members[i].value, maccess, mstatic]));
            }
        }
    }

    function process_RegularType(c) {
        if (!c.name || c.name.toString() == 'undefined') return;

        // Various internal types are uninteresting for autocomplete and such
        var tignore = 0;
        if (/.*COMTypeInfo.*/.exec(c.name)) return;

        // Lots of types are really just instances of a handful of templates
        // for example nsCOMPtr.  Keep track of the underlying template type
        var ttemplate = '';
        if (c.template) ttemplate = c.template.name;

        // If this type is a typedef for something else, get that info too
        var ttypedefname = '';
        var ttypedefloc = '';
        if (c.typedef) {
            ttypedefname = c.typedef.name;
            fix_path(c.typedef.loc);
            // Throw away column info for types.
            ttypedefloc = c.typedef.loc.file + ":" + c.typedef.loc.line.toString();
        }

        // Only add types when seen within source (i.e., ignore all type
        // info when used vs. declared, since we want source locations).
        // NOTE: this also kills off dist/include/foo/nsIFoo.h autogenerated from idl.
        // Mapping back to the idl is likely better anyhow (which MXR does now).
        // NOTE2: there is one more case we care about: sometimes .cpp files are linked
        // into the objdir, and linked locally (e.g., xpcom/glue), and in such cases
        // loc will be a filename with no path.  These are useful to have after post-processing.
        // Normalize path and throw away column info -- we just care about file + line for types.
        fix_path(c.loc);
        var tloc = c.loc.file + ":" + c.loc.line.toString();

        // 'fixme' will be corrected in post-processing.  Can't do it here, because I need to follow
        // symlinks to get full paths for some files.
        //sql.push(insert_sql_stmt("type", ['tname','tloc','ttypedefname','ttypedefloc','tkind','ttemplate','tignore','tmodule'],
        //                        [c.name, tloc, ttypedefname, ttypedefloc, c.kind, ttemplate, tignore, 'fixme']));
        csv.push(
        insert_csv_stmt("type", ['tqualname', 'tloc', 'tname', 'typedefloc', 'tkind', 'ttemplate', 'tignore', 'tmodule'], [c.name, tloc, ttypedefname, ttypedefloc, c.kind, ttemplate, tignore, 'fixme']));

        if (c.members) print_members(c, c.members);

        if (c.bases) print_all_bases(c, c.bases, true);
    }
}

//////////////////////////////////////////////////////////////////////////////
// Def
//////////////////////////////////////////////////////////////////////////////


function process_function(decl, body) {
    // Only worry about members in the source tree (e.g., ignore /usr/... or /dist/include)
    if (/.*\/dist\/include.*/.exec(decl.loc.file) || srcRegex.test(decl.loc.file)) return;

    fix_path(decl.loc);
    var floc = decl.loc.file + ":" + decl.loc.line.toString();

    if (decl.isStatic && !decl.memberOf) {
        // file-scope static
        //    sql.push(insert_sql_stmt("funcs", ['fname','floc'], [decl.name, floc]));
        //sql.push(insert_sql_stmt("members", ['mtname','mtloc','mname','mshortname','mdecl','mvalue','maccess','mstatic'], ['[File Scope Static]',decl.loc.file,decl.name,decl.shortname,floc,'','','1']));
        csv.push(insert_csv_stmt("members", ['mtname', 'mtloc', 'mname', 'mshortname', 'mdecl', 'mvalue', 'maccess', 'mstatic'], ['[File Scope Static]', decl.loc.file, decl.name, decl.shortname, floc, '', '', '1']));
    } else { // regular member in the src
        var m = parse_name(decl);
        var mtloc = 'no_loc'; // XXX: does this case really matter (i.e., won't memberOf.loc always exist)?
        if (decl.memberOf && decl.memberOf.loc) {
            fix_path(decl.memberOf.loc);
            mtloc = decl.memberOf.loc.file + ":" + decl.memberOf.loc.line.toString();
        }

        var update = "update or abort members set mdef=" + quote(floc);
        update += " where mtname=" + quote(m.mtname) + " and mtloc=" + quote(mtloc) + " and mname=" + quote(m.mname) + ";";

        //sql.push(update);
    }

    function processStatements(stmts) {
        function processVariable(s, /* optional */ loc) {
            // if name is undef, skip this
            if (!s.name) return;

            // TODO: should I figure out what is going on here?  Sometimes type is null...
            if (!s.type) return;

            // Skip gcc temporaries
            if (s.isArtificial) return;

            // if loc is defined (e.g., we're in an .assign statement[], use that instead).
            var vloc = loc || stmts.loc;

            if (!vloc) return;

            var vname = s.name;

            // Ignore statements and other things we can't easily link in the source.
            if ((/:?:?operator/.exec(vname)) /* overloaded operators */ || (/^D_[0-9]+$/.exec(vname)) /* gcc temporaries */ || (/^_ZTV.*$/.exec(vname)) /* vtable vars */ || (/.*COMTypeInfo.*/.exec(vname)) /* ignore COMTypeInfo<int> */ || ('this' == vname) || (/^__built_in.*$/.exec(vname))) /* gcc built-ins */
            return;

            var vtype = '';
            var vtloc = '';
            var vmember = '';
            var vmemberloc = '';
            var vdeclloc = '';

            if (s.type && s.type.loc) fix_path(s.type.loc);

            // Special case these smart pointer types: nsCOMPtr, nsRefPtr, nsMaybeWeakPtr, and nsAutoPtr.
            // This is a hack, and very Mozilla specific, but lets us treat these as if they were regular
            // pointer types.
            if ((/^nsCOMPtr</.exec(s.type.name) || /^nsRefPtr</.exec(s.type.name) || /^nsAutoPtr</.exec(s.type.name) || /^nsMaybeWeakPtr</.exec(s.type.name)) && s.type.template) {
                // Use T in nsCOMPtr<T>.
                vtype = s.type.template.arguments[0].name + "*"; // it's really a pointer, so add *
                vtloc = s.type.template.arguments[0].loc;
                // Increase the column, since we'll hit this spot multiple times otherwise
                // (e.g., once for nsCOMPtr and one for internal type.)  This prevents primary key dupes.
                vloc.column++;
            } else if (/::/.exec(s.name)) {
                var parts = parse_name(s);
                vtype = s.type.name;
                vtloc = s.type.loc;
                if (s.memberOf && s.memberOf.loc) {
                    fix_path(s.memberOf.loc);
                    vmember = s.memberOf.name;
                    vmemberloc = s.memberOf.loc.file + ":" + s.memberOf.loc.line.toString();
                }
                vname = parts.mname ? parts.mname : vname;
            } else {
                if (s.type.isPointer) {
                    vtype = s.type.type.name;
                    vtloc = s.type.type.loc;
                } else {
                    vtype = s.type.name;
                    vtloc = s.type.loc;
                }
            }

            if (s.fieldOf && !vtloc) vtloc = s.fieldOf.type.loc;

            // TODO: why are these null sometimes?
            //      if (vloc) 
            fix_path(vloc);
            var vlocf = vloc.file;
            var vlocl = vloc.line;
            var vlocc = vloc.column;

            // There may be no type, so no vtloc
            vtype = vtype || '';
            if (vtloc) {
                fix_path(vtloc);
                vtloc = vtloc.file + ":" + vtloc.line.toString();
            }

            if (s.loc) {
                fix_path(s.loc);
                vdeclloc = s.loc.file + ":" + s.loc.line.toString();
            }

            var vfuncloc = decl.loc.file + ":" + decl.loc.line.toString() + ":" + decl.loc.column.toString();
            var vshortname = s.shortName; //vname.replace(/\(.*$/, '');
            var visFcall = s.isFcall ? 1 : -1;

            //sql.push (insert_sql_stmt("stmts", ['vfuncname','vfuncloc','vname','vshortname','vlocf','vlocl','vlocc','vtype','vtloc','vmember','vmemberloc','visFcall','vdeclloc'],
            //                        [decl.name, vfuncloc, vname, vshortname, vlocf, vlocl, vlocc, vtype, vtloc, vmember, vmemberloc, visFcall, vdeclloc]));
            csv.push(insert_csv_stmt("stmts", ['vfuncname', 'vfuncloc', 'vname', 'vshortname', 'vlocf', 'vlocl', 'vlocc', 'vtype', 'vtloc', 'vmember', 'vmemberloc', 'visFcall', 'vdeclloc'], [decl.name, vfuncloc, vname, vshortname, vlocf, vlocl, vlocc, vtype, vtloc, vmember, vmemberloc, visFcall, vdeclloc]));

            // Deal with args to functions called by this var (i.e., function call, get a and b for g(a, b))
            if (s.arguments) {
                vloc.column += vname.length;
                for (var k = 0; k < s.arguments.length; k++) {
                    vloc.column += k + 1; // just to indicate "further"
                    processVariable(s.arguments[k], vloc);
                }
            }

            // Deal with any .assign variables (e.g., y = x ? a : b);
            if (s.assign) {
                vloc.column += vname.length;
                for (var k = 0; k < s.assign.length; k++) {
                    vloc.column += k + 1; // just to indicate "further"
                    processVariable(s.assign[k], vloc);
                }
            }
        }

        for (var j = 0; j < stmts.statements.length; j++) {
            var s = stmts.statements[j];
            // advance the column on this line by one to indicate we're "further" right/down
            if (stmts.loc) stmts.loc.column += j;
            processVariable(s);
        }

        for (var i = 0; i < body.length; i++) {
            processStatements(body[i]);
        }
    }
}

//////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////


//////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////


function print_all_bases(t, bases, direct) {
    // Keep track of whether this is a direct child of the base vs. many levels deep
    var directBase = direct ? 1 : -1;

    for (var i = 0; i < bases.length; i++) {
        var tbloc = 'no_loc';
        if (bases[i].type.loc) { // XXX: why would this not exist?
            fix_path(bases[i].type.loc);
            tbloc = bases[i].type.loc.file + ":" + bases[i].type.loc.line.toString();
        }

        var tcloc = 'no_loc';
        if (t.loc) { // XXX: why would this not exist?
            fix_path(t.loc);
            tcloc = t.loc.file + ":" + t.loc.line.toString();
        }

        //sql.push (insert_sql_stmt("impl", ['tbname','tbloc','tcname','tcloc','direct'],
        //                              [bases[i].type.name,tbloc,t.name,tcloc,directBase]));
        csv.push(insert_csv_stmt("impl", ['tbname', 'tbloc', 'tcname', 'tcloc', 'direct'], [bases[i].type.name, tbloc, t.name, tcloc, directBase]));
        if (bases[i].type.bases) {
            // pass t instead of base[i].name so as to flatten the inheritance tree for t
            print_all_bases(t, bases[i].type.bases, false);
        }
    }
}

//////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////


function print_members(t, members) {
    for (var i = 0; i < members.length; i++) {
        var m = parse_name(members[i]);
        // TODO: should I just use t.loc here instead?
        fix_path(members[i].memberOf.loc);
        var tloc = members[i].memberOf.loc.file + ":" + members[i].memberOf.loc.line.toString();

        if (!/.*\/dist\/include.*/.exec(members[i].loc.file) && srcRegex.test(members[i].loc.file)) {
            // if this is static, ignore the reported decl in the compilation unit.
            // .isStatic will only be reported in the containing compilation unit.
            //       if (!members[i].isStatic) {
            fix_path(members[i].loc);
            var loc = members[i].loc.file + ":" + members[i].loc.line.toString();
            var mvalue = members[i].value || ''; // enum members have a value
            var mstatic = members[i].isStatic ? 1 : -1;
            if (!members[i].isFunction || (members[i].isFunction && members[i].isExtern)) {
                // This is being seen via an #include vs. being done here in full, so just get decl loc
                var mshortname = m.mname.replace(/\(.*$/, '');
                //sql.push(insert_sql_stmt("members", ['mtname','mtloc','mname','mshortname','mdecl','mvalue','maccess','mstatic'], [m.mtname,tloc,m.mname,mshortname,loc,mvalue,members[i].access,mstatic]));
                csv.push(insert_csv_stmt("members", ['mtname', 'mtloc', 'mname', 'mshortname', 'mdecl', 'mvalue', 'maccess', 'mstatic'], [m.mtname, tloc, m.mname, mshortname, loc, mvalue, members[i].access, mstatic]));
            } else {
                // This is an implementation, not a decl loc, update def (we'll get decl elsewhere)
                print("UPDATE\n");
                var update = "update or abort members set mdef=" + quote(loc);
                update += " where mtname=" + quote(m.mtname) + " and mtloc=" + quote(tloc) + " and mname=" + quote(m.mname) + ";";
                //sql.push(update);
            }
            //      }
        }
    }
}

//////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////


function parse_name(c) {
    var result = {};

    // TODO: not working yet, but need to move this way...
    if (c.memberOf) {
        // Try and do this using member type info if possible
        result.mtname = c.memberOf.name;
        result.mname = c.name.replace(c.memberOf.name, '');
        result.mname = result.mname.replace(/^::/, '');
    } else {

        // Fallback to regex used to split type::member (if only it were that simple!)
        var m = /^(?:[a-zA-Z0-9_]* )?(?:(.*)::)?([^:]+(\(.*\)( .*)?)?)$/.exec(c.name).slice(1, 3);
        result.mtname = m[0];
        result.mname = m[1];

    }

    return result;
}

//////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////


function fix_path(loc) {
    // loc is {file: 'some/path', line: #, column: #}.  Normalize paths as follows:
    // from: /home/dave/gcc-dehydra/installed/bin/../lib/gcc/x86_64-unknown-linux-gnu/4.3.0/../../../../include/c++/4.3.0/exception:59
    // to:   /home/dave/gcc-dehydra/installed/include/c++/4.3.0/exception:59
    if (!loc) return;

    //ignore first slash
    var parts = loc.file.split("/").reverse();
    var fixed;
    var skip = 0;

    for (var i = 0; i < parts.length; i++) {
        if (parts[i] == "..") {
            skip++;
            continue;
        }

        if (skip == 0) {
            if (i == 0) fixed = parts[i];
            else fixed = parts[i] + "/" + fixed;
        } else {
            skip--;
        }
    }
    loc.file = fixed;
}

//////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////


function insert_sql_stmt(table, cols, vals) {
    var stmt = "insert or abort into " + table;
    if (cols) stmt += " " + build_list(cols);
    stmt += " values" + build_list(vals) + ";";
    return stmt;
}

function insert_csv_stmt(table, cols, vals) {
    var stmt = table;
    for (var i = 0; i < cols.length; i++) {
        stmt += ',' + cols[i] + ',' + '"' + vals[i] + '"';
    }
    return stmt;
}
//////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////


function build_list(a) {
    var l = "(";
    for (var i = 0; i < a.length; i++) {
        l += quote(a[i]);
        if (i < a.length - 1) l += ",";
    }
    l += ")";
    return l;
}

//////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////


function quote(s) {
    return "'" + s + "'";
}

require({ after_gcc_pass: "cfg" });
include('platform.js');
include('gcc_compat.js');
include('gcc_util.js');
include('gcc_print.js');
include('map.js');
include('unstable/lazy_types.js');
include('unstable/dehydra_types.js');

let DEBUG = true ;

let edges = [];
let virtuals = [];

function input_end() {
    debug_print("input_end");
    write_file(sys.aux_base_name + ".csv", csv.join("\n") + "\n");
    //write_file (sys.aux_base_name + ".sql", sql.join("\n") + "\n");
    let serial = serialize_edges(edges);
    serial += serialize_virtuals(virtuals);
    write_file(sys.aux_base_name + ".cg.sql", serial);
}

function serialize_edges(edges) {
    // array of edges, each edge looks like so:
    // { caller: { fn: "fn", rt: "rt", loc: "file" },
    //   callee: { fn: "fn", rt: "rt", loc: "file" } }
    // serialize two nodes and an edge using sql INSERT statements.
    debug_print("serialize_edges:["+edges+"]");
    let serial = "";
    for each(edge in edges) {
        serial += push_node(edge.caller);
        serial += push_node(edge.callee);
        serial += push_edge(edge);
        serial += '\n';
    }
    return serial;
}

function serialize_virtuals(virtuals) {
    let serial = "";
    for each(tuple in virtuals) {
        serial += 'INSERT INTO implementors (implementor, interface, method, loc) VALUES ("'
        + serialize_class(tuple.implementor) + '", "'
        + serialize_class(tuple.interface) + '", "'
        + serialize_method(tuple.implementor) + '", "'
        + tuple.interface.loc + '");\n';
    }
    return serial;
}

function serialize_full_method(method) {
    return method.rt + " " + serialize_class(method) + "::" + serialize_method(method);
}

function serialize_method(method) {
    return method.method + "(" + method.params.join(",") + ")";
}

function serialize_class(method) {
    return (method.ns ? (method.ns + "::") : "") + (method.class ? method.class : "");
}

function serialize_boolean(bool) {
    return bool ? "1" : "0";
}

function ensure_string(str) {
    return (str || '');
}

function push_node(node) {
    debug_print("push_node");
    return 'INSERT INTO node (name, returnType, namespace, type, shortName, isPtr, isVirtual, loc) VALUES ("'
    + serialize_full_method(node) + '", "'
    + ensure_string(node.rt) + '", "'
    + ensure_string(node.ns) + '", "'
    + ensure_string(node.class) + '", "'
    + ensure_string(node.method) + '", '
    + serialize_boolean(node.isPtr) + ', '
    + serialize_boolean(node.isVirtual) + ', "'
    + node.loc + '");\n';
}

function push_edge(edge) {
    debug_print("push_edge");
    return 'INSERT INTO edge (caller, callee) VALUES (' + '(SELECT id FROM node WHERE name = "' + serialize_full_method(edge.caller) + '" AND loc = "' + edge.caller.loc + '"), ' + '(SELECT id FROM node WHERE name = "' + serialize_full_method(edge.callee) + '" AND loc = "' + edge.callee.loc + '")' + ');\n';
}

function process_tree_type(t) {
    // scan the class, and its bases, for virtual functions
    //if (!COMPLETE_TYPE_P(t)) { debug_print("\tincomplete type:["+class_key_or_enum_as_string(t)); return; }

    // check if we have a class or struct
    let kind = class_key_or_enum_as_string(t);
    if (kind != "class" && kind != "struct") { return; }

    debug_print("process_tree_type:"+kind);
    // for each member method...
    for (let func = TYPE_METHODS(t); func; func = TREE_CHAIN(func)) {
        if (TREE_CODE(func) != FUNCTION_DECL) continue;

        if (DECL_ARTIFICIAL(func)) continue;
        if (DECL_CLONED_FUNCTION_P(func)) continue;
        if (TREE_CODE(func) == TEMPLATE_DECL) continue;

        if (DECL_PURE_VIRTUAL_P(func) || !DECL_VIRTUAL_P(func)) continue;

        // ignore destructors here?
        // have a class method. pull the namespace and class names.
        let implementor = get_names(func);
        debug_print("impl: " + serialize_full_method(implementor));

        // have a nonpure virtual member function...
        // which could potentially be implemented by this class.
        // scan subclasses to find which ones declare it.
        process_subclasses(t, implementor);
    }
}

function get_names(decl) {
    debug_print("get_names");
    // for a class, names.class and names.method will be defined.
    // for a function, names.method will be defined.
    // for either, names.ns may be defined depending on whether the context is a namespace.
    // for a fnptr, there will be no namespace, class name, or method name -
    // just a return type and params.
    let names = {};

    let fn = TREE_CODE(TREE_TYPE(decl)) == FUNCTION_TYPE || TREE_CODE(TREE_TYPE(decl)) == METHOD_TYPE;
    if (!fn) throw new Error("decl is not a function!");

    // check if we have a function pointer.
    let fnptr = TREE_CODE(decl) == POINTER_TYPE;
    if (fnptr) names.isPtr = true;

    // return type name
    names.rt = type_string(TREE_TYPE(TREE_TYPE(decl)));

    // XXX ptr to member?
    // see http://tuvix.apple.com/documentation/DeveloperTools/gcc-4.2.1/gccint/Expression-trees.html PTRMEM_CST
    // namespace and class name. but if this is a fnptr, there is no context to be had...
    if (!fnptr) {
        // we have a function or method.
        let context = DECL_CONTEXT(decl);
        if (context) {
            // resolve the file loc to a unique absolute path, with no symlinks.
            // use the context here since the declaration will be unique.
            names.loc = location_string(context);

            let have_class = TYPE_P(context);
            if (have_class) context = TYPE_NAME(context);

            let array = context.toCString().split("::");
            if (array.length == 0) throw new Error("no context!");

            if (have_class) {
                // have a class or struct. last element in the array is the class name,
                // and everything before are the namespaces.
                names.class = array.pop();
                if (names.class.length == 0) throw new Error("no class name!");
            }
            if (array.length > 0) {
                // the rest are namespaces.
                names.ns = array.join("::");
            }
        } else {
            // resolve the file loc to a unique absolute path, with no symlinks.
            // have no context, so use what we've got
            names.loc = location_string(decl);
        }

        // XXX for has_this: DECL_NONSTATIC_MEMBER_FUNCTION_P
        // XXX for class ctx (incl enum/union/struct) see gcc_compat.js:class_key_or_enum_as_string(t)
        // method name
        let name = DECL_NAME(decl);
        if (name) {
            // if we have a cloned constructor/destructor (e.g. __comp_ctor/
            // __comp_dtor), pull the original name
            if (DECL_LANG_SPECIFIC(decl) && DECL_CONSTRUCTOR_P(decl)) {
                names.method = names.class;
            } else if (DECL_LANG_SPECIFIC(decl) && DECL_DESTRUCTOR_P(decl)) {
                names.method = "~" + names.class;
            } else if (DECL_LANG_SPECIFIC(decl) && IDENTIFIER_OPNAME_P(name) && IDENTIFIER_TYPENAME_P(name)) {
                // type-conversion operator, e.g. |operator T*|. gcc assigns a random name
                // along the lines of |operator 11|, so come up with something more useful.
                names.method = "operator " + type_string(TREE_TYPE(name));
            } else {
                // usual case.
                names.method = IDENTIFIER_POINTER(name);
            }

            if (DECL_VIRTUAL_P(decl)) names.isVirtual = true;

            //names.push(DECL_UID(decl)); // UID of method
        }

        if (!names.loc) throw new Error("should have a loc by now!");

    } else {
        // provide something sensible for fnptrs.
        names.method = "(*)";
        names.loc = "";
    }

    // parameter type names
    let type = TREE_TYPE(decl);
    let args = TYPE_ARG_TYPES(type);
    if (TREE_CODE(type) == METHOD_TYPE) {
        // skip |this|
        args = TREE_CHAIN(args);
    }

    names.params = [type_string(TREE_VALUE(pt))
    for (pt in flatten_chain(args))
    if (TREE_CODE(TREE_VALUE(pt)) != VOID_TYPE)];

    return names;
}

function location_string(decl) {
    let loc = location_of(decl);
    if (loc == UNKNOWN_LOCATION) throw new Error("unknown location");

    if (LOC_IS_BUILTIN(loc)) return "<built-in>";

    let path = loc.file;

    try {
        return resolve_path(path);
    } catch (e) {
        if (e.message.indexOf("No such file or directory")) {
            // this can occur if people use the #line directive to artificially override
            // the source file name in gcc. in such cases, there's nothing we can really
            // do, and it's their fault if the filename clashes with something.
            return path;
        }

        // something else happened - rethrow
        throw new Error(e);
    }
}

function process_subclasses(c, implementor) {
    debug_print("process_subclasses");
    let bases = [BINFO_TYPE(base_binfo)
            for each (base_binfo in VEC_iterate(BINFO_BASE_BINFOS(TYPE_BINFO(c))))];

    for each(base in bases) {
        // for each member method...
        for (let func = TYPE_METHODS(base); func; func = TREE_CHAIN(func)) {
            if (TREE_CODE(func) != FUNCTION_DECL) continue;

            if (DECL_ARTIFICIAL(func)) continue;
            if (DECL_CLONED_FUNCTION_P(func)) continue;
            if (TREE_CODE(func) == TEMPLATE_DECL) continue;

            if (!DECL_VIRTUAL_P(func)) continue;

            // have a class method. pull the namespace and class names.
            let iface = get_names(func);
            debug_print("iface: " + serialize_full_method(iface));

            if (method_signatures_match(implementor, iface)) {
                let v = {
                    "implementor": implementor,
                    "interface": iface
                };
                virtuals.push(v);
            }
        }

        // scan subclass bases as well
        process_subclasses(base, implementor);
    }
}

function method_signatures_match(m1, m2) {
    debug_print("method_signatures_match");
    return m1.method == m2.method && m1.params.join(",") == m2.params.join(",") && m1.rt == m2.rt;
}

function process_tree(fn) {
    debug_print("CALLER: " + serialize_full_method(get_names(fn))
    +' '+location_of(fn)
    );

    let cfg = function_decl_cfg(fn);
    for (let bb in cfg_bb_iterator(cfg)) {
        for (let isn in bb_isn_iterator(bb)) {
            walk_tree(isn, function (t, stack) {
		print (serialize_full_method(get_names(fn))+' '+TREE_CODE(t)+' '+location_of(t));
                if (TREE_CODE(t) != GIMPLE_CALL) { return; }

                let callee = resolve_function_decl(t);
                if (!callee) throw new Error("unresolvable function " + expr_display(t));

                debug_print("  callee:    " + serialize_full_method(get_names(callee)));

                // serialize the edge
                let edge = {
                    caller: {},
                    callee: {}
                };
                edge.caller = get_names(fn);
                edge.callee = get_names(callee);
                edges.push(edge);
            });
        }
    }
}

function resolve_function_decl(expr) {
    debug_print("resolve_function_decl");
    let r = gimple_call_fndecl(expr);
    switch (TREE_CODE(r)) {
    case OBJ_TYPE_REF:
        return resolve_virtual_fun_from_obj_type_ref(r);
    case FUNCTION_DECL:
    case ADDR_EXPR:
        return gimple_call_fndecl(expr);
    case VAR_DECL:
    case PARM_DECL:
        // have a function pointer. the VAR_DECL holds the fnptr, but we're interested in the type.
        return TREE_TYPE(r);
    default:
        throw new Error("resolve_function_decl: unresolvable decl with TREE_CODE " + TREE_CODE(r));
    }
}

function debug_print(str) {
    if (DEBUG) print(str);
}
