# -*- coding: UTF8 -*-

import logging
import os
import subprocess
import tempfile
import uuid

def pdf_to_tsv(input_filename, output_filename):
  if not os.path.lexists(input_filename):
    logging.error(f'File "{input_filename}" not found.')
    return -1
  command = ['pdftotext', '-tsv', input_filename, output_filename]
  logging.info(f'Running command {command}')
  r = subprocess.run(command, check = False, shell = False)
  if r.returncode != 0:
    logging.warning('pdftotext returns %s errorcode', r.returncode)
  else:
    logging.debug('pdftotext succesfully terminated')
  return r.returncode

def pdt_to_temporary_tsv(input_filename):
  bn = os.path.basename(input_filename)
  temp_dir = tempfile.gettempdir()
  unique_name = f".{bn}-{uuid.uuid4().hex}.tsv"
  temp_file_path = os.path.join(temp_dir, unique_name)
  r = pdf_to_tsv(input_filename, temp_file_path)
  if r == 0:
    return temp_file_path
  return None
