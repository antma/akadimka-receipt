#!/usr/bin/python3
# -*- coding: UTF8 -*-

#standard python modules
import argparse
import csv
import logging
import sys

#project
import git
import log
import pdf_utils
import schema
import tsv

class ExplicitDefaultsHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
  """
  https://stackoverflow.com/a/67208041
  It is often useful to be able to automatically include the default values in the help output,
  but only those that were explicitly specified (with default=..).
  """
  def _get_help_string(self, action):
    return action.help if (action.default is None) or (action.default is False) \
                       else super()._get_help_string(action)

def parse_options():
  argument_parser = argparse.ArgumentParser(
    description = 'Converts table from one page PDF to CSV with custom schema',
    formatter_class=ExplicitDefaultsHelpFormatter)
  argument_parser.add_argument('-o', '--output', metavar = 'FILE', help = 'set output filename')
  argument_parser.add_argument('-l', '--log', metavar = 'FILE', help = 'set log filename, if not given log to STDOUT')
  argument_parser.add_argument('-t', '--tmp_tsv', default = 'out.tsv', metavar = 'FILE', help = 'set temporary TSV filename')
  argument_parser.add_argument('--debug', action = 'store_true', help = 'enable debug logging')
  argument_parser.add_argument('input_filename')
  return argument_parser.parse_args()

def main():
  args = parse_options()
  logging_level = logging.INFO
  if args.debug:
    logging_level = logging.DEBUG
  log.init_logging(args.log, logging_level)
  git_commit_hash = git.hash_version()
  if not git_commit_hash is None:
    logging.info(f'Script version: {git_commit_hash}')
  extraction_schema = schema.load('schema.csv')
  if extraction_schema is None:
    sys.exit(1)
  if pdf_utils.pdf_to_tsv(args.input_filename, args.tmp_tsv) != 0:
    logging.critical(f'Can not convert "{args.input_filename}" PDF file to TSV format.')
    sys.exit(1)
  rl = tsv.read_and_parse(args.tmp_tsv)
  if args.output is None:
    d = rl.first_strdate()
    if d is None:
      logging.warning(f'Date was not found in PDF file "{args.input_filename}"')
      default_output_file = 'out.csv'
      args.output = default_output_file
    else:
      args.output = d + '.csv'
  logging.info(f'Writing CSV data to "{args.output}" file')
  with open(args.output, 'w', newline='', encoding = 'UTF8') as csvfile:
    writer = csv.writer(csvfile, delimiter=' ', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    for (name, columns) in extraction_schema:
      rl.export_row(writer, name, columns)

main()
