#!/usr/bin/env python3
"""Render the approved aggregate snapshot as an in-memory Excel workbook."""
from io import BytesIO
from analytics_ga4_diagnostic import GOALS


def build(doc):
    # Import only when workbook generation is requested; data never touches disk.
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    if not isinstance(doc,dict) or doc.get('schema')!=1:raise ValueError('snapshot schema')
    ga=doc['ga4']; search=doc['search_console']
    if not isinstance(search,list) or len(search)!=2 or not isinstance(ga.get('events'),dict) or not set(ga['events']).issubset(GOALS):raise ValueError('snapshot shape')
    book=Workbook();info=book.active;info.title='Описание'
    for row in [('Приватный срез продвижения','GA4 и Search Console'),
      ('Создан UTC',doc['created_at']),('Актуальность','Снимок на время запуска; даты системы и источника могут расходиться — проверяйте период.'),
      ('GA4 период','28 дней до вчера относительно даты запроса; абсолютные даты не сохранены.'),
      ('Search Console','Окончательные данные веб-поиска; абсолютные даты указаны на листе.'),
      ('Интерпретация','Отсутствие строки события не доказывает ноль и не подтверждает доставку.'),
      ('Приватность','Не публиковать; доступ только с приватным ключом.'),
      ('BigQuery','Экспорт и расходы этим отчётом не подтверждаются.'),
      ('CRM','Отсутствует; не подключена.')]:info.append(row)
    sheet=book.create_sheet('GA4');sheet.append(['Показатель','Значение'])
    totals=ga.get('totals') or {}
    for key,label in [('active_users','Активные пользователи'),('sessions','Сеансы'),('page_views','Просмотры страниц')]:sheet.append([label,totals.get(key)])
    for k,label in [('totals_metadata','Общие показатели'),('events_metadata','События')]:
        sheet.append([label+' — выборка','да' if ga[k]['sampled'] else 'нет']);sheet.append([label+' — пороговая фильтрация','да' if ga[k]['thresholded'] else 'нет'])
    events=book.create_sheet('Цели');events.append(['Согласованное событие','Количество в ответе'])
    for name in GOALS:events.append([name,ga['events'].get(name)])
    events.append(['Пустая ячейка = строка отсутствовала; это не доказанный ноль.'])
    gsc=book.create_sheet('Поиск Google');gsc.append(['Показатель',search[0]['start']+' — '+search[0]['end'],search[1]['start']+' — '+search[1]['end'],'Изменение'])
    for row,(key,label) in enumerate([('clicks','Клики'),('impressions','Показы'),('ctr','CTR'),('position','Средняя позиция')],2):
        values=[r['metrics'].get(key) if r.get('metrics') is not None else None for r in search]
        formula=f'=IF(OR(B{row}="",C{row}="",C{row}=0),"",(B{row}-C{row})/C{row})' if row in (2,3) else None
        gsc.append([label,*values,formula])
        if row==4:
            for col in 'BC':gsc[f'{col}{row}'].number_format='0.00%'
        if row in (2,3):gsc[f'D{row}'].number_format='0.0%'
    gsc.append([]);gsc.append(['Методика','Изменение = (текущий − предыдущий) / предыдущий; при нуле или отсутствии данных не рассчитывается. CTR = клики / показы.'])
    for sh in book:
        sh.freeze_panes='B2'
        for cell in sh[1]:cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='234A75');cell.alignment=Alignment(wrap_text=True)
        for col in range(1,sh.max_column+1):sh.column_dimensions[get_column_letter(col)].width=75 if sh==info and col==2 else 36
        for row in sh.iter_rows(min_row=2):
            for cell in row:cell.alignment=Alignment(wrap_text=True,vertical='top')
            if sh==info:sh.row_dimensions[row[0].row].height=32
    out=BytesIO();book.save(out);data=out.getvalue()
    if len(data)>32000:raise ValueError('workbook too large')
    # Fail before encryption/publication if the generated workbook cannot be opened.
    verify=load_workbook(BytesIO(data),read_only=True);assert verify.sheetnames==['Описание','GA4','Цели','Поиск Google'];verify.close()
    return data
