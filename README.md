# csv to QIF converter for GnuCash
Converts CSV files from various Dutch banks into QIF files.

* ING Bank (checking & savings)
* Rabobank (checking)
* Rabobank (beleggen)
* DeGiro

The parser is tested/optimized to work with GnuCash.

Usage:

`csv2qif.py csv_file.csv` -->  csv_file.qif

`csv2qif.py *.csv` -->  out.qif

The parser will categorize transaction according to (python module re) regex rules described in categories.csv.
You can add you own rules; these are processed from top to bottom; processing for 
a transaction is stopped when a match is found.
Matching is done on either "payee" or "memo".

Parser will list all transactions which don't have a match for a category. You can
"dry-run" a few times to optimize the categories.csv.

## Bank account definitions
Define your back accounts in `/bankaccounts.def`. This file is self explaining.

Order of accounts is important; transactions from a lower prio account
to higher prio account are ignored, to prevent double transactions.


## Extend parser
* Add your bank definition file to /banks
  * Identify a unique fingerprint field for your csv file based on a regex.
  * Specify parser method (defined in parsebank.py)
  * Specify date format

With a bit of luck, you can use an existing parser. Or copy and extend.

## Requirements
* quiffen > 1.1.1
* python > 3.x (tested with 3.7.3)

## Versions

1.0.2:
* Fix error processing when command line is empty
* Fix errors when calling from different location/directory or via symbolic link