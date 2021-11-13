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


# logging
import __main__
import logging
import os

script=os.path.basename(__main__.__file__)
script=os.path.splitext(script)[0]
logger = logging.getLogger(script + "." +  __name__)

import re
import quiffen
import csv


def determineAccountNames(account_dict_, csvlist_):
  """
  Determine GnuCashAccountName from account number (typically IBAN)
  For total list of transactions

  Keyword arguments:
  :param dict account_dict_: key:value -->  iban:(gnucash account name, priority, qif account)
  :param list of dictionaries csvlist: list of dictionaries of transactions
  """

  for transaction in csvlist_:
    try:
      transaction['fromaccountname'] = account_dict_[ transaction['iban'] ]['gnuaccountname']
    except:
      transaction['fromaccountname'] = ""

    try:
      transaction['toaccountname'] = account_dict_[ transaction['to_iban'] ]['gnuaccountname']
    except:
      transaction['toaccountname'] = ""

    # Check if a category is defined
    # Check if category matches a GnuCash account
    # Copy to iban_to and accounttoname
    if transaction['category'] != "":
      to_iban = getIBAN(account_dict_, transaction['category'].name)
      if to_iban != 0:
        transaction['to_iban'] = to_iban
        transaction['toaccountname'] = transaction['category'].name

  return 0


def getIBAN(account_dict_, gnucashaccountname_):
  """
  Return account number (typically IBAN) for a given GnuCashAccountName

  Keyword arguments:
  :param dict account_dict_: key:value -->  iban:(gnucash account name, priority, qif account)
  :param str gnucashaccountname_:
  :return account number (IBAN)
  :rtype str
  """

  for account in account_dict_:
    if account_dict_[account]['gnuaccountname'] == gnucashaccountname_:
      return account

  return 0


def determineCategories(csvlist_, category_regex):
  """
  Determine category for all transactions, based on regex defined in accounts.csv

  Keyword arguments:
  :param list of dictionaries csvlist: list of dictionaries of transactions
  :param list of dictionaries category_regex: list of dictionaries regular expressions for payee and memo
  """

  for transaction in csvlist_:
    # Try to determine category when to account is not a GnuCash account
    if transaction['toaccountname'] == "":
      determineCategory(transaction, category_regex)

  return 0


def determineCategory(csv, category_regex):
  """
  Determine category for one transactions, based on regex defined in accounts.csv

  Keyword arguments:
  :param dictionary csv: transaction
  :param list of dictionaries category_regex: list of dictionaries regular expressions for payee and memo
  :return updated transaction (csv)
  :rtype dictionary
  """

# TODO
# also add check regex payee AND MEMO

  for dict in category_regex:
    # only try to match of there is a payee

    regex = dict["payeeregex"].lower()
    # check if payee is defined and regex is defined
    if len(csv["payee"]) > 0 and len(regex) > 0 and re.match(regex, csv["payee"].lower()):
      # append payee to memo before payee is modified
      csv["memo"] = csv["payee"] + "||" + csv["memo"]
      csv["payee"] = dict["payee"]

      # add quiffen category
      csv["category"] = quiffen.Category(dict["category"])

      # break from loop as a match has been made
      break

    # only try to match of there is a memo
    regex = dict["memoregex"].lower()
    # check if memo is defined and regex is defined
    if len(csv["memo"]) > 0 and len(regex) > 0 and re.match(regex, csv["memo"].lower()):
      # append payee to memo before payee is modified
      csv["memo"] = csv["payee"] + "||" + csv["memo"]

      # Update payee if one is prescribed
      if len(dict["payee"]) > 0:
        csv["payee"] = dict["payee"]

      # add quiffen category
      csv["category"] = quiffen.Category( dict["category"] )

      # break from loop as a match has been made
      break

  return csv



# ------------------------------------------------------------------------------------
#
#
# ------------------------------------------------------------------------------------
def readCategory(categoryscv):
  """
  Read all regex from categories file

  Keyword arguments:
  :param str categoryscv: filename csv file with all category regex-es.
  :return list of dictionaries regular expressions for payee and memo
  :rtype list of dictionaries
  """

  category_regex = []
  category_dict = {}

  with open(categoryscv, newline='', mode='r', encoding='latin1') as csvfp:
    csvIn = csv.reader(csvfp, delimiter=",")  # create csv object using the given separator

    # skip header line
    next(csvIn, None)

    for row in csvIn:
      category_dict.clear()
      category_dict["payee"] = row[0]
      category_dict["category"] = row[1]
      category_dict["payeeregex"] = row[2]
      category_dict["memoregex"] = row[3]
      category_regex.append(category_dict.copy())

  return category_regex



