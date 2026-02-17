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

log.init_logging(None, logging.DEBUG)

json_configuration_filename = os.path.join('conf', 'schema.json')
json_configuration = tsv.load_json_configuration(json_configuration_filename)

for filename in glob.glob(os.path.join('input', 'receipt', '2024-01.*')):
  o = pdf_utils.pdt_to_temporary_tsv(filename)
  if o is None:
    logging.error("Could not convert '%s' to TSV", filename)
  series = tsv.read_and_parse(o, json_configuration)
  print(series)
  os.unlink(o)
