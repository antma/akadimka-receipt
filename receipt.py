#!/usr/bin/python3
# -*- coding: UTF8 -*-

from collections import defaultdict
import argparse
import csv
import logging
import os
import re
import subprocess
import sys

POPPLER_BIN = ''

def pdf_to_tsv(input_filename, output_filename):
  command = [os.path.join(POPPLER_BIN, 'pdftotext'), '-tsv', input_filename, output_filename]
  logging.info(f'Running command {command}')
  r = subprocess.run(command, check = False)
  logging.info(f'pdftotext returns {r.returncode} code')
  return r.returncode

class Row:
  def __init__(self, columns, row):
    for (key, value) in zip(columns, row):
      setattr(self, key, value)
  def __str__(self):
    return str(vars(self))

def lines_text(line):
  return ' '.join(map(lambda x: x.text, line))
def lines_debug(line):
  return ' '.join(map(str, line))
def lines_with_attr(line, attr):
  return ' '.join(map(lambda x: f'{x.text}({getattr(x, attr)})', line))

class NumberRecognizer:
  def __init__(self):
    self.re_number = re.compile(r'\d{1,10}((\.|,)\d{0,6})?')
  def is_number(self, s):
    return not self.re_number.fullmatch(s) is None

def contains_digits(s):
  return any(map(lambda x: x.isdigit(), s))

class Line:
  def _add_number(self, s):
    self.numbers.append(s.replace('.', ','))
  def __init__(self, rows, nr):
    #state: 0 (читаем название), 1 (читаем числа)
    state = 0
    names = []
    self.numbers = []
    rows.sort(key = lambda x: float(x.left))
    for row in rows:
      s = row.text
      if state == 0:
        if contains_digits(s):
          state = 1
          if nr.is_number(s):
            self._add_number(s)
        else: names.append(s)
      else:
        if nr.is_number(s):
          self._add_number(s)
    self.name = ' '.join(names)
  def startswith(self, s):
    return self.name.startswith(s)

class ReceiptLines:
  def __init__(self):
    self.nr = NumberRecognizer()
    self.lines_with_at_least_3_numbers = []
    self.lines_with_at_least_4_numbers = []
  def add_line(self, rows):
    l = Line(rows, self.nr)
    nc = len(l.numbers)
    if nc >= 3:
      self.lines_with_at_least_3_numbers.append(l)
    if nc >= 4:
      self.lines_with_at_least_4_numbers.append(l)
  def get_numbers(self, name, columns):
    l = self.lines_with_at_least_3_numbers if columns == 3 \
        else self.lines_with_at_least_3_numbers
    try:
      p = next(filter(lambda x: x.startswith(name), l))
      return p.numbers
    except StopIteration:
      return None
  def export_row(self, writer, name, columns):
    n = self.get_numbers(name, columns)
    assert((n is None) or (len(n) >= columns))
    if n is None:
      logging.warning(f'row "{name}" is broken')
      t = (name, '-', '-', '-', '-')
    else:
      if len(n) > columns:
        logging.warning(f'row "{name}" contains more numbers ({len(n)}) then expected ({columns}). Please, recheck it manually.')
      if columns == 3:
        t = (name, n[0], '-', n[1], n[2])
      else:
        t = (name, n[0], n[1], n[2], n[3])
    writer.writerow(t)

def group_by(rows, attr):
  d = defaultdict(list)
  for row in rows:
    d[getattr(row, attr)].append(row)
  for i, a in d.items():
    logging.debug(f'{attr} #{i}: {lines_text(a)}')
    logging.debug(f'{attr} #{i}: {lines_with_attr(a, "line_num")}')
    logging.debug(f'{attr} #{i}: {lines_with_attr(a, "left")}')
    #logging.debug('{} #{}: {}'.format(attr, i, lines_debug(a)))
  return d

def csv_readall(reader):
  #level page_num par_num block_num line_num word_num left top width height	conf text
  columns = next(reader)
  logging.debug(f'columns = {columns}')
  rows = []
  for row in reader:
    o = Row(columns, row)
    rows.append(o)
    #logging.debug(o)
  return rows

def read_tsv(input_filename):
  with open(input_filename, newline='', encoding = 'UTF8') as f:
    reader = csv.reader(f, delimiter = '\t')
    return csv_readall(reader)

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
  argument_parser.add_argument('-o', '--output', default = 'out.csv', metavar = 'FILE', help = 'set output filename')
  argument_parser.add_argument('-l', '--log', metavar = 'FILE', help = 'set log filename, if not given log to STDOUT')
  argument_parser.add_argument('-t', '--tmp_tsv', default = 'out.tsv', metavar = 'FILE', help = 'set temporary TSV filename')
  argument_parser.add_argument('--debug', action = 'store_true', help = 'enable debug logging')
  argument_parser.add_argument('input_filename')
  return argument_parser.parse_args()

def load_schema(filename):
  a = []
  with open(filename, 'r', newline='', encoding = 'UTF8') as csvfile:
    reader = csv.reader(csvfile, delimiter=' ', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    header = next(reader)
    if header != ['name', 'columns']:
      logging.error('load_schema: schema header mismatched')
      return None
    for line, t in enumerate(reader):
      if len(t) != 2:
        logging.error(f'load_schema: expected exactly 2 fields in a row (file: "{filename}", line {line+2})')
        return None
      try:
        cols = int(t[1])
      except ValueError as err:
        logging.error(f'load_schema: can not convert columns number to integer (file: "{filename}", line {line+2}, error "{err}")')
        return None
      if (cols < 3) or (cols > 4):
        logging.error(f'load_schema: number of columns could be only 3 or 4 (file: "{filename}", line {line+2})')
        return None
      a.append((t[0], cols))
  return a

def init_logging(log_filename, logging_level):
  fmt = '%(asctime)s %(levelname)s %(message)s'
  if log_filename is None:
    logging.basicConfig(level=logging_level, format=fmt, stream=sys.stdout)
  else:
    logging.basicConfig(level=logging_level, format=fmt, filename=log_filename, filemode='w')

def main():
  args = parse_options()
  logging_level = logging.INFO
  if args.debug:
    logging_level = logging.DEBUG
  init_logging(args.log, logging_level)
  schema = load_schema('schema.csv')
  if schema is None:
    sys.exit(1)
  if not os.path.lexists(args.input_filename):
    logging.critical(f'File "{args.input_filename}" not found.')
    sys.exit(1)
  if pdf_to_tsv(args.input_filename, args.tmp_tsv) != 0:
    logging.critical(f'Can not convert "{args.input_filename}" PDF file to TSV format.')
    sys.exit(1)
  rows = read_tsv(args.tmp_tsv)
  rl = ReceiptLines()
  for group in group_by(rows, 'top').values():
    rl.add_line(group)
  with open(args.output, 'w', newline='', encoding = 'UTF8') as csvfile:
    writer = csv.writer(csvfile, delimiter=' ', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    for (name, columns) in schema:
      rl.export_row(writer, name, columns)

main()
