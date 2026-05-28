import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "belgo_ti.db"
_local = threading.local()

_DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT NOT NULL,
    email        TEXT NOT NULL UNIQUE,
    departamento TEXT NOT NULL,
    ramal        TEXT,
    criado_em    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS tickets (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo         TEXT NOT NULL,
    descricao      TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'ABERTO'
                   CHECK(status IN ('ABERTO','EM_ATENDIMENTO','RESOLVIDO','FECHADO')),
    nivel          TEXT CHECK(nivel IN ('N1','N2','FORA_DE_ESCOPO')),
    categoria      TEXT,
    confianca      INTEGER,
    criado_por     INTEGER REFERENCES usuarios(id),
    atribuido_para INTEGER REFERENCES usuarios(id),
    criado_em      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    resolvido_em   TEXT,
    resolucao      TEXT,
    auto_resolvido INTEGER NOT NULL DEFAULT 0,
    sugestao_ia    TEXT,
    acao_ia        TEXT,
    tempo_estimado TEXT
);

CREATE INDEX IF NOT EXISTS idx_tickets_status    ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_nivel     ON tickets(nivel);
CREATE INDEX IF NOT EXISTS idx_tickets_criado_em ON tickets(criado_em DESC);
"""


def get_db() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return _local.conn


def init_db():
    conn = get_db()
    conn.executescript(_DDL)
    conn.commit()


def _row(row) -> dict | None:
    return dict(row) if row else None


def _rows(rows) -> list[dict]:
    return [dict(r) for r in rows]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Usuários ──────────────────────────────────────────────────────────────────

def criar_usuario(nome: str, email: str, departamento: str, ramal: str = None) -> dict:
    conn = get_db()
    with conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, email, departamento, ramal) VALUES (?, ?, ?, ?)",
            (nome, email, departamento, ramal),
        )
    return buscar_usuario_por_id(cur.lastrowid)


def listar_usuarios() -> list[dict]:
    return _rows(get_db().execute("SELECT * FROM usuarios ORDER BY nome").fetchall())


def buscar_usuario_por_email(email: str) -> dict | None:
    return _row(get_db().execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone())


def buscar_usuario_por_id(uid: int) -> dict | None:
    return _row(get_db().execute("SELECT * FROM usuarios WHERE id=?", (uid,)).fetchone())


def atualizar_usuario(uid: int, nome: str, email: str, departamento: str, ramal: str = None) -> dict | None:
    conn = get_db()
    with conn:
        conn.execute(
            "UPDATE usuarios SET nome=?, email=?, departamento=?, ramal=? WHERE id=?",
            (nome, email, departamento, ramal, uid),
        )
    return buscar_usuario_por_id(uid)


def deletar_usuario(uid: int) -> bool:
    conn = get_db()
    with conn:
        cur = conn.execute("DELETE FROM usuarios WHERE id=?", (uid,))
    return cur.rowcount > 0


# ── Tickets ───────────────────────────────────────────────────────────────────

def criar_ticket(
    titulo: str,
    descricao: str,
    nivel: str = None,
    categoria: str = None,
    confianca: int = None,
    criado_por: int = None,
    status: str = "ABERTO",
    resolucao: str = None,
    auto_resolvido: bool = False,
    sugestao_ia: str = None,
    acao_ia: str = None,
    tempo_estimado: str = None,
) -> dict:
    resolvido_em = _now() if status == "RESOLVIDO" else None
    conn = get_db()
    with conn:
        cur = conn.execute(
            """INSERT INTO tickets
               (titulo, descricao, status, nivel, categoria, confianca, criado_por,
                resolucao, auto_resolvido, sugestao_ia, acao_ia, tempo_estimado, resolvido_em)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (titulo, descricao, status, nivel, categoria, confianca, criado_por,
             resolucao, 1 if auto_resolvido else 0,
             sugestao_ia, acao_ia, tempo_estimado, resolvido_em),
        )
    return buscar_ticket(cur.lastrowid)


def buscar_ticket(ticket_id: int) -> dict | None:
    row = get_db().execute("""
        SELECT t.*,
               u.nome  AS solicitante_nome,
               u.email AS solicitante_email
        FROM tickets t
        LEFT JOIN usuarios u ON t.criado_por = u.id
        WHERE t.id = ?
    """, (ticket_id,)).fetchone()
    return _row(row)


def listar_fila(nivel: str, statuses: list[str] = None) -> list[dict]:
    if statuses is None:
        statuses = ["ABERTO", "EM_ATENDIMENTO"]
    ph = ",".join("?" * len(statuses))
    return _rows(
        get_db().execute(
            f"SELECT * FROM tickets WHERE nivel=? AND status IN ({ph}) ORDER BY criado_em ASC",
            [nivel] + statuses,
        ).fetchall()
    )


def listar_tickets_recentes(limit: int = 20) -> list[dict]:
    return _rows(
        get_db().execute(
            "SELECT * FROM tickets ORDER BY criado_em DESC LIMIT ?", (limit,)
        ).fetchall()
    )


def atualizar_ticket(ticket_id: int, **kwargs) -> dict | None:
    if not kwargs:
        return buscar_ticket(ticket_id)
    if kwargs.get("status") == "RESOLVIDO":
        kwargs.setdefault("resolvido_em", _now())
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [ticket_id]
    conn = get_db()
    with conn:
        conn.execute(f"UPDATE tickets SET {sets} WHERE id=?", vals)
    return buscar_ticket(ticket_id)


def stats_tickets() -> dict:
    row = get_db().execute("""
        SELECT
            COUNT(*)                                                          AS total,
            SUM(CASE WHEN status='ABERTO'        THEN 1 ELSE 0 END)          AS abertos,
            SUM(CASE WHEN status='EM_ATENDIMENTO' THEN 1 ELSE 0 END)         AS em_atendimento,
            SUM(CASE WHEN status='RESOLVIDO'     THEN 1 ELSE 0 END)          AS resolvidos,
            SUM(CASE WHEN auto_resolvido=1       THEN 1 ELSE 0 END)          AS auto_resolvidos,
            SUM(CASE WHEN nivel='N1' AND status NOT IN ('RESOLVIDO','FECHADO') THEN 1 ELSE 0 END) AS fila_n1,
            SUM(CASE WHEN nivel='N2' AND status NOT IN ('RESOLVIDO','FECHADO') THEN 1 ELSE 0 END) AS fila_n2
        FROM tickets
    """).fetchone()
    return dict(row) if row else {}


if __name__ == "__main__":
    init_db()
    print(f"DB inicializado em {DB_PATH}")
