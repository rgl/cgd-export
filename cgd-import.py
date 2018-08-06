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

def transactions_main(args):
    with open('transactions.json') as f:
        for line in f:
            t = json.loads(line)
            if logging.root.isEnabledFor(logging.INFO):
                if t['transactionType'] == 'Credit':
                    amount = '%.2f+' % (t['amount'] / 100.0)
                else:
                    amount = '%.2f-' % (t['amount'] / 100.0)
                logging.info('importing transaction %s %10s %s', t['valueDate'], amount, t['description'])
            r = requests.put(
                'http://localhost:9200/transactions/_doc/%s' % quote(t['transactionId']),
                json=t)
            if r.status_code not in (200, 201):
                raise Exception('failed to import transactionId %s status code %s: %s' % (t['transactionId'], r.status_code, r.text))

def documents_main(args):
    with open('documents.json') as f:
        for line in f:
            d = json.loads(line)
            logging.info('importing document %s %s', d['issueDate'], d['name'])
            r = requests.put(
                'http://localhost:9200/documents/_doc/%s?pipeline=document' % quote(d['documentId']),
                json=d)
            if r.status_code not in (200, 201):
                raise Exception('failed to import documentId %s status code %s: %s' % (d['documentId'], r.status_code, r.text))

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=textwrap.dedent('''\
        imports data from local json documents into Elasticsearch

        example:
          python3 %(prog)s -v transactions
          python3 %(prog)s -v documents
        '''))
parser.add_argument(
    '--verbose',
    '-v',
    default=0,
    action='count',
    help='verbosity level. specify multiple to increase logging.')
subparsers = parser.add_subparsers(help='sub-command help')
transactions_parser = subparsers.add_parser('transactions', help='import transactions.json')
transactions_parser.set_defaults(sub_command=transactions_main)
documents_parser = subparsers.add_parser('documents', help='import documents.json')
documents_parser.set_defaults(sub_command=documents_main)
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

args.sub_command(args)
