#!/usr/bin/python
import io
import logging
import os
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
  with io.StringIO() as csvfile:
    rl.export_csv(csvfile, extraction_schema)
    d = rl.first_strdate()
    if not d is None:
      label['text'] = d
    #https://stackoverflow.com/questions/27966626/how-to-clear-delete-the-contents-of-a-tkinter-text-widget
    output.delete(1.0, tk.END)
    output.insert(tk.END, csvfile.getvalue())
  logging.info(f'Removing temp file "{tmp_tsv}"')
  os.unlink(tmp_tsv)

log.init_logging(None)
extraction_schema = schema.load('schema.csv')
if extraction_schema is None:
  sys.exit(1)
window = tk.Tk()
window.title(f'Receipt-{git.hash_version()}')
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
output.pack(expand=1, fill=tk.BOTH)
button.pack()
window.mainloop()