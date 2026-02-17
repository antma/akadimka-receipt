import json

with open('schema.json') as f:
  config = json.load(f)
  print(config)
