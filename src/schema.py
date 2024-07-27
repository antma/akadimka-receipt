#!/usr/bin/python3
# -*- coding: UTF8 -*-
"""
работа со схемой строк в csv формате
строка схемы: имя, количество столбцов, единицы измерений
"""

import csv
import json
import logging
import os
import pprint

class ExtractionSchema:
  def __init__(self, json_filename):
    self._json_filename = json_filename
    self._d = None
    self.rows = None
  def load(self):
    with open(self._json_filename, 'r') as json_file:
      self._d = json.load(json_file)
      logging.debug('%s', pprint.pformat(self._d))
      return self._rows_schema_load(os.path.join(os.path.dirname(self._json_filename), self._d["rows_schema_csv_filename"]))
  def _parse_row_columns(self, s):
    l = list(map(int, s.split(',')))
    if any(map(lambda x: -1 > x, l)):
      return None
    return l
  def columns(self):
    n = self.columns_names()
    if n is None:
      return 0
    return len(n)
  def columns_names(self):
    if self._d is None:
      return None
    return self._d.get('columns_names')
  def _rows_schema_load(self, filename):
    a = []
    with open(filename, 'r', newline='', encoding = 'UTF8') as csvfile:
      reader = csv.reader(csvfile, delimiter=' ', quotechar='"', quoting=csv.QUOTE_MINIMAL)
      header = next(reader)
      if header != ['name', 'units', 'columns']:
        logging.error('load: schema header mismatched')
        return False
      for line, t in enumerate(reader):
        if len(t) != 3:
          logging.error(f'load: expected exactly 3 fields in a row (file: "{filename}", line {line+2})')
          return False
        try:
          cols = self._parse_row_columns(t[2])
        except ValueError as err:
          logging.error(f'load: can not convert columns indices to List[int] (file: "{filename}", line {line+2}, error "{err}")')
          return False
        a.append((t[0], t[1], cols))
    self.rows = a
    return True
