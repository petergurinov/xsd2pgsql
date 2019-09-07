xsd2pgsql
=========

Create a DB structure from an XML Schema.

Usage
=====
Ouput of ``--help``::

Create a database based on an XSD schema, SQL is output to stdout.

positional arguments:
  FILE             XSD file to base the Postgres Schema on

optional arguments:
  -h, --help       show this help message and exit
  -f, --fail       Fail on finding a bad XS type
  -a, --as-is      Don't normalize element names
  -r, --relations  Add relations from xsd to sql by comments
  -d, --debug      enable debugging
  -s, --silent     don't log to console