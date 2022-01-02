#!/usr/bin/python3
"""
Description
-----------

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

__version__ = "1.0.2"


import os
import sys
import quiffen

# local imports
import parsebank
import categories
from log import logger
import logging
# This setLevel determines which messages are passed on to lower handlers
logger.setLevel(logging.INFO)  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Todo fix
BASEPATH = os.path.dirname(os.path.realpath(__file__))



def close(exit_code):
  """
  Close application

  Keyword arguments:
  :param int exit_code: exit code of this application
   0 = success
  """
  logger.debug(f"INFO:close: exitcode = {exit_code} >>")
  sys.exit(exit_code)


def readBankAccounts(bankaccountsfilename):
  """
  Read from a definition file, all defined GnuCash accounts
  Format: "IBAN | GnuCash Account Name | !Type"
  See bankaccounts.def for more explanation

  Keyword arguments:
  :param str bankaccountsfilename: path + filename to <bankaccounts.def>
  :return dictionary of multiple key:value pairs --> account number:(gnucash account name, priority, qif account)
  :rtype dict
  """

  # key = id of back account (eg COL_IBAN)
  # value = tupple (GnuCash account name, priority between receiving account and sending account (l_ and r_)
  definition_dict = {}

  # priority for account when comparing
  # internal transfers, to prevent double
  # transfers in GnuCash
  # Prio = 0 is highest priority.
  prio = 0

  with open(bankaccountsfilename, newline='', mode='r') as fp:
    for line in fp:
      line = parsebank.sanitizeString(line)

      # strip comments & skip empty lines
      if line.startswith("#"): continue
      if len(line) == 0: continue

      (iban, accountname, accounttype) = line.split("|")
      iban = parsebank.sanitizeString(iban, lowercase=True)
      accountname = parsebank.sanitizeString(accountname)
      accounttype = parsebank.sanitizeString(accounttype)

      definition_dict[iban] = {"gnuaccountname": accountname,
                               "priority": prio,
                               "qifaccount": quiffen.Account(accountname,
                                                             desc='',
                                                             account_type=accounttype)}
      prio += 1

  return definition_dict


def writeQIF(account_dict_, csvlist, outfile_):
  """
  Write all transactions to a QIF formatted file

  Additional INFO
  https://www.w3.org/2000/10/swap/pim/qif-doc/QIF-doc.htm
  https://github.com/jemmyw/Qif/blob/master/QIF_references
  https://github.com/isaacharrisholt/quiffen/tree/main/quiffen

  Keyword arguments:
  :param dict account_dict_: key:value -->  iban:(gnucash account name, priority, qif account)
  :param list of dictionaries csvlist: list of dictionaries of parsed transactions
  :param str outfile_: filename of QIF file
  :return 0
  :rtype int
  """

  # list of transactions without categories
  listNoCategories = []

  # counter
  nrofTransactions = 0
  nrofNoCategories = 0
  nrofDoubleTransactions = 0

  # create qif instance to store accounts and transactions
  qif = quiffen.Qif()

# definition_dict[(key)] = {"gnuaccountname", "priority", "accounttype", "qifaccount"}

  # Create for every account defined in bankaccounts.def a qif account entry
  # Somehow it does not deal well with same entry twice (having 2 different account numbers pointing to same gnuaccountname).
  # Check if account is already created, if so, skip
  for key in account_dict_:
    accountname = account_dict_[key]["gnuaccountname"]

    # Entry already exists, skip
    if accountname in qif._accounts: continue
    else: qif.add_account(account_dict_[key]["qifaccount"])

  for transaction in csvlist:
    # If you have a transfer from account1 to account2 and
    # both accounts are a GnuCash account, and you download
    # statements for both accounts, you will end up with same
    # transaction twice in GnuCash:
    #   from account1 to account2 amount is X euros
    #   from account2 to account 1 amount is -X euros
    # Based on order (= priority) in bankaccounts.def,
    # if the accountFrom has a lower priority than accountTo,
    # transacion will be ignored, as the accountTo download will
    # add this transaction.

    # see below on priorities....
    try:
      iban = transaction['iban']
      accountFromPrio = account_dict_[iban]["priority"]
      accountToPrio = None
    except KeyError:
      logger.error(f"account {iban} is not defined in bankaccounts.def")
      close(1)


    # Process based on header_type. Only bank or invst are implemented
    header_type = transaction['transactiontype']
    if header_type == "Bank":
      tr = quiffen.Transaction(date = transaction['date'],
                               to_account = transaction['toaccountname'],
                               check_number = transaction['sequence'],
                               payee = transaction['payee'],
                               amount = transaction['amount'],
                               category= transaction['category'],
                               memo = transaction['memo'])

      # Determine priority for to account (if it exists) by looking up in account_dict_
      if len(transaction['to_iban']) > 0:
        for accountTo in account_dict_:
          if transaction['toaccountname'] == account_dict_[accountTo]['gnuaccountname']:
            accountToPrio = account_dict_[accountTo]["priority"]

      # print all transactions which don't have a defined category
      # Missing transactions/categories can optionally be added to categories.csv
      if transaction['category'] == quiffen.Category('Expenses:Imbalance-EUR'):
        listNoCategories.append(transaction)
        nrofNoCategories += 1

    # Process Invst transactions
    elif header_type == "Invst":
      tr = quiffen.Investment(date = transaction['date'],
                              action = transaction['action'],
                              security = transaction['isin'],
                              price = transaction['price'],
                              quantity = transaction['quantity'],
                              amount = transaction['amount'],
                              commission = transaction['commission'],
                              to_account = transaction['to_iban'],
                              transfer_amount = transaction['transfer_amount'],
                              memo = transaction['memo'])
    else:
      logger.error(f"Header_type {header_type} is not supported or implemented")
      close(0)


    #logger.debug(f""
    #            f"PRIO={accountFromPrio},{accountToPrio}; "
    #            f"IBAN={transaction['iban']}-->{transaction['to_iban']}||"
    #            f"ACC={transaction['fromaccountname']}-->{transaction['toaccountname']}||"
    #            f"PAYEE={transaction['payee']}||CAT = {transaction['category']}"
    #            f"||E={transaction['amount']}||M={transaction['memo']}")

    # Higher prio number means lowes priority
    if accountToPrio is not None and accountFromPrio > accountToPrio:
      nrofDoubleTransactions += 1
      continue

    # add transaction to account
    account_dict_[iban]["qifaccount"].add_transaction(tr, header = header_type)
    nrofTransactions += 1

  # Write qif file
  qif.to_qif(outfile_)

  sortedlist = sorted( listNoCategories, key=lambda x: x['memo'].lower() )
  for transaction in sortedlist:
    logger.info(f"TRANSACTION without category: {transaction['iban']}|{transaction['memo']}")

  logger.info(f"Converted {nrofTransactions} transactions to QIF; Skipped {nrofDoubleTransactions} duplicate transactions; {nrofNoCategories} transactions are not categorized")

  return 0


def main(listoffiles_, outfile_):
  """
  main

  Keyword arguments:
  :param list of str listoffiles_: Path + Filename to bank csv file(s)
  :param str outfile_: filename of QIF formatted output file
  """

  for file in listoffiles_:
    logger.debug(f"main: IN={file} OUT={outfile_}")

  # detect bankdefinitionfiles
  parsebank.queryBankDefFiles()

  # read which GnuCash accounts exists
  # dictionary of multiple key:value pairs --> account number:(gnucash account name, priority, qif account)
  account_dict = readBankAccounts(BASEPATH + "/bankaccounts.def")

  # read category regex; to format payee & categories
  category_regex = categories.readCategory(BASEPATH + "/categories.csv")

  csvlist = []
  # start processing csv files....

  for file in infile:
    # determine which bank and csvparser matches the csv file
    (bankdefinitionfile, csvparser) = parsebank.determineBank(file)

    # if determineBank does not find a matching bank, NONE is returned
    if bankdefinitionfile == "NONE":
      logger.error(f"CSV file: {file} is not recognized, exiting.....")
      close(0)

    # if determineBank does not find a matching bank, NONE is returned
    if bankdefinitionfile == "DUPLICATE":
      logger.error(f"CSV file: {file} matches multiple bank parsers - change fingerpint, exiting.....")
      close(0)

    # read csv's with a bank definition file
    # return list to store account csv file

    # check first if parser exists w/o calling it
    if hasattr(parsebank, csvparser):
      getattr(parsebank, csvparser)(file, bankdefinitionfile, csvlist)
    else:
      logger.error(f"Parser parsebank.{csvparser} defined in {bankdefinitionfile} does not exist")
      close(0)


  # translate IBAN's to GnuCash account names
  categories.determineAccountNames(account_dict, csvlist)

  # determine the category of the transaction for every transaction in the csv list
  categories.determineCategories(csvlist, category_regex)

  # translate IBAN's to GnuCash account names; after categories are assigned
  # A category can be same as accounttoname, hence needs to  be copied back
  categories.determineAccountNames(account_dict, csvlist)

  # write the QIF file
  writeQIF(account_dict, csvlist, outfile_)

  logger.info("main: <<")
  return
# END def main()


"""
------------------------------------------------------------------------------------
 Entry point
------------------------------------------------------------------------------------

Read command line arguments
- csv2qif.py file1.csv
output: file1.qif

- csv2qif.py file1.csv file2.csv file3.csv
output: out.qif
"""
if __name__ == '__main__':
  logger.debug("__main__: >>")
  logger.info(f"Starting csv2qif version {__version__}")

  # list of input csv files
  infile = []

  try:
    nrofArguments = len(sys.argv) - 1

    # if there are no arguments passed at command line
    if nrofArguments == 0:
      raise FileNotFoundError

    # add csv file to list
    for i in range(nrofArguments):
      infile.append( sys.argv[i+1] )

      # check if file exists; bail out if one is missing
      if not os.path.isfile( infile[i] ):
        logger.error(f"File {infile[i]} does not exist")
        raise FileNotFoundError

    # if only one csv file is specified, the out file will use the basename of the inputfile
    # if multiple csv files are specified, output is written to out.qif
    if nrofArguments == 1:
      outfile = os.path.splitext(infile[0])[0] + ".qif"
    else:
      outfile = "out.qif"

  except:
    logger.info(f"usage {os.path.basename(sys.argv[0])} <file1.csv> <file2.csv>")
    logger.info(f"usage {os.path.basename(sys.argv[0])} <*.csv>")

    # work around to test from IDE or without specifying
    # csv file om commandline
    # Default False
    #if True:
    if False:
      #infile.append(BASEPATH + "/test/INGSAVING.csv")
      #infile.append(BASEPATH + "/test/INGCHECKING.csv")
      infile.append(BASEPATH + "/test/degiro_transactions.csv")
      #infile.append(BASEPATH + "/test/degiro_account.csv")
      #infile.append(BASEPATH + "/test/RABOHANSBELEGGEN.csv")
      outfile = "out.qif"
    else:
      infile.append(BASEPATH + "/csv/INGCHECKING.csv")
      outfile = "out.qif"

    #logger.info(f"Use defaults: \nINPUT = {infile} \nOUTPUT = {outfile}")

  logger.info(f"Use defaults: \nINPUT = {infile} \nOUTPUT = {outfile}")
  main(infile, outfile)
  close(0)
