#! /usr/bin/python3
""" xsd2pgsql.py
========================================

Create a database based on an XSD schema. 

Usage
========================================
    <file>  XSD file to base the Postgres Schema on

    -f  --fail          Fail on finding a bad XS type
    -a  --as-is         Don't normalize element names.
    -r  --relations     Add relations from xsd to sql by comments
    -d  --debug         Enable degug info.
"""

""" Some configuration items """
MAX_RECURSE_LEVEL = 20

""" XSD to Postgres data type translation dictionary. 
"""
class SDict(dict):
    def __getitem__(self, item):
        return dict.__getitem__(self, item) % self
    def get(self, item):
        try:
            return dict.__getitem__(self, item) % self
        except KeyError:
            return None
DEFX2P = SDict({
    'string':               'varchar',
    'boolean':              'boolean',
    'decimal':              'numeric',
    'float':                'real',
    'double':               'double precision',
    'duration':             'interval',
    'dateTime':             'timestamp',
    'time':                 'time',
    'date':                 'date',
    'gYearMonth':           'timestamp',
    'gYear':                'timestamp',
    'gMonthDay':            'timestamp',
    'gDay':                 'timestamp',
    'gMonth':               'timestamp',
    'hexBinary':            'bytea',
    'base64Binary':         'bytea',
    'anyURI':               'varchar',
    'QName':                None,
    'NOTATION':             None,
    'normalizedString':     '%(string)s',
    'token':                '%(string)s',
    'language':             '%(string)s',
    'NMTOKEN':              None,
    'NMTOKENS':             None,
    'Name':                 '%(string)s',
    'NCName':               '%(string)s',
    'ID':                   None,
    'IDREF':                None,
    'IDREFS':               None,
    'ENTITY':               None,
    'ENTITIES':             None,
    'integer':              'integer',
    'nonPositiveInteger':   '%(integer)s',
    'negativeInteger':      '%(integer)s',
    'long':                 '%(integer)s',
    'int':                  '%(integer)s',
    'short':                '%(integer)s',
    'byte':                 '%(integer)s',
    'nonNegativeInteger':   '%(integer)s',
    'unsignedLong':         '%(integer)s',
    'unsignedInt':          '%(integer)s',
    'unsignedShort':        '%(integer)s',
    'unsignedByte':         '%(integer)s',
    'positiveInteger':      '%(integer)s',
})
USER_TYPES = {}

XMLS = "{http://www.w3.org/2001/XMLSchema}"
XMLS_PREFIX = "xs:"
XMLS_USER_PREFIX = ["v:"]
ALL_PREFIX = []
ALL_PREFIX.append(XMLS_PREFIX)
for p in XMLS_USER_PREFIX:
    ALL_PREFIX.append(p)

# "Response",
XMLS_USER_SUF = ["DTO"]

""" Output """
SQL = ''

""" Helpers
"""
class InvalidXMLType(Exception): pass
class MaxRecursion(Exception): pass


def pg_normalize(string):
    """ Normalize strings like column names for PG """
    if not string: string = ''
    string = re.sub(r"(\w)([A-Z])", r"\1_\2", string) # IdentifiersOfChangedObjects => 'Identifiers_Of_Changed_Objects'
    string = string.replace('-', '_')
    string = string.replace('.', '_')
    string = string.replace(' ', '_')
    string = string.replace('/', '_')
    string = string.replace('\\', '_')
    string = string.lower()
    return string


def look4element(ns, el, parent=None, recurse_level=0, fail=False, normalize=True, relations=False):
    """ Look for elements recursively 

    returns tuple (children bool, sql string)
    """
    if recurse_level > MAX_RECURSE_LEVEL: raise MaxRecursion()
    cols = ''
    children = False
    sql = ''
    for x in el.findall(ns + 'element'):
        children = True
        
        rez = look4element(ns, x, x.get('name') or parent, recurse_level + 1, fail=fail, normalize=normalize, relations=relations)
        sql += rez[1] + '\n'
        if not rez[0]:

            logger.debug('parent({}) <{} name={} type={}> {}'.format(parent, x.tag, x.get('name'), x.get('type'), x.text))
            
            thisType = x.get('type') or x.get('ref') or 'string'
            k = thisType.replace(XMLS_PREFIX, '')
            
            pgType = DEFX2P.get(k) or USER_TYPES.get(k) or None

            notNull = ''
            if not x.get('minOccurs') and pgType:
                notNull = ' NOT NULL'

            if not pgType:
                for p in ALL_PREFIX: 
                    k = thisType.replace(p, '')
                    if len(thisType) != len(k):
                        pgType = k
                        break
            
            """Add FOREIGN KEY by full path to type element"""
            if pgType:
                ForeignKey = ''
                for s in XMLS_USER_SUF:
                    if pgType.endswith(s):
                        ForeignKey = '/* FOREIGN KEY {} | maxOccurs: {} */'.format(thisType, x.get('maxOccurs') if x.get('maxOccurs') else '1')
                    if ForeignKey != '':
                        break
            

            if not pgType and fail:
                raise InvalidXMLType("{} is an invalid XSD type.".format(XMLS_PREFIX + thisType))
            elif pgType:
                colName = x.get('name') or x.get('ref')
                if normalize:
                    colName = pg_normalize(colName)
            
                if not cols:
                    cols = "{}{} {} {} {}".format("/*"+ (x.get('name') or x.get('ref')) + "*/ "  if relations else "", colName, pgType, notNull, ForeignKey if relations else "")
                else:
                    cols += ",{}{} {} {} {}".format("/*"+ (x.get('name') or x.get('ref')) + "*/ "  if relations else "", colName, pgType, notNull, ForeignKey if relations else "") 
    if cols:
        sql += """CREATE TABLE {}{}({});""".format(pg_normalize(parent) if normalize else parent, " /*" + parent + "*/ " if relations else " ", cols)

    for elements in ['complexType', 'complexContent', 'sequence', 'extension', 'choice', 'enumeration']:
        for x in el.findall(ns + elements):
            children = True
            rez = look4element(ns, x, x.get('name') or parent, recurse_level + 1, fail=fail, normalize=normalize, relations=relations)
            sql += rez[1] + '\n'
    
    return (children, sql)


def build_types(ns, root_element):
    """ Take care of any types that were defined in the XSD """
    for el in root_element.findall(ns + 'element'):
        if el.get('name') and el.get('type'):
            for p in ALL_PREFIX: 
                k = el.get('type').replace(p, '')
                if len(el.get('type')) != len(k):
                    break
            USER_TYPES[pg_normalize(el.get('name'))] = "FK " + k

    for el in root_element.findall(ns + 'simpleType'):
        restr = el.find(ns + 'restriction')
        USER_TYPES[pg_normalize(el.get('name'))] = restr.get('base').replace(XMLS_PREFIX, '')

def setup_logging(options):
    """Configure logging."""
    root = logging.getLogger("")
    root.setLevel(logging.WARNING)
    logger.setLevel(options.debug and logging.DEBUG or logging.INFO)
    if not options.silent:
        if not sys.stderr.isatty():
            facility = logging.handlers.SysLogHandler.LOG_DAEMON
            sh = logging.handlers.SysLogHandler(address='/dev/log',
                                                facility=facility)
            sh.setFormatter(logging.Formatter(
                "{0}[{1}]: %(message)s".format(
                    logger.name,
                    os.getpid())))
            root.addHandler(sh)
        else:
            ch = logging.StreamHandler()
            ch.setFormatter(logging.Formatter(
                "%(levelname)s[%(name)s] %(message)s"))
            root.addHandler(ch)      

""" Do it
"""
if __name__ == '__main__':

    """ Imports
    """
    import argparse
    import re
    import sys
    import os
    import logging
    import logging.handlers
    import pyxb.utils.domutils as domutils
    from lxml import etree

    logger = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])

    """ Handle options
    """
    parser = argparse.ArgumentParser(description='Create a database based on an XSD schema, SQL is output to stdout.')
    parser.add_argument(
        'xsd', 
        metavar='FILE', 
        type= argparse.FileType('r'), 
        nargs='+',
        help='XSD file to base the Postgres Schema on'
    )
    parser.add_argument(
        '-f', '--fail', 
        dest = 'fail_on_bad_type', 
        action = 'store_true',
        default = False,
        help = 'Fail on finding a bad XS type'
    )
    parser.add_argument(
        '-a', '--as-is', 
        dest = 'as_is', 
        action = 'store_true',
        default = False,
        help = "Don't normalize element names"
    )
    parser.add_argument(
        '-r', '--relations', 
        dest = 'relations', 
        action = 'store_true',
        default = False,
        help = "Add relations from xsd to sql by comments"
    )
    parser.add_argument(
        '-d', '--debug',
        action="store_true",
        default=False,
        help="enable debugging"
    )
    parser.add_argument(
        '-s', '--silent',
        action="store_true",
        default=False,
        help="don't log to console"
    )
    args = parser.parse_args()

    setup_logging(args)

    """ MEAT
    """
    if not args.xsd:
        sys.exit('XSD file not specified.')
    else:
        for f in args.xsd:
            #xsdFile = open(f, 'r')
        
            """ Parse the XSD file
            """
            xsd = etree.parse(f)
            
            # glean out defined types
            build_types(XMLS, xsd)
            # parse structure
            if args.as_is:
                norm = False
            else:
                norm = True
            result = look4element(XMLS, xsd, pg_normalize(f.name.split('.')[0]), fail=args.fail_on_bad_type, normalize=norm, relations=args.relations)
        if result[1]:
            print(result[1].replace('\n\n', ''))
        else:
            raise Exception("This shouldn't happen.")