# -*- coding: UTF8 -*-
"""
работа с набором csv месячных файлов как с единым целом
"""

import csv
import glob
import logging
import os
import re

import io_utils
import schema
import tsv

FLAG_NEW_YEAR = 1
FLAG_NEW_MONTH = 2

def _compute_csv_filename(storage_dir, year, month):
  """
  >>> _compute_csv_filename('', 2024, 7)
  '2024-07.csv'
  """
  return os.path.join(storage_dir, f'{year}-{month:02d}.csv')

class Storage:
  def __init__(self, schema_filename):
    self.schema_filename = schema_filename
    self.schema = schema.ExtractionSchema(schema_filename)
    self.dir = None
    if not self.schema.load():
      self.schema = None
    else:
      self.dir = self.schema.db_data_dir()
      io_utils.create_dir_if_absent(self.dir)
      self._month_masks_by_year = {}
      self._month_columns = self.schema.columns()
      self._scan()
  def is_valid(self):
    return not self.schema is None
  def schema_number_of_rows(self):
    return len(self.schema.rows)
  def compute_csv_filename(self, year, month):
    return _compute_csv_filename(self.dir, year, month)
  def _add_month(self, year, month):
    res = 0
    if 1 <= month <= 12:
      bit = 1 << month
      old = self._month_masks_by_year.get(year, 0)
      if old == 0:
        res += FLAG_NEW_YEAR
      if (old & bit) == 0:
        self._month_masks_by_year[year] = old + bit
        res += FLAG_NEW_MONTH
    return res
  def _scan(self):
    reg_exp = re.compile(r'(\d{4})-(\d\d).csv')
    self._month_masks_by_year = {}
    for fn in glob.glob(os.path.join(self.dir, '[0-9][0-9][0-9][0-9]-[0-9][0-9].csv')):
      s = os.path.basename(fn)
      m = reg_exp.fullmatch(s)
      if not m is None:
        year = int(m.group(1))
        month = int(m.group(2))
        self._add_month(year, month)
  def available_years(self):
    a = list(self._month_masks_by_year.keys())
    a.sort()
    return a
  def load_month_data(self, year, month):
    csv_filename = self.compute_csv_filename(year, month)
    a = []
    with open(csv_filename, 'r', newline='', encoding = 'UTF8') as csvfile:
      reader = csv.reader(csvfile, delimiter=' ', quotechar='"', quoting=csv.QUOTE_MINIMAL)
      for line, (t, data) in enumerate(zip(self.schema.rows, reader)):
        if len(data) != 1 + self._month_columns:
          logging.error(f'Illegal number of columns in the line {line+1} of the file "{csv_filename}". '
                        f'It isn\'t matched to schema file "{self.schema_filename}"')
          return None
        if t[0] != data[0]:
          logging.error(f'Line {line+1} in the file "{csv_filename}" isn''t matched to schema file "{self.schema_filename}"')
          return None
        a.append(data[1:])
    return a
  def load_year_data(self, year):
    logging.debug(f'load_year_data for {year} year')
    logging.debug(f'self._month_columns = {self._month_columns}')
    a = [ [] for _ in self.schema.rows]
    mask = self._month_masks_by_year.get(year, 0)
    months = []
    for month in range(1, 13):
      if (mask & (1 << month)) != 0:
        d = self.load_month_data(year, month)
        if d is None:
          continue
        months.append(month)
        for w, v in zip(a, d):
          w.extend(v)
    return (months, a)
  def save_csv(self, year: int, month: int, rl: tsv.ReceiptLines) -> int:
    """
    returns combination of flags (NEW_YEAR and NEW_MONTH)
    """
    #TODO: consider case when csv file is already exist
    res = 0
    csv_filename = self.compute_csv_filename(year, month)
    with open(csv_filename, 'w', newline='', encoding = 'UTF8') as csvfile:
      rl.export_csv(csvfile, self.schema)
      res += self._add_month(year, month)
    return res
if __name__ == "__main__":
  import doctest
  doctest.testmod(verbose=True)
