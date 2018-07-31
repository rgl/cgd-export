#!/usr/bin/python3
# Developed by Rui Lopes (ruilopes.com). Released under the LGPLv3 license.

from pprint import pprint
from urllib.parse import quote
import argparse
import datetime
import json
import logging
import requests
import textwrap
import urllib

class CgdClient:
    _base_url = 'https://app.caixadirecta.cgd.pt/cdoAppsAPI/rest/v1/'

    _default_headers = {
        'User-Agent': 'Mozilla/5.0',
        'X-CGD-APP-Device': 'as3',
        'X-CGD-APP-Version': '1.0',
        'X-CGD-APP-Language': 'pt-PT'}

    def __init__(self):
        self._session = None
        self._full_account_key = None

    def login(self, username, password):
        self._close_session()
        session = requests.Session()
        session.headers.update(CgdClient._default_headers)
        self._session = session
        r = self._session.post(
            CgdClient._base_url + 'system/security/authentications/basic',
            params={
                'u': username,
                'includeAccountsInResponse': 'true'},
            auth=(username, password))
        if r.status_code != 200:
            raise Exception('login status code %s: %s' % (r.status_code, r.text))
        response = r.json()
        logging.info('account customer %s', response['customerName'])
        accounts = response['accounts']
        if len(accounts) != 1:
            raise Exception('sorry, this only supports a username with a single account')
        account = accounts[0]
        logging.info('account type %s', account['accountType'])
        logging.info('account description %s', account['description'])
        logging.info('account iban %s', account['iban'])
        self._full_account_key = account['fullAccountKey']

    def logout(self):
        r = self._session.delete(
            CgdClient._base_url + 'system/security/authentications/current')
        if r.status_code != 200:
            raise Exception('logout status code %s: %s' % (r.status_code, r.text))
        self._close_session()

    def _close_session(self):
        if self._session:
            self._session.close()
            self._session = None

    def get_account_balance(self):
        r = self._session.get(
            CgdClient._base_url + ('business/accounts/%s/balances' % quote(self._full_account_key)))
        if r.status_code != 200:
            raise Exception('get_account_balance status code %s: %s' % (r.status_code, r.text))
        response = r.json()
        return response

    def get_account_transactions(self):
        # NB only the last two years are normally available.
        from_book_date = '2000-01-01'
        to_book_date = (datetime.datetime.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        page_key = None
        while True:
            r = self._session.get(
                CgdClient._base_url + ('business/accounts/%s/transactions' % quote(self._full_account_key)),
                params={
                    'fromBookDate': from_book_date,
                    'toBookDate': to_book_date,
                    'sort': '+bookDate',
                    'pageKey': page_key})
            if r.status_code != 200:
                raise Exception('get_account_transactions status code %s: %s' % (r.status_code, r.text))
            response = r.json()
            page_key = response['nextPageKey']
            for transaction in response['transactions']:
                if 'details' in transaction:
                    raise Exception('ops... details is in the transaction object with id %s' % transaction['transactionId'])
                transaction['details'] = self._get_account_transaction_details(transaction['transactionId'])
                yield transaction
            if not page_key:
                break

    def _get_account_transaction_details(self, id):
        r = self._session.get(
            CgdClient._base_url + ('business/accounts/%s/transactions/%s' % (
                quote(self._full_account_key),
                quote(id))))
        if r.status_code != 200:
            raise Exception('_get_account_transaction_details status code %s: %s' % (r.status_code, r.text))
        response = r.json()
        return response

    def get_documents(self):
        c = self._get_document_configurations()
        # NB only the last two years are normally available.
        from_date = c['minimumDate']
        to_date = (datetime.datetime.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%dT00:00:00Z')
        page_key = None
        while True:
            r = self._session.get(
                CgdClient._base_url + 'business/documents',
                params={
                    'fromDate': from_date,
                    'toDate': to_date,
                    'pageKey': page_key})
            if r.status_code != 200:
                raise Exception('get_documents status code %s: %s' % (r.status_code, r.text))
            response = r.json()
            page_key = response['nextPageKey']
            for document in response['documents']:
                if 'contents' in document:
                    raise Exception('ops... contents is in the document object with id %s' % document['documentId'])
                document['contents'] = self._get_document_contents(document['documentId'])
                yield document
            if not page_key:
                break

    def _get_document_configurations(self):
        r = self._session.get(
            CgdClient._base_url + 'business/documents/configurations')
        if r.status_code != 200:
            raise Exception('_get_document_configurations status code %s: %s' % (r.status_code, r.text))
        response = r.json()
        return response

    def _get_document_contents(self, id):
        r = self._session.get(
            CgdClient._base_url + ('business/documents/%s/contents' % (
                quote(id))))
        if r.status_code != 200:
            raise Exception('_get_document_contents status code %s: %s' % (r.status_code, r.text))
        response = r.json()
        return response['documentContents']

def transactions_main(client, args):
    for t in client.get_account_transactions():
        if logging.root.isEnabledFor(logging.INFO):
            if t['transactionType'] == 'Credit':
                amount = '%.2f+' % (t['amount'] / 100.0)
            else:
                amount = '%.2f-' % (t['amount'] / 100.0)
            logging.info('transaction %s %10s %s', t['valueDate'], amount, t['description'])
        print(json.dumps(t))

def documents_main(client, args):
    for d in client.get_documents():
        logging.info('document %s %s', d['issueDate'], d['name'])
        print(json.dumps(d))

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=textwrap.dedent('''\
        exports data from a CGD account

        example:
          python3 %(prog)s -v transactions 123456 678901 >transactions.json
          python3 %(prog)s -v documents    123456 678901 >documents.json
        '''))
parser.add_argument(
    '--verbose',
    '-v',
    default=0,
    action='count',
    help='verbosity level. specify multiple to increase logging.')
subparsers = parser.add_subparsers(help='sub-command help')
transactions_parser = subparsers.add_parser('transactions', help='export all available transactions')
transactions_parser.set_defaults(sub_command=transactions_main)
documents_parser = subparsers.add_parser('documents', help='export all available documents')
documents_parser.set_defaults(sub_command=documents_main)
parser.add_argument(
    'username',
    type=str,
    help='account username')
parser.add_argument(
    'password',
    type=str,
    help='account password')
args = parser.parse_args()

LOGGING_FORMAT = '%(asctime)-15s %(levelname)s %(name)s: %(message)s'
if args.verbose >= 3:
    logging.basicConfig(level=logging.DEBUG, format=LOGGING_FORMAT)
    from http.client import HTTPConnection
    HTTPConnection.debuglevel = 1
elif args.verbose >= 2:
    logging.basicConfig(level=logging.DEBUG, format=LOGGING_FORMAT)
elif args.verbose >= 1:
    logging.basicConfig(level=logging.INFO, format=LOGGING_FORMAT)

client = CgdClient()

client.login(args.username, args.password)

if logging.root.isEnabledFor(logging.INFO):
    balance = client.get_account_balance()
    for b in balance['accountBalancesList']:
        logging.info('account balance %.2f %s',
            b['bookBalance'] / 100.0,
            b['currency'])

args.sub_command(client, args)

client.logout()
