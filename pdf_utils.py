# -*- coding: UTF8 -*-

import logging, os, subprocess

def pdf_to_tsv(input_filename, output_filename):
  if not os.path.lexists(input_filename):
    logging.error(f'File "{input_filename}" not found.')
    return -1
  command = ['pdftotext', '-tsv', input_filename, output_filename]
  logging.info(f'Running command {command}')
  r = subprocess.run(command, check = False, shell = False)
  logging.info(f'pdftotext returns {r.returncode} code')
  return r.returncode
