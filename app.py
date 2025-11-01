from flask import Flask, render_template, request, send_file, jsonify
from datetime import datetime
from jinja2 import Environment
from docxtpl import DocxTemplate
from pathlib import Path
import io, os

app = Flask(__name__, template_folder="templates", static_folder="static")

# --- FS setup for contract sequence ---
IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_VERSION"))
BASE_DIR = Path(__file__).parent
DATA_DIR = (Path("/tmp") if IS_SERVERLESS else BASE_DIR / "data")
SEQ_FILE = DATA_DIR / "contract_seq.txt"

def _read_seq() -> int:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if SEQ_FILE.exists():
            return int((SEQ_FILE.read_text().strip() or "1"))
        return 1
    except Exception:
        return 1

def _write_seq(value: int) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SEQ_FILE.write_text(str(value))

def get_current_contract_number() -> int:
    return _read_seq()

def bump_contract_number_from(used: int) -> None:
    current = _read_seq()
    next_val = max(current, used) + 1
    _write_seq(next_val)

# --- Jinja filters used by the DOCX template ---
RU_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

def ru_date(s: str) -> str:
    try:
        d = datetime.strptime(s, "%Y-%m-%d").date()
        return f"{d.day} {RU_MONTHS.get(d.month, '')} {d.year} г."
    except Exception:
        return s

def upper(s: str) -> str:
    return (s or "").upper()

def pad3(x) -> str:
    try:
        return f"{int(x):03d}"
    except Exception:
        return str(x)

JINJA_ENV = Environment(autoescape=False)
JINJA_ENV.filters["ru_date"] = ru_date
JINJA_ENV.filters["upper"] = upper
JINJA_ENV.filters["pad3"] = pad3

# --- Web pages ---
@app.get("/")
def home():
    return render_template(
        "index.html",
        seqContract=get_current_contract_number(),
        today=datetime.today().date().isoformat(),
    )

@app.get("/public/")
def public_alias():
    return home()

@app.get("/health")
def health():
    return jsonify(ok=True, ts=datetime.utcnow().isoformat())

@app.get("/seq")
def seq():
    return jsonify(contractNumber=get_current_contract_number())

@app.get("/api/docx/health")
def health_alias():
    return health()

@app.get("/api/docx/seq")
def seq_alias():
    return seq()

# --- DOCX generation ---
@app.post("/docx")
def gen_docx():
    ctx = {k: v for k, v in request.form.items()}

    # contractNumber: use user-provided or current
    user_num = request.form.get("contractNumber", "").strip()
    try:
        used_num = int(user_num) if user_num else get_current_contract_number()
    except ValueError:
        used_num = get_current_contract_number()
    ctx["contractNumber"] = used_num

    # ownership radios -> checkboxes in template
    ownership = request.form.get("ownership", "own")
    if ownership == "own":
        ctx["ownershipOwn"] = "☑"
        ctx["ownershipLease"] = "☐"
        ctx["lessorName"] = ""
    else:
        ctx["ownershipOwn"] = "☐"
        ctx["ownershipLease"] = "☑"

    # choose template from whitelist
    allowed = {"template.docx", "template2.docx"}
    tpl_name = request.form.get("template", "template.docx")
    if tpl_name not in allowed:
        tpl_name = "template.docx"

    template_path = BASE_DIR / "docx_templates" / tpl_name
    if not template_path.exists():
        return ("Шаблон не найден: " + str(template_path), 500)

    # Render DOCX
    out = io.BytesIO()
    try:
        doc = DocxTemplate(str(template_path))
        doc.render(ctx, jinja_env=JINJA_ENV)
        doc.save(out)
        out.seek(0)
    except Exception as e:
        return (f"Ошибка генерации DOCX: {e}", 500)

    # increase sequence after success
    bump_contract_number_from(used_num)

    fname = f"Договор_{ctx.get('contractNumber','')}.docx"
    return send_file(
        out,
        as_attachment=True,
        download_name=fname,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

# alias for serverless-style path
@app.post("/api/docx")
def gen_docx_alias():
    return gen_docx()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8001, debug=True)
