#!/usr/bin/python3
# -*- coding: UTF8 -*-
"""
pp.py [file.json]
утилита форматирует в удобном виде для просмотра json файл
"""

import json
import pprint
import sys

filename = sys.argv[1]
if not filename.endswith('.json'):
  sys.exit(1)

with open(filename, 'r', encoding = 'UTF8') as f:
  d = json.load(f)

with open(filename, 'w', encoding = 'UTF8') as f:
  s = pprint.pformat(d, indent = 2)
  s = s.replace("'", '"')
  f.write(s + '\n')
