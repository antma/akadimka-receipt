# -*- coding: UTF8 -*-

import logging
import subprocess

def hash_version():
  command = ['git', 'log', '-1', '--pretty=format:"%H"']
  #https://stackoverflow.com/a/3172488/14024582
  #So invoking the shell invokes a program of the user's choosing and is platform-dependent.
  #Generally speaking, avoid invocations via the shell.
  try:
    r = subprocess.run(command, check = False, shell = False, capture_output=True)
  except FileNotFoundError as err:
    logging.warning(f"Can't found script version. {err}")
    return None
  if r.returncode != 0: return None
  return r.stdout.decode('UTF8').strip()
