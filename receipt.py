#!/usr/bin/python3
# -*- coding: UTF8 -*-

from collections import defaultdict
import csv
import logging
import os
import re
import subprocess
import sys

POPPLER_BIN = ''
TEMP_TSV_FILENAME = 'out.tsv'
LOGGING_LEVEL = logging.INFO

rows_with_3_numbers = [
  'Базовое содержание общ. имущ. в МКД',
  'Текущий ремонт общ. имущ. в МКД',
  'Сод. и ремонт СКД, СВ., АППЗ, автом, дымоудаления',
  'Эксплуатация лифт. оборудования',
  'Орг-я раб. Аварийно-Диспет. службы',
  'Обслуж. котельной, ИТП, насосной станции',
  'Содерж. придом. территории',
  'Уборка МОП',
  'Замена моющихся ковров',
  'Управление МКД'
]

rows_with_4_numbers = [
  'ХВС',
  'ГВС теплоноситель',
  'ГВС тепловая энергия',
  'Канализация хол.воды',
  'Канализация гор.воды',
  'Отопление (расход газа)',
  'Отопление (расход электроэнергии)',
]

other = [
  'Охрана комплекса',
  'Содержание зеленых насаждений, газонов',
]

def pdf_to_tsv(input_filename, output_filename):
  command = [os.path.join(POPPLER_BIN, 'pdftotext'), '-tsv', input_filename, output_filename]
  logging.info('Running command {}'.format(command))
  r = subprocess.run(command, check = True)
  logging.info('pdftotext returns {} code'.format(r.returncode))

class Row:
  def __init__(self, columns, row):
    for (key, value) in zip(columns, row):
      setattr(self, key, value)
  def __str__(self): return str(vars(self))

def lines_text(line): return ' '.join(map(lambda x: x.text, line))
def lines_debug(line): return ' '.join(map(lambda x: str(x), line))
def lines_with_attr(line, attr): return ' '.join(map(lambda x: '{}({})'.format(x.text, getattr(x, attr)), line))

class NumberRecognizer:
  def __init__(self):
    self.re_number = re.compile(r'\d{1,10}((\.|,)\d{0,6})?')
  def is_number(self, str):
    return self.re_number.fullmatch(str) != None

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
          if nr.is_number(s): self._add_number(s)
        else: names.append(s)
      else:
        if nr.is_number(s): self._add_number(s)
    self.name = ' '.join(names)
    #logging.debug(f'Line: name = \"{self.name}\", numbers = {self.numbers}')

class ReceiptLines:
  def __init__(self):
    self.nr = NumberRecognizer()
    self.lines_with_3_numbers = []
    self.lines_with_4_numbers = []
  def add_line(self, rows):
    l = Line(rows, self.nr)
    nc = len(l.numbers)
    if nc == 3: self.lines_with_3_numbers.append(l)
    elif nc == 4: self.lines_with_4_numbers.append(l)
    else: nc = -1
    if nc >= 0: logging.debug(f'Add line with {nc} numbers: {l.name}')
  def get_numbers(self, name, columns):
    l = self.lines_with_3_numbers if columns == 3 else self.lines_with_4_numbers
    try:
      p = next(filter(lambda x: x.name.startswith(name), l))
      return p.numbers
      #if columns == 3: r = (name, p[1][0], '-', p[1][1], p[1][2])
      #else: r = (name, p[1][0], p[1][1], p[1][2], p[1][3])
    except StopIteration:
      return None
  def process_section(self, writer, names, columns):
    for name in names:
      n = self.get_numbers(name, columns)
      if n == None:
        logging.warning(f'row "{name}" is broken')
        t = (name, '-', '-', '-', '-')
      elif columns == 3:
        t = (name, n[0], '-', n[1], n[2])
      else:
        t = (name, n[0], n[1], n[2], n[3])
      writer.writerow(t)

def group_by(rows, attr):
  d = defaultdict(list)
  for row in rows:
    d[getattr(row, attr)].append(row)
  for i, a in d.items():
    logging.debug('{} #{}: {}'.format(attr, i, lines_text(a)))
    logging.debug('{} #{}: {}'.format(attr, i, lines_with_attr(a, 'line_num')))
    logging.debug('{} #{}: {}'.format(attr, i, lines_with_attr(a, 'left')))
    #logging.debug('{} #{}: {}'.format(attr, i, lines_debug(a)))
  return d

def csv_readall(reader):
  #level page_num par_num block_num line_num word_num left top width height	conf text
  columns = next(reader)
  logging.debug('columns = {}'.format(columns))
  rows = []
  for row in reader:
    o = Row(columns, row)
    rows.append(o)
    #logging.debug(o)
  return rows

def read_tsv(input_filename):
  with open(input_filename, newline='') as f:
    reader = csv.reader(f, delimiter = '\t')
    return csv_readall(reader)

fmt = '%(asctime)s %(levelname)s %(message)s'
logging.basicConfig(level=LOGGING_LEVEL,format=fmt,filename='receipt.log',filemode='w')
input_filename = sys.argv[1]
pdf_to_tsv(input_filename, TEMP_TSV_FILENAME)
rows = read_tsv(TEMP_TSV_FILENAME)
rl = ReceiptLines()
for group in group_by(rows, 'top').values():
  rl.add_line(group)

with open('out.csv', 'w', newline='') as csvfile:
  writer = csv.writer(csvfile, delimiter=' ', quotechar='"', quoting=csv.QUOTE_MINIMAL)
  rl.process_section(writer, rows_with_3_numbers, 3)
  rl.process_section(writer, rows_with_4_numbers, 4)
  rl.process_section(writer, other, 3)
