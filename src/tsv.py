# -*- coding: UTF8 -*-
"""
разбор файлов в формате tsv, полученных от утилиты pdftotext, согласно заданной схемы
"""
from collections import defaultdict
import csv
import json
import logging
import re
from typing import Optional, Union
from datetime import datetime

#import schema
import pandas as pd

#https://ru.stackoverflow.com/questions/810304/Как-вывести-названия-месяцев-без-склонения-в-calendar
_RU_MONTHS = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

def get_month_by_id(month):
  if 1 <= month <= 12:
    return _RU_MONTHS[month-1]
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
  def parse_number(self, s: str) -> Optional[Union[float,str]]:
    if s == '-':
      return s
    if (self.re_number.fullmatch(s) is None):
      return None
    return float(s.replace(',', '.'))
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
  """depricated"""
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
    return any(map(self._startswith, s.split(' / ')))
  def extract(self, columns):
    max_idx = max(columns)
    if max_idx >= len(self.numbers):
      logging.debug(f'Can not extract {columns} from {self.numbers} for {self.name}.')
      return None
    a = []
    for idx in columns:
      a.append('' if idx < 0 else self.numbers[idx])
    return a

class _ReceiptLines:
  def __init__(self):
    self.nr = NumberRecognizer()
    self.first_date = None
    self._lines = []
  def add_line(self, data):
    state = 0
    #state: 0 (читаем название), 1 (читаем числа)
    #числа или float, либо cтрока '-' означающая отсутствие данных
    names = []
    data.sort(key = lambda x: float(x.left))
    numbers = []
    nr = self.nr
    for row in data:
      s = row.text
      if state == 0:
        if (s == '-') or contains_digits(s):
          state = 1
          x = nr.parse_number(s)
          if not x is None:
            numbers.append(x)
        else: names.append(s)
      else:
        x = nr.parse_number(s)
        if not x is None:
          numbers.append(x)
    name = ' '.join(names)
    if self.first_date is None:
      self.date = None
      for i in range(1, len(data)):
        year = data[i].text
        if nr.is_year(year):
          month = nr.get_month_number(data[i-1].text)
          if not month is None:
            self.first_date = (int(year), month)
            break
    if len(name) > 0:
      self._lines.append((name, numbers))
  def first_strdate(self):
    d = self.first_date
    if d is None:
      return 'unknown'
    return f'{d[0]}-{d[1]:02d}'
  def get_numbers(self, name, columns):
    for l in self._lines:
      if not l.matched(name):
        continue
      r = l.extract(columns)
      if not r is None:
        return r
    return None
  '''
  def _export_row(self, writer, name, columns):
    n = self.get_numbers(name, columns)
    if n is None:
      logging.warning(f'row "{name}" is broken in {self.first_strdate()}')
      n = ['?' for _ in columns]
    n.insert(0, name)
    writer.writerow(n)
  def export_csv(self, csvfile, extraction_schema: schema.ExtractionSchema):
    writer = csv.writer(csvfile, delimiter=' ', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    for (name, _units, columns) in extraction_schema.rows:
      self._export_row(writer, name, columns)
  '''

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

def load_json_configuration(json_configuration_filename):
  with open(json_configuration_filename) as f:
    return json.load(f)

def read_and_parse(input_filename, configuration_from_json):
  d = configuration_from_json
  rows = _read(input_filename)
  rl = _ReceiptLines()
  for group in _group_by(rows, 'top').values():
    rl.add_line(group)
  series = []
  assert(len(rl._lines) > 0)
  logging.debug("Found %d interesting lines in file '%s'.", len(rl._lines), input_filename)
  #print(d['rows'])
  logging.debug("Found %d rows in json configuration.", len(d['rows']))
  #самая тупая реализация за квадрат
  for r in d['rows']:
    row_name = r['name']
    f = None
    for l in rl._lines:
      logging.debug('Processing line %s', str(l))
      if l[0].startswith(row_name):
        f = l
        break
    if f is None:
      logging.warning(f'row "{row_name}" is missed in {rl.first_strdate()}')
      continue
    k = 0
    for i in r['columns_ids']:
      if k >= len(f[1]):
        logging.error(f"index({k}) out of range in {f}, row_name = '{row_name}'")
      value = f[1][k]
      k += 1
      if value == '-':
        logging.warning("Row '%s', column '%s' value(%s) is not a float number, use 0.0 as it value.", row_name, d['columns'][i], value)
        value = 0.0
      assert isinstance(value, float)
      recept_date = datetime(rl.first_date[0], rl.first_date[1], 1)
      data = { 'date': recept_date, 'row': row_name, 'col': d['columns'][i], 'value': value }
      logging.debug('Add data: %s', data)
      series.append(pd.Series(data))
  logging.info("File '%s' contains %d records.", input_filename, len(series))
  return series

  '''
  for l in rl._lines:
    name, numbers = s
    f = None
    for r in d['rows']:
      row_name = r['name']
      if row_name.startswith(name):
        f = r
        break
    if not f is None:
  '''

if __name__ == "__main__":
  import doctest
  doctest.testmod(verbose=True)
