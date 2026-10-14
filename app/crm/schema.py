"""CRM datubāzes shēma, kodu nosaukumi un sintētiskie sākumdati (N4)."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('darbinieks', 'vaditajs', 'administrators'))
);
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    reg_nr TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('uznemums', 'nvo', 'pasvaldiba')),
    responsible_id INTEGER NOT NULL REFERENCES employees(id)
);
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL,
    position TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    basis TEXT NOT NULL,
    basis_date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    author_id INTEGER NOT NULL REFERENCES employees(id),
    kind TEXT NOT NULL CHECK (kind IN ('zvans', 'epasts', 'sanaksme')),
    date TEXT NOT NULL,
    summary TEXT NOT NULL,
    next_step TEXT NOT NULL DEFAULT '',
    ai_generated INTEGER NOT NULL DEFAULT 0,
    approved_by INTEGER REFERENCES employees(id)
);
-- contact_id ir NULL, ja kontaktpersona dzēsta (N2): dalība saglabājas anonīmi.
CREATE TABLE IF NOT EXISTS interaction_participants (
    interaction_id INTEGER NOT NULL REFERENCES interactions(id),
    contact_id INTEGER REFERENCES contacts(id)
);
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_on TEXT NOT NULL,
    deadline TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('jauns', 'darba', 'atbildets')),
    answered_on TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    assignee_id INTEGER NOT NULL REFERENCES employees(id),
    due TEXT NOT NULL,
    organization_id INTEGER REFERENCES organizations(id),
    request_id INTEGER REFERENCES requests(id),
    done_on TEXT,
    CHECK (organization_id IS NOT NULL OR request_id IS NOT NULL)
);
CREATE TABLE IF NOT EXISTS access_log (
    id INTEGER PRIMARY KEY,
    at TEXT NOT NULL,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    action TEXT NOT NULL CHECK (action IN ('skatīja', 'izveidoja', 'mainīja', 'dzēsa')),
    entity TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    organization_id INTEGER REFERENCES organizations(id)
);
"""

ROLES = {"darbinieks": "darbinieks", "vaditajs": "vadītājs", "administrators": "administrators"}
ORG_TYPES = {"uznemums": "Uzņēmums", "nvo": "NVO", "pasvaldiba": "Pašvaldība"}
KINDS = {"zvans": "Zvans", "epasts": "E-pasts", "sanaksme": "Sanāksme"}
STATUSES = {"jauns": "Jauns", "darba": "Darbā", "atbildets": "Atbildēts"}
NEXT_STATUS = {"jauns": "darba", "darba": "atbildets"}
# VDAR 6. panta tiesiskie pamati, kas attiecas uz sadarbības kontaktiem.
BASES = [
    "Leģitīmās intereses",
    "Līgums",
    "Piekrišana",
    "Juridisks pienākums",
    "Sabiedrības intereses",
]
REQUEST_DAYS = 30
RETENTION_YEARS = 2

EMPLOYEES = [
    ("Anna Kalniņa", "darbinieks"),
    ("Jānis Ozols", "darbinieks"),
    ("Līga Bērziņa", "darbinieks"),
    ("Mārtiņš Liepa", "darbinieks"),
    ("Ilze Krūmiņa", "darbinieks"),
    ("Edgars Zariņš", "darbinieks"),
    ("Dace Vītola", "darbinieks"),
    ("Raivis Eglītis", "darbinieks"),
    ("Sandra Lāce", "darbinieks"),
    ("Kristaps Avotiņš", "darbinieks"),
    ("Ieva Priede", "darbinieks"),
    ("Gints Sproģis", "darbinieks"),
    ("Zane Celmiņa", "darbinieks"),
    ("Artūrs Rozītis", "darbinieks"),
    ("Linda Strautiņa", "darbinieks"),
    ("Toms Kļaviņš", "darbinieks"),
    ("Agnese Vilka", "darbinieks"),
    ("Uldis Siliņš", "darbinieks"),
    ("Baiba Jansone", "darbinieks"),
    ("Pēteris Ābele", "darbinieks"),
    ("Elīna Grava", "darbinieks"),
    ("Normunds Lapiņš", "darbinieks"),
    ("Inese Dzene", "vaditajs"),
    ("Valdis Kreicbergs", "vaditajs"),
    ("Rūta Saulīte", "administrators"),
]

# (nosaukums, reģ. nr., veids, atbildīgā darbinieka indekss). Reģ. nr. ir izdomāti.
ORGANIZATIONS = [
    ('SIA "Ezerkrasta koks"', "10000000001", "uznemums", 1),
    ('SIA "Niedru tehnoloģijas"', "10000000002", "uznemums", 1),
    ('AS "Ezermalas ūdens"', "10000000003", "uznemums", 2),
    ('SIA "Laivu darbnīca"', "10000000004", "uznemums", 3),
    ('Biedrība "Zaļā Ezermala"', "10000000005", "nvo", 2),
    ('Nodibinājums "Ezermalas kopiena"', "10000000006", "nvo", 4),
    ('Biedrība "Jauniešu laiva"', "10000000007", "nvo", 5),
    ("Ezermalas novada pašvaldība", "10000000008", "pasvaldiba", 23),
    ("Kalnmalas novada pašvaldība", "10000000009", "pasvaldiba", 6),
    ("Upmalas novada pašvaldība", "10000000010", "pasvaldiba", 7),
]

CONTACT_NAMES = [
    ("Aija Mežule", "valdes locekle"),
    ("Kārlis Dūmiņš", "projektu vadītājs"),
    ("Silvija Bērza", "valdes priekšsēdētāja"),
    ("Oskars Lejnieks", "tehniskais direktors"),
    ("Vija Puriņa", "izpilddirektore"),
    ("Didzis Kalējs", "inženieris"),
    ("Maija Rudzīte", "direktore"),
    ("Aldis Smiltnieks", "meistars"),
    ("Laura Zemīte", "valdes priekšsēdētāja"),
    ("Juris Krasts", "brīvprātīgo koordinators"),
    ("Evija Liepiņa", "direktore"),
    ("Roberts Vējš", "programmu vadītājs"),
    ("Daiga Kurzemniece", "vadītāja"),
    ("Ainārs Pļaviņš", "treneris"),
    ("Gunta Ezeriņa", "attīstības nodaļas vadītāja"),
    ("Imants Akmens", "izpilddirektors"),
    ("Sintija Mieze", "projektu koordinatore"),
    ("Valters Pūce", "domes priekšsēdētāja vietnieks"),
    ("Monta Ozoliņa", "plānošanas speciāliste"),
    ("Ritvars Kroņkalns", "izpilddirektors"),
]

SUMMARIES = [
    ("sanaksme", "Pārrunāta sadarbība pavasara semināru ciklā. Organizācija vēlas divas tēmas: finansējuma piesaiste un brīvprātīgo darbs.", "Nosūtīt semināru programmas projektu."),
    ("zvans", "Kontaktpersona jautāja par konsultācijas iespējām projekta pieteikuma sagatavošanai. Termiņš pieteikumam ir mēneša beigās.", "Pieteikt konsultāciju nākamajai nedēļai."),
    ("epasts", "Saņemts lūgums atsūtīt iepriekšējā semināra materiālus. Materiāli nosūtīti tajā pašā dienā.", ""),
    ("sanaksme", "Kopīgi izvērtēts sadarbības līguma projekts. Jāprecizē pušu pienākumi un atskaišu biežums.", "Sagatavot līguma otro redakciju."),
    ("zvans", "Organizācija informēja par jaunu kontaktpersonu un mainītu juridisko adresi.", "Atjaunot kontaktinformāciju."),
    ("epasts", "Nosūtīts uzaicinājums uz reģionālo forumu. Organizācija apstiprināja dalību ar diviem pārstāvjiem.", "Nosūtīt foruma darba kārtību."),
]


def _shift_years(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:  # 29. februāris
        return day.replace(year=day.year + years, day=28)


def retention_cutoff(today: date) -> date:
    return _shift_years(today, -RETENTION_YEARS)


def seed(conn: sqlite3.Connection, today: date) -> None:
    """Ievieto sākumdatus tukšā datubāzē. Datumi ir relatīvi pret `today`."""
    if conn.execute("SELECT 1 FROM employees LIMIT 1").fetchone():
        return

    def day(offset: int) -> str:
        return (today + timedelta(days=offset)).isoformat()

    conn.executemany("INSERT INTO employees (name, role) VALUES (?, ?)", EMPLOYEES)
    conn.executemany(
        "INSERT INTO organizations (name, reg_nr, type, responsible_id) VALUES (?, ?, ?, ?)",
        ORGANIZATIONS,
    )

    old_basis = _shift_years(today, -3).isoformat()
    for index, (name, position) in enumerate(CONTACT_NAMES):
        org_id = index // 2 + 1
        local = name.split()[0].lower().translate(str.maketrans("āčēģīķļņšūž", "acegiklnsuz"))
        # Divi kontakti ar senu saziņu, lai N2 glabāšanas termiņa saraksts nav tukšs.
        basis_date = old_basis if index in (7, 13) else day(-30 * (index + 1))
        conn.execute(
            "INSERT INTO contacts (organization_id, name, position, email, phone, basis,"
            " basis_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                org_id, name, position, f"{local}{index + 1}@example.com",
                f"2000{index + 1:04d}", BASES[index % 2], basis_date,
            ),
        )

    retention_contacts = {8, 14}
    for index in range(30):
        org_id = index % 10 + 1
        kind, summary, next_step = SUMMARIES[index % len(SUMMARIES)]
        responsible = ORGANIZATIONS[org_id - 1][3]
        author = responsible if index % 3 else (index % 22) + 1
        cursor = conn.execute(
            "INSERT INTO interactions (organization_id, author_id, kind, date, summary,"
            " next_step) VALUES (?, ?, ?, ?, ?, ?)",
            (org_id, author, kind, day(-(index * 4 + 1)), summary, next_step),
        )
        contact_id = (org_id - 1) * 2 + 1 + index % 2
        if contact_id not in retention_contacts:
            conn.execute(
                "INSERT INTO interaction_participants (interaction_id, contact_id) VALUES (?, ?)",
                (cursor.lastrowid, contact_id),
            )

    requests = [
        (1, "Konsultācija par ES fondu pieteikumu", -40, "jauns", None),
        (2, "Semināra materiālu pieprasījums", -35, "darba", None),
        (3, "Dalība reģionālajā forumā", -20, "atbildets", -5),
        (5, "Brīvprātīgo apmācības", -10, "jauns", None),
        (6, "Sadarbības līguma saskaņošana", -50, "atbildets", -12),
        (7, "Telpu nodrošinājums pasākumam", -3, "jauns", None),
        (8, "Datu apmaiņas vienošanās", -32, "darba", None),
        (9, "Kopīga projekta pieteikums", -15, "darba", None),
        (10, "Informācija par iepirkumu", -1, "jauns", None),
        (4, "Uzaicinājums uz izstādi", -60, "atbildets", -25),
        (2, "Pieredzes apmaiņas vizīte", -45, "atbildets", -10),
        (5, "Atbalsta vēstule projektam", -8, "darba", None),
        # F9: termiņš pēc 4 dienām, lai kopsavilkumā būtu „tuvojošies” pieprasījums.
        (1, "Prezentācijas materiāli konferencei", -26, "darba", None),
    ]
    for org_id, title, created, status, answered in requests:
        conn.execute(
            "INSERT INTO requests (organization_id, title, description, created_on, deadline,"
            " status, answered_on) VALUES (?, ?, '', ?, ?, ?, ?)",
            (
                org_id, title, day(created), day(created + REQUEST_DAYS), status,
                None if answered is None else day(answered),
            ),
        )

    tasks = [
        ("Nosūtīt semināra programmu", 1, 0, 1, None),
        ("Piezvanīt par līguma redakciju", 1, -2, 2, None),
        ("Sagatavot atbildi par fondu pieteikumu", 1, 3, None, 1),
        ("Atjaunot kontaktinformāciju", 2, 0, 3, None),
        ("Pārbaudīt foruma dalībnieku sarakstu", 3, 0, 4, None),
        ("Sagatavot datu apmaiņas vienošanos", 23, 0, None, 7),
        ("Nosūtīt pateicības vēstuli", 4, -1, 6, None),
        ("Apkopot brīvprātīgo apmācību vajadzības", 5, 2, None, 4),
        ("Izvērtēt telpu pieejamību", 5, 0, None, 6),
        ("Sagatavot iepirkuma informāciju", 7, 1, None, 9),
    ]
    for title, assignee, due, org_id, request_id in tasks:
        conn.execute(
            "INSERT INTO tasks (title, assignee_id, due, organization_id, request_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (title, assignee, day(due), org_id, request_id),
        )
