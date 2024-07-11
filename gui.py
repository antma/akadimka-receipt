#!/usr/bin/python
import csv
import io
import logging
import sys
import tkinter as tk
from tkinter.filedialog import askopenfilename

import git
import log
import pdf_utils
import schema
import tsv

def on_click():
  input_filename = askopenfilename(
    filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
  )
  if not input_filename:
    return
  tmp_tsv = 'out.tsv'
  if pdf_utils.pdf_to_tsv(input_filename, tmp_tsv) != 0:
    logging.error(f'Can not convert "{input_filename}" PDF file to TSV format.')
    return
  rl = tsv.read_and_parse(tmp_tsv)
  csvfile = io.StringIO()
  with io.StringIO() as csvfile:
    writer = csv.writer(csvfile, delimiter=' ', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    for (name, columns) in extraction_schema:
      rl.export_row(writer, name, columns)

    d = rl.first_strdate()
    if not d is None:
      label['text'] = d
    #https://stackoverflow.com/questions/27966626/how-to-clear-delete-the-contents-of-a-tkinter-text-widget
    output.delete(1.0, tk.END)
    output.insert(tk.END, csvfile.getvalue())

log.init_logging(None)
git_commit_hash = git.hash_version()
if git_commit_hash is None:
  git_commit_hash = 'unknown'
extraction_schema = schema.load('schema.csv')
if extraction_schema is None:
  sys.exit(1)
window = tk.Tk()
window.title(f'Receipt-{git_commit_hash}')
label = tk.Label(text="Output")
output = tk.Text()
button = tk.Button(
  text="Parse PDF file",
  width=25,
  height=5,
  bg="blue",
  fg="yellow",
  command = on_click,
)
label.pack()
output.pack()
button.pack()
window.mainloop()
