let DEBUG_LEVEL=1;

//////////////////////////////////////////////////////////////////////////////
// Utility functions
//////////////////////////////////////////////////////////////////////////////
function Serializer() {
        this.storage = [];
        this.insert =  function(table, colsVals)
        {
                var stmt = table;
                for (var el in colsVals)
                {
                        stmt += ',' + el + ',' + '"' + colsVals[el] + '"';
                }
                this.storage.push(stmt);
        }
        this.get = function() { return this.storage; }
}
csv = new Serializer();
//////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////
function buildList(a)
{
    var l = "(";
    for (var i = 0; i < a.length; i++)
    {
        l += quote(a[i]);
        if (i < a.length - 1) l += ",";
    }
    l += ")";
    return l;
}


function debugPrint(lvl,str)
{
    if (lvl <= DEBUG_LEVEL) print("JS: "+str);
}

function methodSignaturesMatch(m1, m2)
{
    debugPrint(2,"methodSignaturesMatch");
    return m1.method == m2.method && m1.params.join(",") == m2.params.join(",") && m1.rt == m2.rt;
}


function ignorableFile(f)
{
    //|| /^[^\/]+\.cpp$/.exec(type.loc.file))
    return false;
}


function ensureString(str)
{
    return (str || '');
}

/**
 * Get the short name of a decl name. E.g. turn
 * "MyNamespace::MyClass::Method(int j) const" into
 * "Method"
 */
function getScopeName(decl)
{
  let name = decl.name;
  let lp = name.lastIndexOf('::');
  if (lp != -1)
    name = name.slice(0, lp);
  return name;
}

function quote(s)
{
    return "'" + s + "'";
}

function locationToString(decl)
{
    let loc = decl.loc;
    if (loc == UNKNOWN_LOCATION)
    {
        loc = location_of(decl);
        if (loc == UNKNOWN_LOCATION) throw new Error("unknown location:"+location_of(decl) );
        if (LOC_IS_BUILTIN(loc)) return "<built-in>";
    }

    let path = loc.file;

    try
    {
        //XXXresolve_path(path)
        return path + ':' + loc.line.toString() + ':' + loc.column.toString();
    }
    catch (e)
    {
        if (e.message.indexOf("No such file or directory"))
        {
            // this can occur if people use the #line directive to artificially override
            // the source file name in gcc. in such cases, there's nothing we can really
            // do, and it's their fault if the filename clashes with something.
            return path + ':' + loc.line.toString() + ':' + loc.column.toString();
        }

        // something else happened - rethrow
        throw new Error(e);
    }
}
function getExtent(decl,name)
{
    let loc = decl.loc;
    if (loc == UNKNOWN_LOCATION)
    {
        loc = location_of(decl);
        if (loc == UNKNOWN_LOCATION) throw new Error("unknown location");
        if (LOC_IS_BUILTIN(loc)) return "<built-in>";
    }

    try
    {
        //XXXresolve_path(path)
        print("LENGTH:"+loc.column);
        return loc.line.toString() + ':' + loc.column.toString() + ':' + loc.line.toString()+':'+(parseInt(loc.column)+parseInt(name.length));
    }
    catch (e)
    {
        if (e.message.indexOf("No such file or directory"))
        {
            // this can occur if people use the #line directive to artificially override
            // the source file name in gcc. in such cases, there's nothing we can really
            // do, and it's their fault if the filename clashes with something.
            return loc.line.toString() + ':' + loc.column.toString() + ':' + name.length;
        }

        // something else happened - rethrow
        throw new Error(e);
    }
}

//////////////////////////////////////////////////////////////////////////////
//mtname=member type name
//mname=membername
//////////////////////////////////////////////////////////////////////////////
function parseName(c)
{
    var result = {};
    // XXX: not working yet, but need to move this way...
    if (c.memberOf)
    {
        // Try and do this using member type info if possible
        result.tname = c.memberOf.name;
        result.name = c.name.replace(c.memberOf.name, '');
        result.name = result.name.replace(/^::/, '');
    }
    else
    {
        // Fallback to regex used to split type::member (if only it were that simple!)
        var m = /^(?:[a-zA-Z0-9_]* )?(?:(.*)::)?([^:]+(\(.*\)( .*)?)?)$/.exec(c.name).slice(1, 3);
        result.tname = m[0];
        result.name = m[1];
    }

    return result;
}

/////////////////////////////////////////////////////////
/////////////////////////////////////////////////////////
/////////////////////////////////////////////////////////




//////////////////////////////////////////////////////////////////////////////
// Keep track of whether this is a direct child of the
// base vs. many levels deep
//////////////////////////////////////////////////////////////////////////////
function printAllBases(t, bases)
{
    for (var i = 0; i < bases.length; i++)
    {
        debugPrint(1,"XXX:"+bases[i].name);
        var tbloc = locationToString(bases[i].type);
        var tcloc = locationToString(t);
        let access = bases[i].access + bases[i].isVirtual ? ' virtual' : '';
        csv.insert("impl",
                {
                'tcname':t.name,
                'tcloc':tcloc,
                'tbname':bases[i].type.name,
                'tbloc':tbloc,
                'access':access
                });
        csv.insert("ref",
                {
                'varname':bases[i].type.name,
                'varloc':tbloc,
                'refloc':tcloc,
                'extent': getExtent(bases[i].type,bases[i].type.name)
                });


        if (bases[i].type.bases)
        {
            // pass t instead of base[i].name so as to flatten the inheritance tree for t
            printAllBases(t, bases[i].type.bases);
        }
    }
}




//////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////
function printMembers(t, members)
{
    for (var i = 0; i < members.length; i++)
    {
        var m = parseName(members[i]);
        if (ignorableFile(members[i].loc.file)) continue;

        // if this is static, ignore the reported decl in the compilation unit.
        // .isStatic will only be reported in the containing compilation unit.
        //       if (!members[i].isStatic)
        if (members[i].isFunction && members[i].isExtern) {
                csv.insert("function",
                        {
                        'fname': members[i].shortName,
                        'fqualname': members[i].name.replace(fargs,""),
                        'ftype' : members[i].type.type.name,
                        'fargs' : fargs,
                        'floc': locationToString(members[i]),
                        'scopename': getScopeName(members[i]),
                        'extent' :getExtent(members[i],members[i].shortName)
                        });
        }
        else
        {
            // This is an implementation, not a decl loc, update def (we'll get decl elsewhere)
            /*XXXcsv.insert("decldef",
                {
                'name':members[i].name,
                'declloc':locationToString(members[i]),
                'defloc':locationToString(members[i].memberOf),
                });*/
        }
    }
}







//////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////


//////////////////////////////////////////////////////////////////////////////
// CALLGRAPH
//////////////////////////////////////////////////////////////////////////////
require(
{
    after_gcc_pass: "cfg"
});
include('platform.js');
include('gcc_compat.js');
include('gcc_util.js');
include('gcc_print.js');
include('map.js');
include('unstable/lazy_types.js');
include('unstable/dehydra_types.js');

let edges = [];
let virtuals = [];

//////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////

function serializeFullMethod(method)
{
    return method.rt + " " + serializeClass(method) + "::" + serializeMethod(method);
}

function serializeMethod(method)
{
    return method.method + "(" + method.params.join(", ") + ")";
}

function serializeClass(method)
{
    return (method.ns ? (method.ns + "::") : "") + (method.class ? method.class : "");
}

function serializeBoolean(bool)
{
    return bool ? "1" : "0";
}

//////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////


function insertNode(node)
{
    let o = {
        'name': node.name, //serializeFullMethod(node)  ,
        'returnType': ensureString(node.rt),
        'namespace': ensureString(node.ns),
        'type': ensureString(node.class),
        'shortName': ensureString(node.method),
        'isPtr': serializeBoolean(node.isPtr),
        'isVirtual': serializeBoolean(node.isVirtual),
        'loc': node.loc
        };
    debugPrint(2,"insertNode:"+o);
    csv.insert('node', o ) ;
}


function insertCall(edge)
{
    debugPrint(2,"insertCall");
    csv.insert('call',
        {
        'callername': edge.caller.shortName, //serializeFullMethod(edge.caller),
        'callerloc': edge.caller.loc,
        'calleename': edge.callee.shortName, //serializeFullMethod(edge.callee),
        'calleeloc': edge.callee.loc,
        'calltype':'static'
        });
}


//////////////////////////////////////////////////////////////////////////////
// @param edges: array of edges, each edge looks like:
// { caller: { fn: "fn", rt: "rt", loc: "file" },
//   callee: { fn: "fn", rt: "rt", loc: "file" } }
// serialize two nodes and an edge
//////////////////////////////////////////////////////////////////////////////
function insertEdges(edges)
{
    debugPrint(2,"insertEdges:[" + edges + "]");
    for each(edge in edges)
    {
        insertCall(edge);
    }
}

function insertVirtuals(virtuals)
{
    let serial = "";
    for each(tuple in virtuals)
    {
        csv.insert('impl', 
                {
                'implementor': serializeClass(tuple.implementor),
                'interface': serializeClass(tuple.interface),
                'method': serializeMethod(tuple.implementor),
                'loc': tuple.interface.loc
                });
    }
    return serial;
}


//////////////////////////////////////////////////////////////////////////////
// for a class, names.class and names.method will be
// defined.
//
// for a function, names.method will be defined.
//
// for either, names.ns may be defined depending on
// whether the context is a namespace.
//
// for a fnptr, there will be no namespace, class name,
// or method name, just a return type and params.
//////////////////////////////////////////////////////////////////////////////
function getTNames(decl)
{
    debugPrint(2,"getTNames");
    let names = {};

    let fn = TREE_CODE(TREE_TYPE(decl)) == FUNCTION_TYPE
          || TREE_CODE(TREE_TYPE(decl)) == METHOD_TYPE;
    if (!fn) throw new Error("decl is not a function!");

    // check if we have a function pointer.
    let fnptr = TREE_CODE(decl) == POINTER_TYPE;
    if (fnptr) names.isPtr = true;

    // return type name
    names.rt = type_string(TREE_TYPE(TREE_TYPE(decl)));

    // XXX ptr to member?
    // see http://tuvix.apple.com/documentation/DeveloperTools/gcc-4.2.1/gccint/Expression-trees.html PTRMEM_CST
    // namespace and class name. but if this is a fnptr, there is no context to be had...
    if (fnptr)
    {
        // provide something sensible for fnptrs.
        names.method = "(*)";
        names.loc = UNKNOWN_LOCATION;
    }
    else
    {
        // we have a function or method.
        let context = DECL_CONTEXT(decl);
        if (context && TREE_CODE(context) != TRANSLATION_UNIT_DECL)
        {
            // use the context here since the declaration will be unique.
            names.loc = locationToString(context);

            let have_class = TYPE_P(context);
            if (have_class) context = TYPE_NAME(context);

            let array = context.toCString().split("::");
            if (array.length == 0) throw new Error("no context!");

            if (have_class)
            {
                // have a class or struct. last element in the array is the class name,
                // and everything before are the namespaces.
                names.class = array.pop();
                if (names.class.length == 0) throw new Error("no class name!");
            }
            if (array.length > 0)
            {
                // the rest are namespaces.
                names.ns = array.join("::");
            }
        }
        else
        {
            // have no context, so use what we've got
            names.loc = locationToString(decl);
        }

        // XXX for has_this: DECL_NONSTATIC_MEMBER_FUNCTION_P
        // XXX for class ctx (incl enum/union/struct) see gcc_compat.js:class_key_or_enum_as_string(t)
        // method name
        let name = DECL_NAME(decl);
        if (name)
        {
            // if we have a cloned constructor/destructor (e.g. __comp_ctor/
            // __comp_dtor), pull the original name
            if (DECL_LANG_SPECIFIC(decl) && DECL_CONSTRUCTOR_P(decl))
            {
                names.method = names.class;
            }
            else if (DECL_LANG_SPECIFIC(decl) && DECL_DESTRUCTOR_P(decl))
            {
                names.method = "~" + names.class;
            }
            else if (DECL_LANG_SPECIFIC(decl) && IDENTIFIER_OPNAME_P(name) && IDENTIFIER_TYPENAME_P(name))
            {
                // type-conversion operator, e.g. |operator T*|. gcc assigns a random name
                // along the lines of |operator 11|, so come up with something more useful.
                names.method = "operator " + type_string(TREE_TYPE(name));
            }
            else
            {
                // usual case.
                names.method = IDENTIFIER_POINTER(name);
            }

            if (DECL_VIRTUAL_P(decl)) names.isVirtual = true;

            //names.push(DECL_UID(decl)); // UID of method
        }

        if (!names.loc) throw new Error("should have a loc by now!");

    }
    // parameter type names
    let type = TREE_TYPE(decl);
    let args = TYPE_ARG_TYPES(type);
    if (TREE_CODE(type) == METHOD_TYPE)
    {
        // skip |this|
        args = TREE_CHAIN(args);
    }

    names.params = [type_string(TREE_VALUE(pt))
            for (pt in flatten_chain(args))
            if (TREE_CODE(TREE_VALUE(pt)) != VOID_TYPE)];
    names.fullName=serializeMethod(names);
    names.shortName=names.method;
    debugPrint(2,names);
    return names;
}


function processSubclasses(c, implementor)
{
    debugPrint(2,"processSubclasses");
    let bases = [BINFO_TYPE(base_binfo)
                    for each(base_binfo in VEC_iterate(BINFO_BASE_BINFOS(TYPE_BINFO(c))))];

    for each(base in bases)
    {
        // for each member method...
        for (let func = TYPE_METHODS(base); func; func = TREE_CHAIN(func))
        {
            if (TREE_CODE(func) == TEMPLATE_DECL) continue;
            if (TREE_CODE(func) != FUNCTION_DECL) continue;
            if (DECL_CLONED_FUNCTION_P(func)) continue;
            if (DECL_ARTIFICIAL(func)) continue;
            if (!DECL_VIRTUAL_P(func)) continue;

            // have a class method. pull the namespace and class names.
            let iface = getTNames(func);
            debugPrint(2,"iface: " + serializeFullMethod(iface));

            if (methodSignaturesMatch(implementor, iface))
            {
                let v = {
                    "implementor": implementor,
                    "interface": iface
                };
                virtuals.push(v);
            }
        }

        // scan subclass bases as well
        processSubclasses(base, implementor);
    }
}


function resolveFunctionDecl(expr)
{
    debugPrint(2,"resolveFunctionDecl");
    let r = gimple_call_fndecl(expr);
    switch (TREE_CODE(r))
    {
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
        throw new Error("resolveFunctionDecl: unresolvable decl with TREE_CODE " + TREE_CODE(r));
    }
}

//////////////////////////////////////////////////////////////////////////////
// Hydra specific
//////////////////////////////////////////////////////////////////////////////

/*
 * process_decl is called for every
 *  global variable, function, or template declaration.
 *
 * @param decl  A variable type
 */
function process_decl(decl)
{
    if (ignorableFile(decl.loc.file)) return;
    debugPrint(3,"s:"+decl+">>>");
    if ( ! decl.isFunction ) {
       debugPrint(3,"exNotFunction");
            csv.insert("variable",
                    {
                    'vname': decl.name,
                    'vloc': locationToString(decl),
                    'vtype': decl.type.name, // this will not work for arrays
                    'extent' :getExtent(decl,decl.shortName)
                    });
       return;
    }

    // Skip things we don't care about
    if ((/:?:?operator.*$/.exec(decl.name)) // overloaded operators
    || (/^D_[0-9]+$/.exec(decl.name))       // gcc temporaries
    || (/^_ZTV.*$/.exec(decl.name))         // vtable vars
    || (/.*COMTypeInfo.*/.exec(decl.name))  // ignore COMTypeInfo<int>
    || ('this' == decl.name)                // this
    || (/^__built_in.*$/.exec(decl.name)))  // gcc built-ins
        return;

    // Treat the actual func decl as a statement so we can easily linkify it
    var vtype = '';
    var vname = decl.name;

    // member function
    if (/::/.exec(vname))
    {
        var parts = parseName(decl);
        vtype = parts.tname || vtype;
        vname = parts.name || vname;
    }

    /*XXXcsv.insert("decldef",
        {
        'name': decl.shortName,
        'declloc': locationToString(decl),
        'defloc':'12'
        });*/
    processFunctionArguments(decl);

    function processFunctionArguments(decl)
    {
        if (!decl.parameters) { print("NO_PARAMS"); return; }

        // Keep track of all params in the function
        for (var i = 0; i < decl.parameters.length; i++)
        {
            vname = decl.parameters[i].name;

            // we'll skip |this| and treat it as a keyword instead
            if ('this' == vname) continue;

            vshortname = vname.replace(/\(.*$/, ''); // XXX: will vname not always be the same in this case?
            vlocf = decl.loc.file;
            vlocl = decl.loc.line;
            decl.loc.column++ // col is never accurate, but indicates "further"
            vlocc = decl.loc.column;
            vtype = '';
            vtloc = '';
            if (decl.parameters[i].type)
            {
                vtype = decl.parameters[i].type.name;
                vtloc = decl.parameters[i].type.loc ? locationToString(decl.parameters[i].type) : '';
            }
            csv.insert("variable",
                     {
                        'vname':vname,
                        'vloc':locationToString(decl),
                        'vtype':vtype,
                        'extent' :getExtent(decl,decl.shortName)
                     });
        }
    }// processFunArguments
}


/*
 * Dehydra calls this for each
 *  class, struct, enum, union, and typedef declaration.
 *
 * process_type is called after process_function is called
 * for all the member functions.
 * @param type  A type object representing the type that
 *              was declared.
 *
 * process_type() (actually, printMembers() called via process_type)
 * - gives a member's declaration (mdecl) IF loc is normalized
 */
function process_type(type)
{
    if ( ignorableFile(type.loc.file) ) return ;
    //XXX - what to do about other types?
    if (type.typedef) return processTypedef(type);
    if (type.kind == 'enum') return processEnum(type);
    if (type.kind == 'class' || type.kind=='struct') return processClassOrStruct(type);

    function processTypedef(type)
    {
        // Normalize path and throw away column info -- we just care about file + line for types.
        var tname = ensureString(type.name);
        var tloc = locationToString(type);
        var tqualname = ensureString(type.typedef.name);

        var ttemplate = '';
        if (type.template) ttemplate = type.template.name;

        csv.insert("typedef",
                {'tname': tname,
                 'tloc': tloc,
                 'tqualname': tqualname,
                 'tkind': 'typedef',
                 'ttemplate': ttemplate
                 });
    }/*function processTypedef*/

    function processEnum(type)
    {
        if (!type.name || type.name.toString() == 'undefined') return;

        // Normalize path and throw away column info -- we just care about file + line for types.
        var tloc = locationToString(type);
        if ( tloc == "<built-in>:0:0" ) return;
        m = parseName(type);
        csv.insert("type",
                {'tname': ensureString(m.name),
                 'tqualname': ensureString(type.name),
                 'tloc': tloc,
                 'tkind': type.kind,
                 'extent': getExtent(type,m.name)
                 /*XXX
                 'scopename': 'SOME_SCOPE', 
                 'scopeloc': 'file:1:2'
                 */
                });
        if (type.members)
        {
            for (var i = 0; i < type.members.length; i++)
            {
                var mstatic = type.members[i].isStatic ? 1 : -1;
                var maccess = ensureString(type.members[i].access);
                // XXX
                csv.insert("variable",
                        {
                        'vname': type.name+'::'+type.members[i].name,
                        'vloc': tloc,
                        'vtype': type.kind,
                        });
            }
        }
    }/*processEnum*/

    function processClassOrStruct(type)
    {
        if (!type.name
        || type.name.toString() == 'undefined')
            return;

        // Various internal types are uninteresting for autocomplete and such
        var tignore = 0;
        if (/.*COMTypeInfo.*/.exec(type.name)) return;

        // Lots of types are really just instances of a handful of templates
        // for example nsCOMPtr.  Keep track of the underlying template type
        //var ttemplate = '';
        //if (type.template) ttemplate = type.template.name;
        // If this type is a typedef for something else, get that info too
        //var ttypedefname = '';
        //var ttypedefloc = '';
        //if (type.typedef) {
        //    ttypedefname = type.typedef.name;
        //    // Throw away column info for types.
        //    ttypedefloc = locationToString(type.typedef);
        //}
        // Only add types when seen within source (i.e., ignore all type
        // info when used vs. declared, since we want source locations).
        // NOTE: this also kills off dist/include/foo/nsIFoo.h autogenerated from idl.
        // Mapping back to the idl is likely better anyhow (which MXR does now).
        // NOTE2: there is one more case we care about: sometimes .cpp files are linked
        // into the objdir, and linked locally (e.g., xpcom/glue), and in such cases
        // loc will be a filename with no path.  These are useful to have after post-processing.
        // Normalize path and throw away column info -- we just care about file + line for types.
        var tloc = locationToString(type);
        if ( tloc == "<built-in>:0:0" ) return;
        m = parseName(type);
        csv.insert("type",
            {'tname': m.name,
            'tqualname': type.name,
            'tloc': tloc,
            'tkind': type.kind
            });

        if (type.members) printMembers(type, type.members);
        if (type.bases) printAllBases(type, type.bases, true);
    }/*processClassOrStruct*/
}

//////////////////////////////////////////////////////////////////////////////
// Def
//////////////////////////////////////////////////////////////////////////////
/*
 * @brief: gives a member's definition (mdef) of a normalized loc
 *
 * - NOTE: process_function/printMembers will give the same loc
 *   if the member is defined/declared in the same place
 * Ex:
 *   nsAccessible.h 138: static PRUint32 State(nsIAccessible *aAcc) { PRUint32 state = 0; if (aAcc) aAcc->GetFinalState(&state, nsnull); return state; }
 *   nsAccessible process_function() mtname=nsAccessible mname=State(nsIAccessible*) loc=/home/dave/mozilla-central/src/accessible/src/base/nsAccessible.h:138
 *   nsAccessible printMembers() mtname=nsAccessible mname=State(nsIAccessible*) loc=/home/dave/mozilla-central/src/accessible/src/base/nsAccessible.h:138
 *
 * - NOTE: data members will have nothing in process_function, and only appear in printMembers(), for example:
 *
 *  253: PRInt32 mAccChildCount; // protected data member
 *  nsAccessible printMembers() mtname=nsAccessible mname=mAccChildCount loc=/home/dave/mozilla-central/src/accessible/src/base/nsAccessible.h:253
 */

/*
 * Dehydra calls this for each function definition
 * (declarations without bodies are not included),
 * including both top-level functions, class member
 * functions, and inline class member functions.
 *
 * @param decl  A Variable Type object representing the
 *              function being processed
 * @param body  An array of
 *              {loc:, statements:array of Variable Types}
 *              representing an outline of the function
 *              stripped down to
 *                  variables, function calls and assignments.
 */
function process_function(decl, body)
{
    // Only worry about members in the source tree.
    if (ignorableFile(decl.loc.file)) return;
    fargs = '('+decl.name.split(decl.shortName+'(')[1];
    debugPrint(1,"FARGS:"+fargs);
    csv.insert("function",
            {
            'fname': decl.shortName,
            'fqualname': decl.name.replace(fargs,""),
            'ftype' : decl.type.type.name,
            'fargs' : fargs,
            'floc': locationToString(decl),
            'extent': getExtent(decl,decl.shortName)
            });
/*XXX csv.insert("members",
                {'mtname': '[File Scope Static]',
                'mtloc': decl.loc.file,
                'mname': decl.name,
                'mshortname': decl.shortname,
                'mdecl': floc,
                'mvalue': '',
                'maccess': '',
                'mstatic': '1'
                });
    }
    else
    { // regular member in the src
        var m = parseName(decl);
        var mtloc = UNKNOWN_LOCATION;
        if (decl.memberOf && decl.memberOf.loc)
            mtloc = locationToString(decl.memberOf);
        //var update = "update or abort members set mdef=" + quote(floc);
        //update += " where mtname=" + quote(m.tname) + " and mtloc=" + quote(mtloc) + " and mname=" + quote(m.name) + ";";
        //debugPrint(2,"UPDATE:" + update);
    } */
    for (var i = 0; i < body.length; i++)
    {
        processStatements(body[i]);
    }

    function processStatements(stmts)
    {
        for (var j = 0; j < stmts.statements.length; j++)
        {
            var stmt = stmts.statements[j];
            // advance the column on this line by one to indicate we're "further" right/down
            if (stmts.loc) stmts.loc.column += j;
            processVariable(stmt,stmts.loc);
        }
        function processVariable(s, loc)
        {
            // if name is undef, skip this
            if (!s.name) { debugPrint(3, "ex1"+s); return; }

            // XXX: should I figure out what is going on here?  Sometimes type is null...
            if (!s.type) return;

            // Skip gcc temporaries
            if (s.isArtificial) return;

            // if loc is defined (e.g., we're in an .assign statement[], use that instead).
            var vloc = loc || stmts.loc;

            if (!vloc) return;

            var vname = s.shortName;

            // Ignore statements and other things we can't easily link in the source.
            if ((/:?:?operator/.exec(vname)) // overloaded operators
            || (/^D_[0-9]+$/.exec(vname)) // gcc temporaries
            || (/^_ZTV.*$/.exec(vname)) // vtable vars
            || (/.*COMTypeInfo.*/.exec(vname)) // ignore COMTypeInfo<int>
            || ('this' == vname)
            || (/^__built_in.*$/.exec(vname))) // gcc built-ins
                return;
            var vtype = '';
            var vtloc = '';
            var vmember = '';
            var vmemberloc = '';
            var vdeclloc = '';


            // Special case these smart pointer types: nsCOMPtr, nsRefPtr, nsMaybeWeakPtr, and nsAutoPtr.
            // This is a hack, and very Mozilla specific, but lets us treat these as if they were regular
            // pointer types.
            if ((/^nsCOMPtr</.exec(s.type.name)
            || /^nsRefPtr</.exec(s.type.name)
            || /^nsAutoPtr</.exec(s.type.name)
            || /^nsMaybeWeakPtr</.exec(s.type.name)) && s.type.template)
            {
                // Use T in nsCOMPtr<T>.
                vtype = s.type.template.arguments[0].name + "*"; // it's really a pointer, so add *
                vtloc = s.type.template.arguments[0].loc;
                // Increase the column, since we'll hit this spot multiple times otherwise
                // (e.g., once for nsCOMPtr and one for internal type.)  This prevents primary key dupes.
                vloc.column++;
            }
            else if (/::/.exec(s.name))
            {
                var parts = parseName(s);
                vname = s.name;
                vtype = s.type.name;
                vtloc = locationToString(s);
            }
            else
            {
                if (s.type.isPointer)
                {
                    vtype = s.type.type.name;
                    vtloc = s.type.type.loc;
                }
                else
                {
                    vtype = s.type.name;
                    vtloc = s.type.loc;
                }
            }

            if (s.fieldOf && !vtloc)
                vtloc = s.fieldOf.type.loc;

            if (s.loc)
            {
                vdeclloc = locationToString(s);
            }

            var visFcall = s.isFcall ? 1 : -1;
            debugPrint(1,"REF:"+loc+"++==++"+vname);
            csv.insert("ref",
                    {
                    'varname': vname,
                    'varloc': locationToString(s),
                    'refloc': loc
                    });

            // Deal with args to functions called by this var (i.e., function call, get a and b for g(a, b))
            if (s.arguments)
            {
                vloc.column += vname.length;
                for (var k = 0; k < s.arguments.length; k++)
                {
                    vloc.column += k + 1; // just to indicate "further"
                    processVariable(s.arguments[k], vloc);
                }
            }

            // Deal with any .assign variables (e.g., y = x ? a : b);
            if (s.assign)
            {
                vloc.column += vname.length;
                for (var k = 0; k < s.assign.length; k++)
                {
                    vloc.column += k + 1; // just to indicate "further"
                    processVariable(s.assign[k], vloc);
                }
            }
        } /*function processVariable*/
    } /*function processStatements*/
}

function process_tree(fn)
{
    debugPrint(2,"CALLER: " + serializeFullMethod(getTNames(fn)) + ' ' + location_of(fn));
    debugPrint(1,"process_tree:location:"+location_of(fn) );

    let cfg = function_decl_cfg(fn);
    for (let bb in cfg_bb_iterator(cfg))
    {
        for (let isn in bb_isn_iterator(bb))
        {
            walk_tree(isn, function (t, stack)
            {
                debugPrint(2,serializeFullMethod(getTNames(fn)) + ' ' + TREE_CODE(t) + ' ' + location_of(t));
                if (TREE_CODE(t) != GIMPLE_CALL)
                {
                    return;
                }

                let callee = resolveFunctionDecl(t);
                if (!callee) throw new Error("unresolvable function " + expr_display(t));
                // serialize the edge
                let edge = {
                    caller: {},
                    callee: {}
                };
                edge.caller = getTNames(fn);
                edge.callee = getTNames(callee);
                edges.push(edge);
            });
        }
    }
}
function process_tree_decl(t)
{
	//if ( TREE_CODE(t) ==NAMESPACE_DECL )
    debugPrint(1,"process_tree_decl:"+t+":"+location_of(t) );
}
// scan the class, and its bases, for virtual functions
function process_tree_type(t)
{
    debugPrint(1,"TREE_CODE:"+TREE_CODE(t));
    //if (!COMPLETE_TYPE_P(t)) { debugPrint(2,"\tincomplete type:["+class_key_or_enum_as_string(t)); return; }
    // check if we have a class or struct
    let kind = class_key_or_enum_as_string(t);
    if (kind != "class" && kind != "struct")
        return;

    debugPrint(2,"process_tree_type:" + kind);
    // for each member method...
    for (let func = TYPE_METHODS(t); func; func = TREE_CHAIN(func))
    {
        if (TREE_CODE(func) != FUNCTION_DECL) continue;
        if (TREE_CODE(func) == TEMPLATE_DECL) continue;
        if (DECL_CLONED_FUNCTION_P(func)) continue;
        if (DECL_ARTIFICIAL(func)) continue;
        if (DECL_PURE_VIRTUAL_P(func)) continue;
        if (!DECL_VIRTUAL_P(func)) continue;

        // ignore destructors here?
        // have a class method. pull the namespace and class names.
        let implementor = getTNames(func);

        // have a nonpure virtual member function...
        // which could potentially be implemented by this class.
        // scan subclasses to find which ones declare it.
        processSubclasses(t, implementor);
    }
}

function input_end()
{
    debugPrint(2,"input_end");
    insertEdges(edges);
    insertVirtuals(virtuals);
    write_file(sys.aux_base_name + ".csv", csv.get().join("\n") + "\n");
}
