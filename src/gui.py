#!/usr/bin/python
import io
import logging
import os
import sys
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as fd

import git
import io_utils
import log
import pdf_utils
import schema
import storage
import tsv

class MainWindow:
  def __init__(self, root, db_storage):
    self.root = root
    self.db_storage = db_storage
    self.root.title(f'Receipt-{git.hash_version()}')
    self._create_menubar()
    self._create_year_combobox()
  def _create_menubar(self):
    self.menubar = tk.Menu(self.root)
    self.root.configure(menu=self.menubar)
    baseMenu = tk.Menu(self.menubar)
    self.menubar.add_cascade(label="База", menu=baseMenu)
    baseMenu.add_command(label="Добавить PDF квитанции", command=self.add_pdf_files)
  def _create_year_combobox(self):
    self._year = 0
    self.currentYear = tk.StringVar()
    self.yearCombobox = ttk.Combobox(self.root, textvariable = self.currentYear)
    years = list(map(str, self.db_storage.available_years()))
    last_year = None
    if len(years) > 0:
      last_year = years[-1]
    self.yearCombobox['values'] = years
    self.currentYear.trace("w", lambda varname, _, operation: self._change_current_year())
    if not last_year is None:
      self.currentYear.set(last_year)
      self._change_current_year()
    self.yearCombobox.pack()
  def _change_current_year(self):
    cur = int(self.yearCombobox.get())
    if self._year != cur:
      logging.debug(f'Modifing current year to {cur}')
      self._year = cur
  def _add_pdf_file(self, pdf_filename):
    tmp_tsv = io_utils.temporary_filename('out.tsv')
    if pdf_utils.pdf_to_tsv(pdf_filename, tmp_tsv) != 0:
      logging.error(f'Can not convert "{pdf_filename}" PDF file to TSV format.')
      return
    rl = tsv.read_and_parse(tmp_tsv)
    date = rl.first_date
    if not date is None:
      year, month = date
      self.db_storage.save_csv(year, month, rl)
    logging.info(f'Removing temp file "{tmp_tsv}"')
    os.unlink(tmp_tsv)
  def add_pdf_files(self):
    logging.info("Clicked add_pdf_file")
    input_filenames = fd.askopenfilenames(
      filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
    )
    for pdf_filename in input_filenames:
      self._add_pdf_file(pdf_filename)
  def mainloop(self):
    self.root.mainloop()

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

log.init_logging('out.log', logging.DEBUG)
#extraction_schema = schema.load('schema.csv')
s = storage.Storage('.data', 'schema.csv')
if not s.is_valid():
  sys.exit(1)

window = MainWindow(tk.Tk(), s)
window.mainloop()

"""
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
"""
