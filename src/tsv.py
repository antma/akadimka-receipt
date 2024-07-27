# -*- coding: UTF8 -*-
"""
разбор файлов в формате tsv, полученных от утилиты pdftotext, согласно заданной схемы
"""
from collections import defaultdict
import csv
import logging
import re

import schema

#https://ru.stackoverflow.com/questions/810304/Как-вывести-названия-месяцев-без-склонения-в-calendar
_RU_MONTHS = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

def get_month_by_id(month):
  if 1 <= month <= 12: return _RU_MONTHS[month-1]
  return None

class Row:
  def __init__(self, columns, row):
    for (key, value) in zip(columns, row):
      setattr(self, key, value)
  def __str__(self):
    return str(vars(self))

def _lines_text(line):
  return ' '.join(map(lambda x: x.text, line))
def _lines_debug(line):
  return ' '.join(map(str, line))
def _lines_with_attr(line, attr):
  return ' '.join(map(lambda x: f'{x.text}({getattr(x, attr)})', line))

class NumberRecognizer:
  def __init__(self):
    self.re_number = re.compile(r'-?\d{1,10}((\.|,)\d{0,6})?')
    self.months = dict(map(lambda x: (x[1], x[0] + 1), enumerate(_RU_MONTHS)))
    self.re_year = re.compile(r'20\d\d')
  def is_number(self, s):
    return (s == '-') or (not self.re_number.fullmatch(s) is None)
  def get_month_number(self, s):
    """
    >>> NumberRecognizer().get_month_number('Май')
    5
    """
    return self.months.get(s)
  def is_year(self, s):
    """
    >>> NumberRecognizer().is_year('2024')
    True
    >>> NumberRecognizer().is_year('20245')
    False
    >>> NumberRecognizer().is_year('1980')
    False
    """
    logging.debug(f'is_year(): s = {s}')
    return not self.re_year.fullmatch(s) is None

def contains_digits(s):
  return any(map(lambda x: x.isdigit(), s))

class _Line:
  def _add_number(self, s):
    self.numbers.append(s.replace('.', ','))
  def __init__(self, rows, nr, parse_date):
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
    if parse_date:
      self.date = None
      for i in range(1, len(rows)):
        year = rows[i].text
        if nr.is_year(year):
          month = nr.get_month_number(rows[i-1].text)
          if not month is None:
            self.date = (int(year), month)
            break
  def _startswith(self, s):
    return self.name.startswith(s)
  def matched(self, s):
    """ ' / ' в названии строчки s используется как один из вариантов (содержание газонов или уборка снега) """
    return any(map(lambda t: self._startswith(t), s.split(' / ')))
  def extract(self, columns):
    max_idx = max(columns)
    if max_idx >= len(self.numbers):
      logging.debug(f'Can not extract {columns} from {self.numbers} for {self.name}.')
      return None
    a = []
    for idx in columns:
      a.append('' if idx < 0 else self.numbers[idx])
    return a

class ReceiptLines:
  def __init__(self):
    self.nr = NumberRecognizer()
    self.first_date = None
    self._lines = []
  def first_strdate(self):
    d = self.first_date
    if d is None:
      return 'unknown'
    return f'{d[0]}-{d[1]:02d}'
  def add_line(self, rows):
    l = _Line(rows, self.nr, self.first_date is None)
    if (self.first_date is None) and (not l.date is None):
      self.first_date = l.date
    self._lines.append(l)
  def get_numbers(self, name, columns):
    for l in self._lines:
      if not l.matched(name): continue
      r = l.extract(columns)
      if not r is None:
        return r
    return None
  def _export_row(self, writer, name, columns):
    n = self.get_numbers(name, columns)
    if n is None:
      logging.warning(f'row "{name}" is broken in {self.first_strdate()}')
      n = ['?' for _ in columns]
    n.insert(0, name)
    writer.writerow(n)
  def export_csv(self, csvfile, extraction_schema: schema.ExtractionSchema):
    writer = csv.writer(csvfile, delimiter=' ', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    for (name, units, columns) in extraction_schema.rows:
      self._export_row(writer, name, columns)

def _group_by(rows, attr):
  d = defaultdict(list)
  for row in rows:
    d[getattr(row, attr)].append(row)
  for i, a in d.items():
    logging.debug(f'{attr} #{i}: {_lines_text(a)}')
    logging.debug(f'{attr} #{i}: {_lines_with_attr(a, "line_num")}')
    logging.debug(f'{attr} #{i}: {_lines_with_attr(a, "left")}')
    #logging.debug('{} #{}: {}'.format(attr, i, lines_debug(a)))
  return d

def _csv_readall(reader):
  #level page_num par_num block_num line_num word_num left top width height	conf text
  columns = next(reader)
  logging.debug(f'columns = {columns}')
  rows = []
  for row in reader:
    o = Row(columns, row)
    rows.append(o)
  return rows

def _read(input_filename):
  with open(input_filename, newline='', encoding = 'UTF8') as f:
    reader = csv.reader(f, delimiter = '\t')
    return _csv_readall(reader)

def read_and_parse(input_filename):
  rows = _read(input_filename)
  rl = ReceiptLines()
  for group in _group_by(rows, 'top').values():
    rl.add_line(group)
  return rl

if __name__ == "__main__":
  import doctest
  doctest.testmod(verbose=True)
