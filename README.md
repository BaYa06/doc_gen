# DOCX-конструктор (локальный Flask)

## Запуск
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 app.py
```

Откройте: http://127.0.0.1:8001

- Главная: `/` — конструктор договора.
- Здоровье: `/health`
- Счётчик: `/seq`

### Шаблоны
Файлы DOCX-шаблонов лежат в `docx_templates/`. По умолчанию используется `template.docx`.
Внутри шаблона используйте плейсхолдеры docxtpl, например:
`{{ contractNumber|pad3 }}`, `{{ date|ru_date }}`, `{{ director|upper }}`,
а также чекбоксы для владения: `{{ ownershipOwn }}` и `{{ ownershipLease }}`.

### Пояснения
- Номер договора хранится в `data/contract_seq.txt` (локально). В serverless окружении используется `/tmp`.
- Счётчик увеличивается только после успешной генерации файла.
- Форме разрешено выбирать шаблон из белого списка: `template.docx` или `template2.docx`.
