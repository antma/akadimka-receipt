# -*- coding: UTF8 -*-
''' functions for raising exceptions and logging '''

import logging
import os
import sys

def is_debug():
  return logging.getLogger().getEffectiveLevel() == logging.DEBUG

def raise_value_error(msg, level = logging.ERROR):
  '''log error and raise ValueError'''
  logging.log(level, msg)
  raise ValueError(msg)

def init_logging(log_filename = None, logging_level = logging.INFO):
  fmt = '%(asctime)s %(levelname)s [%(module)s] %(message)s'
  df = "%H:%M:%S"
  level = os.getenv('LOG_LEVEL', logging_level)
  if not log_filename is None:
    logging.basicConfig(datefmt = df, level = level, format = fmt, filename=log_filename, filemode='w')
  else:
    try:
      import colorlog
    except ImportError:
      logging.basicConfig(datefmt = df, level = level, format = fmt, stream=sys.stdout)
      logging.warning('Please install colorlog: pip3 install colorlog')
    else:
      handler = colorlog.StreamHandler()
      fmt = "%(log_color)s" + fmt
      formatter = colorlog.ColoredFormatter(fmt, datefmt = df, log_colors = {
        'DEBUG':    'cyan',
        'INFO':     'white',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red,bg_white',
      })
      handler.setFormatter(formatter)
      logging.basicConfig(level = level, handlers=[handler], force = True)
