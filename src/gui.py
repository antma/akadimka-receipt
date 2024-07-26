#!/usr/bin/python
import io
import logging
import os
import pprint
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

def float_value(s):
  if (s == '-') or (s == '') or (s == '?'): return 0.0
  return float(s.replace(',', '.'))

def remove_all_widgets_from_frame(frame):
  """
  https://stackoverflow.com/a/50657381/14024582
  """
  for widget in frame.winfo_children():
    widget.destroy()

class MainWindow:
  def __init__(self, root, db_storage):
    self.root = root
    self.root.minsize(width=1600,height=900)
    self.db_storage = db_storage
    self.root.title(f'Receipt-{git.hash_version()}')
    self._create_menubar()
    self._create_table()
    self._create_year_combobox()
    self._pack_widgets()
  def _create_menubar(self):
    self.menubar = tk.Menu(self.root)
    self.root.configure(menu=self.menubar)
    baseMenu = tk.Menu(self.menubar)
    self.menubar.add_cascade(label="База", menu=baseMenu)
    baseMenu.add_command(label="Добавить PDF квитанции", command=self.add_pdf_files)
  def _create_table(self):
    #self.table = ttk.Treeview(self.root)
    self.table = ttk.Frame(self.root)
    self.table.columnconfigure(0, weight=1)
  def _create_year_combobox(self):
    self._year = 0
    self.currentYear = tk.StringVar()
    self.yearCombobox = ttk.Combobox(self.root, textvariable = self.currentYear)
    years = list(map(str, self.db_storage.available_years()))
    last_year = None
    if len(years) > 0:
      last_year = years[-1]
    logging.debug('last_year = %s', last_year)
    self.yearCombobox['values'] = years
    self.currentYear.trace("w", lambda varname, _, operation: self._change_current_year())
    if not last_year is None:
      self.currentYear.set(last_year)
      self._change_current_year()
  def _pack_widgets(self):
    self.yearCombobox.pack()
    self.table.pack(fill="both", expand=True)
  def _change_current_year(self):
    self.set_year(int(self.currentYear.get()))
  def _add_label_to_table(self, row, column, text, bg = None, columnspan = None):
    d = { 'text': text, 'anchor': 'center', 'justify': 'center'} 
    if not bg is None:
      d["bg"] = bg
    label = tk.Label(self.table, **d)
    d = {"row": row, "column": column}
    if not columnspan is None:
      d["columnspan"] = columnspan
    label.grid(**d)
  def reload_table(self):
    months, data = self.db_storage.load_year_data(self._year)
    logging.debug('%s', pprint.pformat(data))
    remove_all_widgets_from_frame(self.table)
    if len(months) == 0:
      return
    w = len(data[0]) // len(months)
    for i, month in enumerate(months):
      name = tsv.get_month_by_id(month)
      self._add_label_to_table(0, 1 + i * w, name, None, w)
    for i, (n, v) in enumerate(zip(self.db_storage.schema, data)):
      self._add_label_to_table(i + 1, 0, n[0])
      for j, p in enumerate(v):
        bg = None
        c = float_value(p) 
        if p == '?': bg = "gray"
        if j >= 4:
          c -= float_value(v[j-4])
          if c < -1e-6: bg = "green"
          if c > 1e-6: bg = "red"
        self._add_label_to_table(i + 1, j + 1, p, bg)
  def set_year(self, year):
    if self._year != year:
      logging.debug(f'Modifing current year to {year}')
      self._year = year
      self.reload_table()
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
