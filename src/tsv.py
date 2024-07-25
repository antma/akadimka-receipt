# -*- coding: UTF8 -*-
from collections import defaultdict
import csv
import logging
import re

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
    self.re_number = re.compile(r'\d{1,10}((\.|,)\d{0,6})?')
    self.months = dict(map(lambda x: (x[1], x[0] + 1), enumerate(_RU_MONTHS)))
    self.re_year = re.compile(r'20\d\d')
  def is_number(self, s):
    return not self.re_number.fullmatch(s) is None
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

class ReceiptLines:
  def __init__(self):
    self.nr = NumberRecognizer()
    self.first_date = None
    self._lines_with_at_least_3_numbers = []
    self._lines_with_at_least_4_numbers = []
  def first_strdate(self):
    d = self.first_date
    if d is None:
      return 'unknown'
    return f'{d[0]}-{d[1]:02d}'
  def add_line(self, rows):
    l = _Line(rows, self.nr, self.first_date is None)
    if (self.first_date is None) and (not l.date is None):
      self.first_date = l.date
    nc = len(l.numbers)
    if nc >= 3:
      self._lines_with_at_least_3_numbers.append(l)
    if nc >= 4:
      self._lines_with_at_least_4_numbers.append(l)
  def get_numbers(self, name, columns):
    l = self._lines_with_at_least_3_numbers if columns == 3 \
        else self._lines_with_at_least_3_numbers
    try:
      p = next(filter(lambda x: x.matched(name), l))
      return p.numbers
    except StopIteration:
      return None
  def _export_row(self, writer, name, columns):
    n = self.get_numbers(name, columns)
    assert((n is None) or (len(n) >= columns))
    if n is None:
      logging.warning(f'row "{name}" is broken in {self.first_strdate()}')
      t = (name, '-', '-', '-', '-')
    else:
      if len(n) > columns:
        logging.warning(f'row "{name}" contains more numbers ({len(n)}) then expected ({columns}). Please, recheck it manually.')
      if columns == 3:
        t = (name, n[0], '-', n[1], n[2])
      else:
        t = (name, n[0], n[1], n[2], n[3])
    writer.writerow(t)
  def export_csv(self, csvfile, extraction_schema):
    writer = csv.writer(csvfile, delimiter=' ', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    for (name, columns) in extraction_schema:
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
