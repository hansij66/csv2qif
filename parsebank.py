#!/usr/bin/python3


"""
Description
-----------

All parser methods for specific csv files and helper methods


        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import re
import csv
from datetime import datetime
import fileinput



# logging
import __main__
import logging
import os

script=os.path.basename(__main__.__file__)
script=os.path.splitext(script)[0]
logger = logging.getLogger(script + "." +  __name__)

# global list of bank definition files
# without path
# TODO remove global variable
listofbanks = []
BASEPATH = os.path.dirname(os.path.realpath(__file__))


def sanitizeString(line, lowercase=False):
  """
  Removes leading and trailing spaces
  Removes duplicate spaces
  Optionally, converts string to lower case

  :param str line:
  :param bool lowercase:
  :return sanitized line
  :rtype str

  """

  line = line.lstrip()
  line = line.rstrip()
  line = " ".join(line.split())
  if lowercase:
    line = line.lower()
  return line


def convertDecimalComma(amount):
  """
  Convert decimal comma to decimal point notation
  25.400,05 --> 25400.05

  Removes any non digits (as Rabobank certificaten add %)

  :param str amount: amount to be converted
  :return sanitized amount:
  :rtype str
  """

  # remove decimal point
  __amount = amount.replace(".", "", 1)

  # replace decimal comma with decimal point
  __amount = __amount.replace(",", ".", 1)

  # remove keep all digits, decimal point and minus; remove all others
  __amount = re.sub("[^\d|.|-]", "", __amount)

  return __amount


def queryBankDefFiles():
  """
  Create list of all bank definition file

  Keyword arguments:
  """

  for file in os.listdir(BASEPATH + "/banks"):
    if file.endswith(".def"):
      listofbanks.append(file)
  return 0


def readDefinitionFile(definitionfile_):
  """
  Read content of a bank definition file

  Keyword arguments:
  :param str definitionfile_: Path + Filename to bank definition file
  :return definition_dict key:value pairs
  :rtype dict
  """

  definition_dict = {}

  with open(definitionfile_, newline='', mode='r') as definitionfp:
    for line in definitionfp:
      line = sanitizeString(line)

      #   strip comments and empty lines
      if line.startswith("#"): continue
      if len(line) == 0: continue

      try:
        (key, val) = line.split()
        definition_dict[(key)] = val
      except ValueError:
        logger.error(f"In {definitionfile_}, line = {line} does not have a key:val pair; Uncomment line or add a value")
        continue

  return definition_dict


def determineBank(infile):
  """
  Determine which banks matches to transaction csv file

  Keyword arguments:
  :param str infile: Path + Filename to bank csv file
  :return (bank definition file, parser) : success
          ("NONE", "NONE") : no match found
          ("DUPLICATE", "NONE") : collision, multiple matches
  :rtype tuple
  """

  # counter how many matches with bankdefinition files are found
  # success = 1 match
  nrofMatches = 0
  returnValue = ("NONE", "NONE")

  # iterate through all bank definition files
  for bank in listofbanks:
    definitionfile = BASEPATH + "/banks/" + bank
    logger.debug(f"Matching {infile} with{definitionfile} .........................")

    definition_dict = readDefinitionFile(definitionfile)

    # get cvs file format from definition_dict
    delimiter_ = definition_dict['DELIMITER']  # How the csv is separated
    quotechar_ = definition_dict['QUOTECHAR']  # quoatation chars of fileds
    col_fp_ = int(definition_dict['COL_FINGERPRINT'])  # fingerprint col
    row_fp_ = int(definition_dict['ROW_FINGERPRINT'])  # fingerprint field
    fpregex_ = definition_dict['FINGERPRINTREGEX']  # fingerprint regex
    csvparser = definition_dict['CSVPARSER']  # parser to be used

    with open(infile, newline='', mode='r', encoding='latin1') as csvfp:
      # create csv object using the given delimeter & quotechar
      csvIn = csv.reader(csvfp, delimiter=delimiter_, quotechar=quotechar_)

      # skip all rows till row_fp
      for i in range(row_fp_):
        next(csvIn, None)

      row = next(csvIn)

      try:
        if re.match(fpregex_, row[ col_fp_]):
          returnValue = (definitionfile, csvparser)
          nrofMatches += 1
      except IndexError:
        continue

  if nrofMatches > 1:
    returnValue = ("DUPLICATE", "NONE")

  # CSV file does not match with any definition file
  return returnValue


def readRabobankCheckingCSV(csvfile_, definitionfile_, csvlist):
  """
  Parse Rabobank Checking/Regular account CSV file
  
  :param str csvfile_: Path + Filename to bank csv file
  :param str definitionfile_:Path + Filename to definition file of bank
  :param list of dictionaries csvlist: list of dictionaries of parsed transactions
  """

  # definition of various fields in csv file; depends on bank
  definition_dict = readDefinitionFile(definitionfile_)

  # get cvs file format from definition_dict
  header_ = int(definition_dict['SKIPHEADERS'])  # How many header lines to skip?
  date_ = int(definition_dict['COL_DATE']) # date of transaction
  dateformat_ = definition_dict['DATEFORMAT1'] # strptime format string
  iban_ = int(definition_dict['COL_IBAN']) # account number
  amount_ = int(definition_dict['COL_AMOUNT']) #How much was the transaction
  balance_ = int(definition_dict['COL_BALANCE'])  # How much was the transaction
  memo_ = int(definition_dict['COL_MEMO']) #discription of the transaction
  to_iban_ = int(definition_dict['COL_IBANPAYEE']) #name to account
  payee_ = int(definition_dict['COL_NAMEPAYEE']) #name to account
  delimiter_ = definition_dict['DELIMITER'] #How the csv is separated
  quotechar_ = definition_dict['QUOTECHAR'] #quoatation chars of fileds
  sequence_ = int(definition_dict['COL_SEQUENCE']) #sequence of transaction

  with open(csvfile_, newline='', mode='r', encoding='latin1') as csvfp:
    # create csv object using the given delimeter & quotechar
    csvIn = csv.reader(csvfp, delimiter=delimiter_, quotechar=quotechar_)

    # skip header line(s)
    for i in range(header_):
      next(csvIn, None)

    for row in csvIn:
      # replace decimal comma with decimal point
      row[amount_] = convertDecimalComma(row[amount_])
      row[balance_] = convertDecimalComma(row[balance_])

      # convert date from YYYY-MM-DD to datetime format
      row[date_] = datetime.strptime(row[date_], dateformat_)

      # SPECIAL CASE with associated investment account
      # Rabo investment account starts with 3 - atleast for accounts I know, 8 digits, eg 31234567
      # If investment account is define in bankaccounts.def, all should work as a charm
      # Find buy/sell of securities and associate to_iban with investment account
      m = re.match("^.*(koop|verkoop) internet.*(3[0-9]{7}).*$", row[memo_].lower())
      if m:
        row[to_iban_] = m.group(2)

      # remove leading and trailing spaces; optionally convert to lowercase
      row[iban_] = sanitizeString(row[iban_], lowercase=True)
      row[to_iban_] = sanitizeString(row[to_iban_], lowercase=True)
      row[payee_] = sanitizeString(row[payee_])
      row[memo_] = sanitizeString(row[memo_])

      csvlist.append({"date" : row[date_],
                      "transactiontype": "Bank",
                      "iban" : row[iban_],
                      "sequence" : row[sequence_],
                      "to_iban" : row[to_iban_],
                      "payee" : row[payee_],
                      "amount" : row[amount_],
                      "balance" : row[balance_],
                      "memo" : row[memo_],
                      "category" : ""
                      }.copy())

  return 0


def readINGCheckingCSV(csvfile_, definitionfile_, csvlist):
  """
  Parse ING Checking/Regular account CSV file

  Keyword arguments:
  :param str csvfile_: Path + Filename to bank csv file
  :param str definitionfile_:Path + Filename to definition file of bank
  :param list of dictionaries csvlist: list of dictionaries of parsed transactions csvlist
  """

  # definition of various fields in csv file; depends on bank
  definition_dict = readDefinitionFile(definitionfile_)

  # get cvs file format from definition_dict
  header_ = int(definition_dict['SKIPHEADERS'])  # How many header lines to skip?
  date_ = int(definition_dict['COL_DATE']) # date of transaction
  dateformat_ = definition_dict['DATEFORMAT1'] # strptime format string
  iban_ = int(definition_dict['COL_IBAN']) # account number
  amount_ = int(definition_dict['COL_AMOUNT']) #How much was the transaction
  sign_ = int(definition_dict['COL_SIGN'])  # AF or BIJ (deposit or withdrawal)
  balance_ = int(definition_dict['COL_BALANCE'])  # How much was the transaction
  memo1_ = int(definition_dict['COL_MEMO1']) #discription of the transaction (omschrijving)
  memo2_ = int(definition_dict['COL_MEMO2'])  # discription of the transaction (mededeling)
  to_iban_ = int(definition_dict['COL_IBANPAYEE']) #name to account
  payee_ = int(definition_dict['COL_NAMEPAYEE']) #name to account
  delimiter_ = definition_dict['DELIMITER'] #How the csv is separated
  quotechar_ = definition_dict['QUOTECHAR'] #quoatation chars of fileds

  with open(csvfile_, newline='', mode='r', encoding='latin1') as csvfp:
    # create csv object using the given delimeter & quotechar
    csvIn = csv.reader(csvfp, delimiter=delimiter_, quotechar=quotechar_)

    # skip header line(s)
    for i in range(header_):
      next(csvIn, None)

    for row in csvIn:
      # replace decimal comma with decimal point
      row[amount_] = convertDecimalComma(row[amount_])
      row[balance_] = convertDecimalComma(row[balance_])

      if row[sign_].lower() == "af":
        row[amount_] = str( -1.0 * float(row[amount_]) )

      # convert date from YYYY-MM-DD to datetime format
      row[date_] = datetime.strptime(row[date_], dateformat_)

      # remove leading and trailing spaces; optionally convert to lowercase
      row[iban_] = sanitizeString(row[iban_], lowercase=True)
      row[to_iban_] = sanitizeString(row[to_iban_], lowercase=True)
      row[payee_] = sanitizeString(row[payee_])
      row[memo1_] = sanitizeString(row[memo1_])
      row[memo2_] = sanitizeString(row[memo2_])

      csvlist.append({"date" : row[date_],
                      "transactiontype": "Bank",
                      "iban" : row[iban_],
                      "sequence" : 0,
                      "to_iban" : row[to_iban_],
                      "payee" : row[payee_],
                      "amount" : row[amount_],
                      "balance" : row[balance_],
                      "memo" : row[memo1_] + "|" + row[memo2_],
                      "category" : ""
                      }.copy())

  return 0


def readDeGiroTransactionsCSV(csvfile_, definitionfile_, csvlist):
  """
  Parse DeGiro TRANSACTIONS CSV file

  The transactions csv file only contains buy/sell of securities
  Dividends and costs are via DeGiro ACCOUNTS CSV file

  Keyword arguments:
  :param str csvfile_: Path + Filename to bank csv file
  :param str definitionfile_:Path + Filename to definition file of bank
  :param list of dictionaries csvlist: list of dictionaries of parsed transactions csvlist
  """

  # definition of various fields in csv file; depends on bank
  definition_dict = readDefinitionFile(definitionfile_)

  # get cvs file format from definition_dict
  header_ = int(definition_dict['SKIPHEADERS'])
  delimiter_ = definition_dict['DELIMITER']
  quotechar_ = definition_dict['QUOTECHAR']
  degiroIBAN = definition_dict['CHECKINGACCOUNT']

  date_ = int(definition_dict['COL_DATE']) # date of transaction
  dateformat1_ = definition_dict['DATEFORMAT1'] # strptime format string
  dateformat2_ = definition_dict['DATEFORMAT2'] # strptime format string
  memo_ = int(definition_dict['COL_MEMO']) #discription of the transaction
  sequence_ = int(definition_dict['COL_ORDERID'])
  iban_ = int(definition_dict['COL_IBAN']) # this is a fake; just to store DeGiro iban
  isin_ = int(definition_dict['COL_ISIN']) # security
  stockmarket_ = int(definition_dict['COL_STOCKMARKET'])  # stock market
  price_ = int(definition_dict['COL_PRICE']) # price of security
  quantity_ = int(definition_dict['COL_QUANTITY'])  # quantity of security bought/sold
  amount_ = int(definition_dict['COL_AMOUNT']) # amount of transaction w/o commission
  commission_ = int(definition_dict['COL_COMMISSION'])
  transfer_amount_ = int(definition_dict['COL_TOTAL'])

  # Sofar, only one currency (EURO) is supported/tested.
  # Check if another currency than EUR is used
  # Check is done a bit later in this method
  currency = []
  currency.append( f"{int(definition_dict['COL_PRICECURRENCY'])}" )
  currency.append( f"{int(definition_dict['COL_LOCALCURRENCY'])}" )
  currency.append( f"{int(definition_dict['COL_AMOUNTCURRENCY'])}" )
  currency.append( f"{int(definition_dict['COL_COMMISSIONCURRENCY'])}" )
  currency.append( f"{int(definition_dict['COL_TOTALCURRENCY'])}" )

  with open(csvfile_, newline='', mode='r', encoding='latin1') as csvfp:
    # create csv object using the given delimeter & quotechar
    csvIn = csv.reader(csvfp, delimiter=delimiter_, quotechar=quotechar_)

    # skip header line(s)
    for i in range(header_):
      next(csvIn, None)

    for row in csvIn:
      # convert date to datetime format
      # Use second format if exception on first
      try:
        row[date_] = datetime.strptime(row[date_], dateformat1_)
      except ValueError:
        row[date_] = datetime.strptime(row[date_], dateformat2_)

      row[iban_] = sanitizeString(degiroIBAN, lowercase=True)

      # "Sell"; "Buy"; "ShrsIn"; "ShrsOut" The latter 2 are not implemented
      # Gnucash ignores this anyway (I think)
      if float(row[amount_]) > 0:
        action_ = "Sell"
      else:
        action_ = "Buy"

      #  Check whether non-EURO currencies are used
      for i in currency:
        if row[ int(i) ] != "EUR" and row[ int(i) ] != "":
          logger.error(f"Transaction is not in EUR; this is not yet supported! {row[date_]}: {row[isin_]}")

      # positive number = BUY
      # negative number is SELL
      # Flip signs
      row[transfer_amount_] = str(-1.0*(float(row[transfer_amount_])))

      # Commission
      # positive number == expense
      try:
        row[commission_] = str(-1.0*(float(row[commission_])))
      except:
        None

      # It seems that:
      # amount = price * quantity + commission
      # my original erroneous assumption was that:
      # amount = price * quantity
      # transfer_amount = -(amount + commission)
      csvlist.append({"date" : row[date_],
                      "transactiontype": "Invst",
                      "iban" : row[iban_],
                      "sequence" : row[sequence_],
                      "isin" : row[isin_],
                      "price" : row[price_],
                      "quantity" : row[quantity_],
                      "amount": row[transfer_amount_],
                      "action" : action_,
                      "commission" : row[commission_],
                      "transfer_amount" : "",
                      "to_iban": "",
                      "payee" : "",
                      "category": "",
                      "memo" : row[memo_] + " @ " + row[stockmarket_] + " SEQ:" + row[sequence_]
                      }.copy() )

  return 0


def readDeGiroAccountCSV(csvfile_, definitionfile_, csvlist):
  """
  Parse DeGiro ACCOUNTS CSV file

  Buy/Sell of securities is processed via DeGiro transactions csv file
  This parser processes dividends, costs etc

  It is not 100% perfect...typically a few dimes off....DeGiro has IMO inconsistent csv file structure

  Keyword arguments:
  :param str csvfile_: Path + Filename to bank csv file
  :param str definitionfile_:Path + Filename to definition file of bank
  :param list of dictionaries csvlist: list of dictionaries of parsed transactions csvlist
  """

  # definition of various fields in csv file; depends on bank
  definition_dict = readDefinitionFile(definitionfile_)

  # get cvs file format from definition_dict
  header_ = int(definition_dict['SKIPHEADERS'])  # How many header lines to skip?
  delimiter_ = definition_dict['DELIMITER'] #How the csv is separated
  quotechar_ = definition_dict['QUOTECHAR'] #quoatation chars of fileds
  degiroIBAN = definition_dict['CHECKINGACCOUNT']

  date_ = int(definition_dict['COL_DATE']) # date of transaction
  dateformat1_ = definition_dict['DATEFORMAT1'] # strptime format string
  dateformat2_ = definition_dict['DATEFORMAT2'] # strptime format string
  memo_ = int(definition_dict['COL_MEMO']) #discription of the transaction
  iban_ = int(definition_dict['COL_IBAN']) # this is a fake; just to store DeGiro iban
  amount_ = int(definition_dict['COL_AMOUNT'])  # How much was the transaction
  currency_ = int(definition_dict['COL_CURRENCY'])
  balance_ = int(definition_dict['COL_BALANCE'])

  with open(csvfile_, newline='', mode='r', encoding='latin1') as csvfp:
    # create csv object using the given delimeter & quotechar
    csvIn = csv.reader(csvfp, delimiter=delimiter_, quotechar=quotechar_)

    # skip header line(s)
    for i in range(header_):
      next(csvIn, None)

    for row in csvIn:
      row[balance_] = convertDecimalComma(row[balance_])
      row[amount_] = convertDecimalComma(row[amount_])

      # Skip everything which is already processed in DeGiro transactions
      # skip all non-EURO transacions (as there will be also a line item in EUROs for same transaction)
      # skip all transacions with amount == 0
      if row[currency_] != "EUR" : continue
      if abs(float(row[amount_])) == 0: continue
      if not ( re.match( "^.*Aansluitingskosten.*$", row[memo_] ) or
               re.match("^.*Corporate Action Kosten.*$", row[memo_]) or
               re.match("^.*Geldmarktfondsen Compensatie.*$", row[memo_]) or
               re.match("^.*(Koersverandering|Conversie) geldmarktfonds.*$", row[memo_]) or
               re.match("^.*Dividend.*$", row[memo_]) or
#               re.match("^.*DEGIRO transactiekosten.*$", row[memo_]) or  # Already included via transactions
               re.match("^.*Valuta (Creditering|Debitering).*$", row[memo_])
             ) : continue

      # convert date to datetime format
      # Use second format if exception on first
      try:
        row[date_] = datetime.strptime(row[date_], dateformat1_)
      except ValueError:
        row[date_] = datetime.strptime(row[date_], dateformat2_)

      row[iban_] = sanitizeString(degiroIBAN, lowercase=True)

      csvlist.append({"date" : row[date_],
                      "transactiontype" : "Bank",
                      "iban" : row[iban_],
                      "sequence": 0,
                      "amount" : row[amount_],
                      "balance" : row[balance_],
                      "currency" : row[currency_],
                      "to_iban": "",
                      "payee": "DeGiro",
                      "memo" : row[memo_],
                      "category": ""
                      }.copy() )

  return 0



def readRabobankBeleggenCSV(csvfile_, definitionfile_, csvlist):
  """
  Parse Rabobank Beleggen (Investment) account CSV file

  Rabobank Investment account does only manage securities
  "Cash" balance (eg dividend payments) are immediately
  transferred to linked checking account.
  The format of the csv file is pretty hard to process,
  many exceptions afaik.
  The "cash" transactions are already part of the Rabo checking
  account csv file, and ignored by this parser/
  This parser will only process buy/sell of securities
  I have limited data to validate. Only "buy" is tested;
  "Sell" (verkoop internet) is implemented, but might be
  incorrect.

  TODO/FIX
  Implementation assumption is that security price currency is EUROS. This
  does not have to be true;

  Keyword arguments:
  :param str csvfile_: Path + Filename to bank csv file
  :param str definitionfile_:Path + Filename to definition file of bank
  :param list of dictionaries csvlist: list of dictionaries of parsed transactions csvlist
  """

  # definition of various fields in csv file; depends on bank
  definition_dict = readDefinitionFile(definitionfile_)

  # get cvs file format from definition_dict
  header_ = int(definition_dict['SKIPHEADERS'])  # How many header lines to skip?
  delimiter_ = definition_dict['DELIMITER'] #How the csv is separated
  quotechar_ = definition_dict['QUOTECHAR'] #quoatation chars of fileds

  date_ = int(definition_dict['COL_DATE']) # date of transaction
  dateformat1_ = definition_dict['DATEFORMAT1'] # strptime format string
  memo_ = int(definition_dict['COL_MEMO']) #discription of the transaction
  order_ = int(definition_dict['COL_SHARENAME'])  # opdracht
  isin_ = int(definition_dict['COL_ISIN'])
  iban_ = int(definition_dict['COL_IBAN'])
  quantity_ = int(definition_dict['COL_QUANTITY'])
  price_ = int(definition_dict['COL_PRICE'])
  amount_ = int(definition_dict['COL_AMOUNT'])  # How much was the transaction (qty * price)
  commission_ = int(definition_dict['COL_COMMISSION'])
  transfer_amount_ = int(definition_dict['COL_TOTAL']) # Total amount of transaction
  #currency_ = int(definition_dict['COL_PRICECURRENCY'])

  # Rabobank beleggen csv files truncates last colomns when empty
  # Rewrite csv file with constant nrof columns per row
  statement = list( csv.reader(fileinput.input(files=(csvfile_)), delimiter=delimiter_, quotechar=quotechar_) )
  maxFields = max( len(i) for i in statement )  # how many fields?

  # rewrite csv file with constant nrof columns
  with open(csvfile_, 'w') as f:
    print("\n".join([delimiter_.join(i + [""] * (maxFields - len(i))) for i in statement]), file=f)

  # start parsing csv file
  with open(csvfile_, newline='', mode='r', encoding='latin1') as csvfp:

    # create csv object using the given delimiter & quotechar
    csvIn = csv.reader(csvfp, delimiter=delimiter_, quotechar=quotechar_)

    # skip header line(s)
    for i in range(header_):
      next(csvIn, None)

    for row in csvIn:
      # convert date to datetime format
      row[date_] = datetime.strptime(row[date_], dateformat1_)

      # remove leading and trailing spaces; optionally convert to lowercase
      row[iban_] = sanitizeString(row[iban_], lowercase=True)

      # Convert numbers to decimal point
      row[transfer_amount_] = convertDecimalComma(row[transfer_amount_])
      row[price_] = convertDecimalComma(row[price_])
      row[quantity_] = convertDecimalComma(row[quantity_])
      row[amount_] = convertDecimalComma(row[amount_])

      # TODO
      # commision cost is not properly / complete implemented, will not
      # be categorized as such.
      # It will be calculated below for security buy/sell transactions
      # row[commission_] = convertDecimalComma(row[commission_])

      # "Sell"; "Buy"; "ShrsIn"; "ShrsOut" The latter 2 are not implemented
      if re.match( "^.*koop internet.*$", row[memo_].lower() ):
        action_ = "Buy"
      if re.match("^.*verkoop internet.*$", row[memo_].lower()):
        action_ = "Sell"

      # TODO: verkoop is not tested! Not sure if that is correct label in csv file
      # Parse when we sell or buy a security
      if re.match( "^.*koop internet.*$", row[memo_].lower() ) or \
         re.match("^.*verkoop internet.*$", row[memo_].lower()):

        a = abs(float(row[transfer_amount_]))
        b = abs(float(row[amount_]))
        row[commission_] = format( abs(a - b), '.2f')

        # Rabobank certificates are nominal value of E25,-
        # Rabobank uses nominal value iso units of E25
        # Convert to units of E25
        # BUT if you update online stock/fund prices, the RABO certificates
        # price is reported against nominal value of E100,-
        if row[isin_] == "XS1002121454":
          # uncomment if you want in units of E25
          #row[quantity_] = str(int(float(row[quantity_])/25))
          #row[price_] = str( float(row[price_])/4.0 )

          #  uncomment if you want in units of E100
          row[quantity_] = str(int(float(row[quantity_])/100))

        # It seems that:
        # amount = price * quantity + commission
        # my original erroneous assumption was that:
        # amount = price * quantity
        # transfer_amount = -(amount + commission)

        # positive number = BUY
        # negative number is SELL
        # Flip signs
        row[transfer_amount_] = str(-1.0 * (float(row[transfer_amount_])))

        # Fill csvlist
        csvlist.append({"date" : row[date_],
                        "transactiontype": "Invst",
                        "iban" : row[iban_],
                        "sequence" : 0,
                        "isin" : row[isin_],
                        "price" : row[price_],
                        "quantity" : row[quantity_],
                        #"amount" : row[amount_],
                        "amount": row[transfer_amount_],
                        "action" : action_,
                        "commission" : row[commission_],
                        "transfer_amount" : "",
                        "to_iban": "",
                        "payee" : "",
                        "category": "",
                        "memo" : row[memo_]  + " @ " + row[order_]  #+ " SEQ:" + row[sequence_]
                        }.copy() )

  return 0
