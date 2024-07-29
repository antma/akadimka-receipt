#!/usr/bin/python
import logging
import os
import sys
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import tkinter.filedialog as fd
import tkinter.font as tkFont

import git
import io_utils
import log
import pdf_utils
import storage
import tsv

def float_value(s):
  if s == '?':
    return None
  if (s == '-') or (s == '') or (s == '?'):
    return 0.0
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

def _create_label(parent, text, fg = None, font = None, hint = None):
  d = { 'text': text, 'anchor': tk.CENTER, 'justify': tk.CENTER}
  if not fg is None:
    d["fg"] = fg
  if not font is None:
    d["font"] = font
  label = tk.Label(parent, **d)
  if not hint is None:
    _tip(label, hint)
  return label

class BrowsableGridTable:
  """ таблица с разделителями,
      фиксированными столбцами описания,
      окно обзора можно двигать по месяцам
  """
  def _add_label_to_grid(self, label, row, column):
    logging.debug(f"_add_label_to_grid: text = {label['text']}, row = {row}, column = {column}")
    #четные позиции для разделителей, нечетные для label
    d = { 'row': 2 * row + 1, 'column': 2 * column + 1 }
    month_label = row + 1 == self._row_count
    if month_label:
      d['columnspan'] = self._month_label_colspan
    label.grid(**d)
  def is_empty(self):
    return len(self._months) == 0
  def scrollable_area_window_change_visibility(self, show = True):
    if self.is_empty():
      return
    it = enumerate(self._labels)
    #skip header (it immutable)
    next(it)
    for i, rl in it:
      for j in range(0, self._visible_months * self._col_per_month):
        l = rl[2 + self._first_month * self._col_per_month + j]
        if l is None:
          continue
        if show:
          self._add_label_to_grid(l, i, j + 2)
        else:
          #https://stackoverflow.com/questions/23189610/how-to-remove-widgets-from-grid-in-tkinter
          logging.debug(f"call grid_forget() for {l['text']}")
          l.grid_forget()
  def go_next(self):
    if self._first_month + 1 + self._visible_months <= len(self._months):
      self.scrollable_area_window_change_visibility(False)
      self._first_month += 1
      self.scrollable_area_window_change_visibility(True)
  def go_back(self):
    if self._first_month  > 0:
      self.scrollable_area_window_change_visibility(False)
      self._first_month -= 1
      self.scrollable_area_window_change_visibility(True)
  def __init__(self, frame: tk.Frame, s: storage.Storage, year: int, max_months: int):
    months, data = s.load_year_data(year)
    self._parent = frame
    self._months = months
    self._data = data
    tot_months = len(months)
    if tot_months == 0:
      return
    #header, rows, footer (month name)
    self._col_per_month = len(data[0]) // tot_months
    self._row_count = 2 + len(data)
    self._col_count = 2 + len(data[0])
    self._visible_months = min(max_months, tot_months)
    self._month_label_colspan = 2 * self._col_per_month - 1
    self._first_month = 0
    self._row_grid = 2 * self._row_count + 1
    self._col_grid = 2 * (2 + self._visible_months * self._col_per_month) + 1
    for row in range(0, self._row_grid, 2):
      sep = ttk.Separator(frame, orient = tk.HORIZONTAL)
      sep.grid(row = row, column = 0, columnspan = self._col_grid - 1, sticky = tk.W + tk.E)
    for col in range(0, self._col_grid, 2):
      sep = ttk.Separator(frame, orient = tk.VERTICAL)
      rowspan = self._row_grid - 1
      c = col // 2
      if (c >= 2) and ((c - 2) % self._col_per_month != 0):
        rowspan -= 2
      sep.grid(row = 0, column = col, rowspan = rowspan, sticky = tk.N + tk.S)
    self._labels = [ [None] * self._col_grid for _ in range(self._row_grid)]
    normal_font = tkFont.Font(family = 'Times', size = 11, slant = tkFont.ROMAN)
    bold_font = tkFont.Font(family = 'Times', size = 11, weight = tkFont.BOLD, slant = tkFont.ROMAN)
    for i, (n, v) in enumerate(zip(s.schema.rows, data)):
      rl = self._labels[i+1]
      rl[0] = _create_label(frame, n[0], font = normal_font)
      self._add_label_to_grid(rl[0], i+1, 0)
      rl[1] = _create_label(frame, n[1], font = bold_font)
      self._add_label_to_grid(rl[1], i+1, 1)
      for j, p in enumerate(v):
        fg = None
        hint = None
        c = float_value(p)
        if c is None:
          fg = "gray"
          hint = "нет данных в квитанции"
        elif j >= self._col_per_month:
          c2 = float_value(v[j-self._col_per_month])
          if not c2 is None:
            c -= c2
            if c > 1e-6:
              #increase
              fg = "red"
            if c < -1e-6:
              #decrease
              fg = "green"
        rl[j+2] = _create_label(frame, p, fg, normal_font, hint)
    rl = self._labels[0]
    rl[1] = _create_label(frame, 'ед.изм.', font = normal_font)
    self._add_label_to_grid(rl[1], 0, 1)
    columns_names = s.schema.columns_names()
    for j in range(self._col_per_month * self._visible_months):
      rl[j+2] = _create_label(frame, columns_names[j % self._col_per_month], font = normal_font)
      self._add_label_to_grid(rl[j+2], 0, j+2)
    rl = self._labels[self._row_count - 1]
    for j, month in enumerate(months):
      rl[2 + j * self._col_per_month] = _create_label(frame, tsv.get_month_by_id(month), font = normal_font)
    self.scrollable_area_window_change_visibility(True)

class MainWindow:
  def __init__(self, root, db_storages: list[storage.Storage]):
    self.root = root
    self.root.minsize(width=1600,height=900)
    self.db_storages = db_storages
    self.db_storage = db_storages[0]
    self.table = None
    self._year = 0
    self.current_year = None
    self.year_combobox = None
    self.root.title(f'Receipt-{git.hash_version()}')
    self._create_menubar()
    self._create_table_frame()
    self._create_frame_with_buttons()
    self._pack_widgets()
  def _change_current_storage(self):
    idx = self.current_storage_index.get()
    if 0 <= idx < len(self.db_storages):
      if self.db_storages[idx] != self.db_storage:
        self.db_storage = self.db_storages[idx]
        self.reload_combobox()
        self.reload_table()
  def _create_menubar(self):
    self.menubar = tk.Menu(self.root)
    self.root.configure(menu=self.menubar)
    base_menu = tk.Menu(self.menubar)
    self.menubar.add_cascade(label="База", menu=base_menu)
    base_menu.add_command(label="Добавить PDF квитанции", command=self.add_pdf_files)
    base_menu.add_separator()
    self.current_storage_index = tk.IntVar(base_menu, 0)
    self.current_storage_index.trace("w", lambda varname, _, operation: self._change_current_storage())
    for i, s in enumerate(self.db_storages):
      base_menu.add_radiobutton(label = s.schema.title(), value = i, variable = self.current_storage_index)
  def _create_table_frame(self):
    self.table_frame = tk.Frame(self.root)
    #self.table = tk.Frame(self.root, bd = 10, relief = tk.SUNKEN)
    #self.table_frame.columnconfigure(0, weight=1)
  def reload_combobox(self):
    years = list(map(str, self.db_storage.available_years()))
    self.year_combobox['values'] = years
    if self._year == 0:
      last_year = None
      if len(years) > 0:
        last_year = years[-1]
      if not last_year is None:
        self.current_year.set(last_year)
        self._change_current_year()
  def _create_year_combobox(self):
    self.current_year = tk.StringVar()
    self.current_year.trace("w", lambda varname, _, operation: self._change_current_year())
    self.year_combobox = ttk.Combobox(self.frame_with_buttons, textvariable = self.current_year)
    self.reload_combobox()
  def _go_next(self):
    if self.table is None:
      return
    self.table.go_next()
  def _go_back(self):
    if self.table is None:
      return
    self.table.go_back()
  def _create_frame_with_buttons(self):
    self.frame_with_buttons = tk.Frame(self.root)
    self.button_next = tk.Button(self.frame_with_buttons, text = 'Следующий месяц', command = self._go_next)
    self.button_next.pack(side = tk.RIGHT)
    self.button_back = tk.Button(self.frame_with_buttons, text = 'Предыдущий месяц', command = self._go_back)
    self.button_back.pack(side = tk.LEFT)
    self._create_year_combobox()
    self.year_combobox.pack(side = tk.LEFT)
  def _pack_widgets(self):
    #self.year_combobox.pack()
    self.frame_with_buttons.pack(side = tk.TOP)
    self.table_frame.pack(side = tk.TOP, fill="both", expand=True)
  def _change_current_year(self):
    self.set_year(int(self.current_year.get()))
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
    remove_all_widgets_from_frame(self.table_frame)
    self.table = BrowsableGridTable(self.table_frame, self.db_storage, self._year, 3)
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

def main():
  log.init_logging('out.log', logging.DEBUG)
  dirname = io_utils.script_dirname()
  storages = storage.load_storages(dirname)
  if len(storages) == 0:
    messagebox.showerror("Ошибка", f'Не найдено ни одного правильного файла конфигурации в json формате в папке "{dirname}"')
    sys.exit(1)
  window = MainWindow(tk.Tk(), storages)
  window.mainloop()

main()
