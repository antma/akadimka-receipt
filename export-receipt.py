#!/usr/bin/python3
import datetime
import glob
import logging
import os
import shutil
import sys

import pandas as pd
import matplotlib.pyplot as plt

PROJECT_PATH = os.getcwd()
SOURCE_PATH = os.path.join(PROJECT_PATH, "src")
sys.path.append(SOURCE_PATH)

import log
import pdf_utils
import tsv

OUTPUT_DIR = 'output'

if not os.path.lexists(OUTPUT_DIR):
  os.mkdir(OUTPUT_DIR)

log.init_logging(None, logging.INFO)

json_configurations = []

for name in ['schema-receipt.json', 'schema-complete-renovation.json']:
  json_configuration_filename = os.path.join('conf', name)
  json_configurations.append(tsv.load_json_configuration(json_configuration_filename))

output_csv_filename = os.path.join(OUTPUT_DIR, 'receipt.csv.gz')

series = []
for filename in sorted(glob.glob(os.path.join('input', '*.pdf'))):
  o = pdf_utils.pdt_to_temporary_tsv(filename)
  if o is None:
    logging.error("Could not convert '%s' to TSV", filename)
    continue
  k = [j for j in json_configurations if os.path.basename(filename).startswith(j['id'])]
  if len(k) == 1:
    #в имени файла указан тип квитанции
    s = tsv.read_and_parse(o, k[0])
    assert(len(s) > 0)
    series.extend(s)
  else:
    #пытаемся угадать тип квитанции и если получилось также копируем файл с указанием даты и типа квитанции
    copy_filename = None
    for j in json_configurations:
      s = tsv.read_and_parse(o, j)
      if len(s) > 0:
        series.extend(s)
        dt = s[0]['date']
        copy_filename = os.path.join(OUTPUT_DIR, j['id'] + '_' + dt.strftime('%Y-%m') + '.pdf')
        ok = True
        break
    if copy_filename is None:
      logging.error("Could not parse '%s'", filename)
      sys.exit(1)
    shutil.copy2(filename, copy_filename)
  os.unlink(o)

df = pd.DataFrame.from_records(series).sort_values(by = 'date', kind='mergesort')
print(df)
df.to_csv(output_csv_filename, compression={'method': 'gzip', 'compresslevel': 9}, index = False)
