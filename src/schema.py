#!/usr/bin/python3
# -*- coding: UTF8 -*-
"""
работа со схемой строк в csv формате
строка схемы: имя, количество столбцов, единицы измерений
"""

import csv
import logging

def load(filename):
  a = []
  with open(filename, 'r', newline='', encoding = 'UTF8') as csvfile:
    reader = csv.reader(csvfile, delimiter=' ', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    header = next(reader)
    if header != ['name', 'columns', 'units']:
      logging.error('load: schema header mismatched')
      return None
    for line, t in enumerate(reader):
      if len(t) != 3:
        logging.error(f'load: expected exactly 2 fields in a row (file: "{filename}", line {line+2})')
        return None
      try:
        cols = int(t[1])
      except ValueError as err:
        logging.error(f'load: can not convert columns number to integer (file: "{filename}", line {line+2}, error "{err}")')
        return None
      if (cols < 3) or (cols > 4):
        logging.error(f'load: number of columns could be only 3 or 4 (file: "{filename}", line {line+2})')
        return None
      a.append((t[0], cols, t[2]))
  return a
