# -*- coding: UTF8 -*-

import csv
import glob
import logging
import os
import re
import sys

import schema

def _compute_csv_filename(storage_dir, year, month):
  """
  >>> _compute_csv_filename('', 2024, 7)
  '2024-07.csv'
  """
  return os.path.join(storage_dir, f'{year:04d}-{month:02d}.csv')

class Storage:
  def __init__(self, dirname, schema_filename):
    self.dir = os.path.join(os.path.dirname(sys.argv[0]), dirname)
    if not os.path.lexists(self.dir):
      os.mkdir(self.dir)
    self.schema_filename = schema_filename
    self.schema = schema.load(schema_filename)
    self._max_month_columns = max(map(lambda t: t[1], self.schema))
    self._month_masks_by_year = {}
  def compute_csv_filename(self, year, month):
    return _compute_csv_filename(self.dir, year, month)
  def scan(self):
    reg_exp = re.compile(r'(\d{4})-(\d\d).csv')
    d = {}
    for fn in glob.glob(os.path.join(self.dir, '[0-9][0-9][0-9][0-9]-[0-9][0-9].csv')):
      s = os.path.basename(fn)
      m = reg_exp.fullmatch(s)
      if not m is None:
        year = int(m.group(1))
        month = int(m.group(2))
        if 1 <= month <= 12:
          d[year] = d.get(year, 0) | (1 << month)
    self._month_masks_by_year = d
  def available_years(self):
    a = list(self._month_masks_by_year.keys())
    a.sort()
    return a
  def load_month_data(self, year, month):
    csv_filename = self.compute_csv_filename(year, month)
    a = []
    with open(csv_filename, 'r', newline='', encoding = 'UTF8') as csvfile:
      reader = csv.reader(csvfile, delimiter=' ', quotechar='"', quoting=csv.QUOTE_MINIMAL)
      for line, (t, data) in enumerate(zip(self.schema, reader)):
        if len(data) != 1 + self._max_month_columns:
          logging.error(f'Illegal number of columns in the line {line+1} of the file "{csv_filename}". \
                          It isn''t matched to schema file "{self.schema_filename}"')
          return None
        if t[0] != data[0]:
          logging.error(f'Line {line+1} in the file "{csv_filename}" isn''t matched to schema file "{self.schema_filename}"')
          return None
        a.append(data[1:])
    return a
  def load_year_data(self, year):
    a = [ [] for t in self.schema]
    mask = self._month_masks_by_year.get(0)
    months = []
    for month in range(1, 13):
      if (mask & (1 << month)) != 0:
        d = self.load_month_data(year, month)
        if d is None:
          continue
        months.append(month)
        for i, v in enumerate(d):
          a[i].extend(v)
    return (months, a)

if __name__ == "__main__":
  import doctest
  doctest.testmod(verbose=True)
