#!/usr/bin/python3
import logging
import os
import sys
import glob
import datetime

import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.io as pio

PROJECT_PATH = os.getcwd()
SOURCE_PATH = os.path.join(PROJECT_PATH, "src")
sys.path.append(SOURCE_PATH)

import log
import pdf_utils
import tsv

OUTPUT_DIR = 'output'

df = pd.read_csv(os.path.join(OUTPUT_DIR, 'receipt.csv.gz'), compression='gzip')
h = []
for name in df['row'].unique():  
  f = df[(df['row'] == name) & (df['col'] == 'amount')][['date','value']]
  logging.info('Plot graph for %s', name)
  figure = px.bar(f, x='date', y='value')
  figure_html = figure.to_html(full_html=False, include_plotlyjs=False)
  h.append((name, figure_html))

html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Отчёт с вкладками</title>
    <!-- Подгружаем Plotly.js с CDN (один раз) -->
    <script src="https://cdn.plot.ly/plotly-3.3.1.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .tabs { margin-bottom: 20px; }
        .tab-btn {
            padding: 10px 15px;
            margin-right: 5px;
            border: none;
            background-color: #f0f0f0;
            cursor: pointer;
            border-radius: 4px;
        }
        .tab-btn.active { background-color: #007bff; color: white; }
        .tab-content { display: none; padding: 15px; border: 1px solid #ddd; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>Интерактивный отчёт</h1>
    <!-- Вкладки -->
    <div class="tabs">
'''
for i, v in enumerate(h):
  active = ' active' if i == 0 else ''
  html +=  f'<button class="tab-btn{active}" onclick="showTab({i}, event)">{v[0]}</button>\n'
html += '''</div>
    <!-- Контент вкладок (сюда вставим графики) -->
'''
for i, v in enumerate(h):
  html +=  f'<div id="tab{i}" class="tab-content">{v[1]}</div>\n'

html += '''
    <script>
        // Функция переключения вкладок
        function showTab(index, event) {
            // Скрываем все вкладки
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.style.display = 'none';
            });
            // Показываем нужную
            document.getElementById('tab' + index).style.display = 'block';


            // Обновляем кнопки
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
        }
    </script>
</body>
</html>
'''

with open(os.path.join(OUTPUT_DIR, 'receipt.html'), 'w', encoding='utf-8') as f:
  f.write(html)
