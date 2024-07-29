# -*- coding: UTF8 -*-
"""
функции связанные с файловой системой и вводом/выводом
"""
import os
import sys

def script_dirname():
  return os.path.dirname(sys.argv[0])

def path_join(dirname, filename):
  if os.path.isabs(filename):
    return filename
  if dirname is None:
    dirname = script_dirname()
  return os.path.join(dirname, filename)

def create_dir_if_absent(dirname):
  if not os.path.lexists(dirname):
    os.mkdir(dirname)

def temporary_filename(filename):
  return path_join(None, filename)
