import sqlite3
import threading
from datetime import datetime, timezone, timedelta
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


def buscar_tickets_avancado(texto: str = None, categoria: str = None, nivel=None,
                            status=None, auto_resolvido: bool = None,
                            periodo_dias: int = None, limit: int = 50) -> list[dict]:
    """Busca por filtros estruturados (usada pela busca em linguagem natural).

    Todos os filtros são opcionais; apenas os não-nulos entram no WHERE.
    `nivel` e `status` aceitam str ou lista. `texto` faz LIKE em
    título/descrição/categoria/nome/e-mail do solicitante.
    """
    where, params = [], []
    if texto:
        like = f"%{texto}%"
        where.append(
            "(t.titulo LIKE ? OR t.descricao LIKE ? OR t.categoria LIKE ? "
            "OR u.nome LIKE ? OR u.email LIKE ?)"
        )
        params += [like, like, like, like, like]
    if categoria:
        where.append("t.categoria = ?")
        params.append(categoria)
    if nivel:
        nivel = [nivel] if isinstance(nivel, str) else list(nivel)
        where.append("t.nivel IN (" + ",".join("?" * len(nivel)) + ")")
        params += nivel
    if status:
        status = [status] if isinstance(status, str) else list(status)
        where.append("t.status IN (" + ",".join("?" * len(status)) + ")")
        params += status
    if auto_resolvido is not None:
        where.append("t.auto_resolvido = ?")
        params.append(1 if auto_resolvido else 0)
    if periodo_dias:
        where.append("t.criado_em >= datetime('now', ?)")
        params.append(f"-{int(periodo_dias)} days")
    sql = (
        "SELECT t.*, u.nome AS solicitante_nome, u.email AS solicitante_email "
        "FROM tickets t LEFT JOIN usuarios u ON t.criado_por = u.id"
    )
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY t.criado_em DESC LIMIT ?"
    params.append(limit)
    return _rows(get_db().execute(sql, params).fetchall())


def buscar_tickets(termo: str, limit: int = 50) -> list[dict]:
    """Busca tickets por ID (INC000123 ou 123), título, descrição, categoria,
    ou nome/e-mail do solicitante. Case-insensitive (ASCII)."""
    termo = (termo or "").strip()
    if not termo:
        return []
    like = f"%{termo}%"
    params = [like, like, like, like, like]
    sql = """
        SELECT t.*,
               u.nome  AS solicitante_nome,
               u.email AS solicitante_email
        FROM tickets t
        LEFT JOIN usuarios u ON t.criado_por = u.id
        WHERE t.titulo    LIKE ?
           OR t.descricao LIKE ?
           OR t.categoria LIKE ?
           OR u.nome      LIKE ?
           OR u.email     LIKE ?
    """
    # Casa também por ID quando o termo contém dígitos (ex.: "INC000007" -> 7)
    digitos = "".join(ch for ch in termo if ch.isdigit())
    if digitos:
        sql += " OR t.id = ?"
        params.append(int(digitos))
    sql += " ORDER BY t.criado_em DESC LIMIT ?"
    params.append(limit)
    return _rows(get_db().execute(sql, params).fetchall())


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


def listar_tickets_graficos(dias: int | None = None) -> list[dict]:
    sql = (
        "SELECT id, status, nivel, categoria, auto_resolvido, confianca, "
        "criado_em, resolvido_em FROM tickets"
    )
    params: list = []
    if dias:
        sql += " WHERE criado_em >= datetime('now', ?)"
        params.append(f"-{dias} days")
    sql += " ORDER BY criado_em ASC"
    return _rows(get_db().execute(sql, params).fetchall())


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


# ── Seed de demonstração ────────────────────────────────────────────────────────

def _dt_dias_atras(dias: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _inserir_ticket_seed(t: dict) -> None:
    """Insere um ticket de seed com criado_em/resolvido_em derivados de dias_atras."""
    criado = _dt_dias_atras(t.get("dias_atras", 0))
    status = t.get("status", "ABERTO")
    encerrado = status in ("RESOLVIDO", "FECHADO")
    resolvido_em = criado if encerrado else None
    resolucao = t.get("sugestao_ia") if encerrado else None
    usuario = buscar_usuario_por_email(t["email"]) if t.get("email") else None
    criado_por = usuario["id"] if usuario else None
    conn = get_db()
    with conn:
        conn.execute(
            """INSERT INTO tickets
               (titulo, descricao, status, nivel, categoria, confianca, criado_por,
                resolucao, auto_resolvido, sugestao_ia, acao_ia, tempo_estimado,
                criado_em, resolvido_em)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (t["titulo"], t["descricao"], status, t.get("nivel"), t.get("categoria"),
             t.get("confianca"), criado_por, resolucao,
             1 if t.get("auto_resolvido") else 0,
             t.get("sugestao_ia"), t.get("acao_ia"), t.get("tempo_estimado"),
             criado, resolvido_em),
        )


def seed_demo(force: bool = False) -> bool:
    """Popula a massa de demonstração (banco efêmero).

    Reseta para um estado conhecido (apaga tickets/usuários e recria) apenas
    quando o total de tickets < 50, ou quando force=True. Idempotente depois:
    chamadas seguintes não duplicam dados nem apagam chamados criados na demo.
    """
    import seed_data

    total = stats_tickets().get("total") or 0
    if total >= 50 and not force:
        return False

    conn = get_db()
    with conn:
        conn.execute("DELETE FROM tickets")
        conn.execute("DELETE FROM usuarios")
    # Reinicia os IDs (sqlite_sequence só existe após o 1º INSERT com AUTOINCREMENT)
    try:
        with conn:
            conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('tickets','usuarios')")
    except sqlite3.OperationalError:
        pass

    for u in seed_data.USUARIOS:
        criar_usuario(u["nome"], u["email"], u["departamento"], u.get("ramal"))
    for t in seed_data.TICKETS:
        _inserir_ticket_seed(t)
    return True


if __name__ == "__main__":
    init_db()
    inserido = seed_demo(force=True)
    print(f"DB inicializado em {DB_PATH}")
    print(f"Seed aplicado: {inserido} | total de tickets: {stats_tickets().get('total')}")
