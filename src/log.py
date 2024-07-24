# -*- coding: UTF8 -*-

import logging
import sys

def init_logging(log_filename, logging_level = logging.INFO):
  fmt = '%(asctime)s %(levelname)s [%(module)s] %(message)s'
  if log_filename is None:
    logging.basicConfig(level=logging_level, format=fmt, stream=sys.stdout)
  else:
    logging.basicConfig(level=logging_level, format=fmt, filename=log_filename, filemode='w')
