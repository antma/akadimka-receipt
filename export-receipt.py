#!/usr/bin/python3
import logging
import os
import sys
import glob
import datetime

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

json_configuration_filename = os.path.join('conf', 'schema.json')
json_configuration = tsv.load_json_configuration(json_configuration_filename)
output_csv_filename = os.path.join(OUTPUT_DIR, 'receipt.csv.gz')

series = []
for filename in sorted(glob.glob(os.path.join('input', 'receipt', '*.pdf'))):
  o = pdf_utils.pdt_to_temporary_tsv(filename)
  if o is None:
    logging.error("Could not convert '%s' to TSV", filename)
  series.extend(tsv.read_and_parse(o, json_configuration))
  os.unlink(o)

df = pd.DataFrame.from_records(series)
print(df)
df.to_csv(output_csv_filename, compression={'method': 'gzip', 'compresslevel': 9}, index = False)
