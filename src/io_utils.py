# -*- coding: UTF8 -*-
import os
import sys

def path_join(relative_filename):
  return os.path.join(os.path.dirname(sys.argv[0]), relative_filename)

def create_dir_if_absent(dirname):
  if not os.path.lexists(dirname):
    os.mkdir(dirname)
