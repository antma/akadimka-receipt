#!/usr/bin/python
import io
import logging
import os
import pprint
import sys
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as fd
import tkinter.font as tkFont

import git
import io_utils
import log
import pdf_utils
import schema
import storage
import tsv

def float_value(s):
  if s == '?': return None
  if (s == '-') or (s == '') or (s == '?'): return 0.0
  return float(s.replace(',', '.'))

def remove_all_widgets_from_frame(frame):
  """
  https://stackoverflow.com/a/50657381/14024582
  """
  for widget in frame.winfo_children():
    widget.destroy()

def _tip(window, hint):
  """ https://stackoverflow.com/a/65125558/14024582 """
  from idlelib.tooltip import Hovertip
  tip = Hovertip(window, hint)

class MainWindow:
  def __init__(self, root, db_storage):
    self.root = root
    self.root.minsize(width=1600,height=900)
    self.db_storage = db_storage
    self._bold_font = tkFont.Font(weight="bold")
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
    self.table = tk.Frame(self.root)
    #self.table = tk.Frame(self.root, bd = 10, relief = tk.SUNKEN)
    self.table.columnconfigure(0, weight=1)
  def reload_combobox(self):
    years = list(map(str, self.db_storage.available_years()))
    self.yearCombobox['values'] = years
    if self._year == 0:
      last_year = None
      if len(years) > 0:
        last_year = years[-1]
      if not last_year is None:
        self.currentYear.set(last_year)
        self._change_current_year()
  def _create_year_combobox(self):
    self._year = 0
    self.currentYear = tk.StringVar()
    self.currentYear.trace("w", lambda varname, _, operation: self._change_current_year())
    self.yearCombobox = ttk.Combobox(self.root, textvariable = self.currentYear)
    self.reload_combobox()
  def _pack_widgets(self):
    self.yearCombobox.pack()
    self.table.pack(fill="both", expand=True)
  def _change_current_year(self):
    self.set_year(int(self.currentYear.get()))
  def _add_label_to_table(self, row, column, text, fg = None, columnspan = None, font = None, hint = None):
    d = { 'text': text, 'anchor': tk.CENTER, 'justify': tk.CENTER}
    if not fg is None:
      d["fg"] = fg
    if not font is None:
      d["font"] = font
    label = tk.Label(self.table, **d)
    if not hint is None:
      _tip(label, hint)
    d = {"row": row, "column": column}
    if not columnspan is None:
      d["columnspan"] = columnspan
    label.grid(**d)
    return label
  def reload_table(self):
    months, data = self.db_storage.load_year_data(self._year)
    logging.debug('%s', pprint.pformat(data))
    remove_all_widgets_from_frame(self.table)
    if len(months) == 0:
      return
    w = len(data[0]) // len(months)
    sep = tk.Frame(self.table, bd=10, relief = tk.SUNKEN, width=4)
    sep.grid(row = 0, column = 1, rowspan = 3 + self.db_storage.schema_number_of_rows(), sticky = 'ns')
    self._add_label_to_table(1, 2, 'ед.изм.')
    for i, month in enumerate(months):
      name = tsv.get_month_by_id(month)
      self._add_label_to_table(1, 4 + i * (2 * w), name, None, 2 * w)
      sep = tk.Frame(self.table, bd=10, relief = tk.SUNKEN, width=4)
      sep.grid(row = 0, column = 3 + i * (2 * w), rowspan = 3 + self.db_storage.schema_number_of_rows(), sticky = 'ns')
    columns_names = self.db_storage.schema.columns_names()
    for i, (n, v) in enumerate(zip(self.db_storage.schema.rows, data)):
      self._add_label_to_table(i + 3, 0, n[0])
      self._add_label_to_table(i + 3, 2, n[1], font = self._bold_font)
      for j, p in enumerate(v):
        bg = None
        c = float_value(p)
        if c is None: bg = "gray"
        elif j >= w:
          c2 = float_value(v[j-w])
          if not c2 is None:
            c -= c2
            if c > 1e-6:
              #increase
              bg = "red"
            if c < -1e-6:
              #decrease
              bg = "green"
        col1, col2 = divmod(j, w)
        self._add_label_to_table(i + 3, 4 + col1 * (2 * w) + 2 * col2, p, bg, None, hint = columns_names[col2])
        if col2 > 0:
          sep = ttk.Separator(self.table, orient = 'vertical')
          sep.grid(row = 3, column = 4 + col1 * (2 * w) + 2 * col2 - 1, rowspan = 2 + self.db_storage.schema_number_of_rows(), sticky = 'ns')
    sep = tk.Frame(self.table, bd=10, relief = tk.SUNKEN, height=4)
    sep.grid(row = 0, column = 0, columnspan = len(months) * 2 * w + 3, sticky = 'ew')
    sep = tk.Frame(self.table, bd=10, relief = tk.SUNKEN, height=4)
    sep.grid(row = 2, column = 0, columnspan = len(months) * 2 * w + 3, sticky = 'ew')
    sep = tk.Frame(self.table, bd=10, relief = tk.SUNKEN, height=4)
    sep.grid(row = 3 + self.db_storage.schema_number_of_rows(), column = 0, columnspan = len(months) * 2 * w + 3, sticky = 'ew')

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
      flags = self.db_storage.save_csv(year, month, rl)
      if (flags & storage.FLAG_NEW_YEAR) != 0:
        self.reload_combobox()
      if (flags & storage.FLAG_NEW_MONTH) != 0:
        self.reload_table()
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

log.init_logging('out.log', logging.DEBUG)
s = storage.Storage('.data', 'schema.json')
if not s.is_valid():
  sys.exit(1)

window = MainWindow(tk.Tk(), s)
window.mainloop()
