import json
import secrets
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

import analytics
import kb_data

DB_PATH = Path(__file__).parent / "belgo_ti.db"
_local = threading.local()
_seed_lock = threading.Lock()

_DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT NOT NULL,
    email        TEXT NOT NULL UNIQUE,
    departamento TEXT NOT NULL,
    ramal        TEXT,
    senha        TEXT,
    is_admin     INTEGER NOT NULL DEFAULT 0,
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
    tempo_estimado TEXT,
    canal          TEXT DEFAULT 'PORTAL',
    sla_horas      INTEGER,
    sla_prazo      TEXT,
    csat_nota      INTEGER,
    csat_comentario TEXT,
    feedback_humano TEXT,
    kb_artigo      TEXT,
    ia_nivel_sugerido     TEXT,
    ia_categoria_sugerida TEXT
);

-- Base de conhecimento (KB): artigos editáveis (CRUD). A citação automática no
-- chamado usa kb_por_categoria(); os passos são guardados como JSON.
CREATE TABLE IF NOT EXISTS kb_artigos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo        TEXT UNIQUE,
    titulo        TEXT NOT NULL,
    categoria     TEXT,
    passos        TEXT,
    ativo         INTEGER NOT NULL DEFAULT 1,
    criado_em     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    atualizado_em TEXT
);

-- Registro do modo sombra (shadow mode): a IA classifica em paralelo ao humano
-- sem atuar. Tabela própria para não poluir as filas/buscas/estatísticas reais.
CREATE TABLE IF NOT EXISTS shadow_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao        TEXT NOT NULL,
    ia_nivel         TEXT,
    ia_categoria     TEXT,
    ia_confianca     INTEGER,
    humano_nivel     TEXT,
    humano_categoria TEXT,
    criado_em        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_tickets_status    ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_nivel     ON tickets(nivel);
CREATE INDEX IF NOT EXISTS idx_tickets_criado_em ON tickets(criado_em DESC);
"""

# Colunas adicionadas à tabela tickets após a 1ª versão — migração defensiva
# (bancos já existentes não recebem colunas via CREATE TABLE IF NOT EXISTS).
_TICKETS_COLS_NOVAS = [
    ("canal", "TEXT DEFAULT 'PORTAL'"),
    ("sla_horas", "INTEGER"),
    ("sla_prazo", "TEXT"),
    ("csat_nota", "INTEGER"),
    ("csat_comentario", "TEXT"),
    ("feedback_humano", "TEXT"),
    ("kb_artigo", "TEXT"),
    ("ia_nivel_sugerido", "TEXT"),
    ("ia_categoria_sugerida", "TEXT"),
]


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
    # Migração defensiva: bancos antigos não têm senha/is_admin
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(usuarios)").fetchall()}
    if "senha" not in cols:
        conn.execute("ALTER TABLE usuarios ADD COLUMN senha TEXT")
    if "is_admin" not in cols:
        conn.execute("ALTER TABLE usuarios ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    # Migração defensiva: colunas novas de tickets (SLA, canal, CSAT, KB, etc.)
    tcols = {r["name"] for r in conn.execute("PRAGMA table_info(tickets)").fetchall()}
    for nome, tipo in _TICKETS_COLS_NOVAS:
        if nome not in tcols:
            conn.execute(f"ALTER TABLE tickets ADD COLUMN {nome} {tipo}")
    conn.commit()
    # KB é dado de referência: garante os artigos-base mesmo sem o seed de demo.
    seed_kb()


# Sem caracteres ambíguos (0/O/1/l/I) para senhas legíveis no olhinho
_SENHA_ALFABETO = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def gerar_senha(n: int = 8) -> str:
    return "".join(secrets.choice(_SENHA_ALFABETO) for _ in range(n))


def _row(row) -> dict | None:
    return dict(row) if row else None


def _rows(rows) -> list[dict]:
    return [dict(r) for r in rows]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Usuários ──────────────────────────────────────────────────────────────────

def criar_usuario(nome: str, email: str, departamento: str, ramal: str = None,
                  senha: str = None, is_admin: bool = False) -> dict:
    conn = get_db()
    with conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, email, departamento, ramal, senha, is_admin) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (nome, email, departamento, ramal, senha, 1 if is_admin else 0),
        )
    return buscar_usuario_por_id(cur.lastrowid)


def autenticar(email: str, senha: str) -> dict | None:
    row = get_db().execute(
        "SELECT * FROM usuarios WHERE email = ? AND senha = ?",
        ((email or "").strip().lower(), senha or ""),
    ).fetchone()
    return _row(row)


def listar_usuarios() -> list[dict]:
    return _rows(get_db().execute("SELECT * FROM usuarios ORDER BY nome").fetchall())


def buscar_usuario_por_email(email: str) -> dict | None:
    return _row(get_db().execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone())


def buscar_usuario_por_id(uid: int) -> dict | None:
    return _row(get_db().execute("SELECT * FROM usuarios WHERE id=?", (uid,)).fetchone())


def atualizar_usuario(uid: int, nome: str, email: str, departamento: str, ramal: str = None,
                      senha: str = None, is_admin: bool = None) -> dict | None:
    conn = get_db()
    sets = ["nome=?", "email=?", "departamento=?", "ramal=?"]
    vals = [nome, email, departamento, ramal]
    if senha is not None:
        sets.append("senha=?")
        vals.append(senha)
    if is_admin is not None:
        sets.append("is_admin=?")
        vals.append(1 if is_admin else 0)
    vals.append(uid)
    with conn:
        conn.execute(f"UPDATE usuarios SET {', '.join(sets)} WHERE id=?", vals)
    return buscar_usuario_por_id(uid)


def deletar_usuario(uid: int) -> bool:
    conn = get_db()
    with conn:
        # Desvincula chamados do solicitante antes de remover (evita violação de FK)
        conn.execute("UPDATE tickets SET criado_por=NULL WHERE criado_por=?", (uid,))
        conn.execute("UPDATE tickets SET atribuido_para=NULL WHERE atribuido_para=?", (uid,))
        cur = conn.execute("DELETE FROM usuarios WHERE id=?", (uid,))
    return cur.rowcount > 0


# ── Tickets ───────────────────────────────────────────────────────────────────

def _add_horas(iso: str, horas: int) -> str:
    base = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (base + timedelta(hours=horas)).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    canal: str = "PORTAL",
    kb_artigo: str = None,
    ia_nivel_sugerido: str = None,
    ia_categoria_sugerida: str = None,
    criado_em: str = None,
) -> dict:
    criado_em = criado_em or _now()
    resolvido_em = criado_em if status == "RESOLVIDO" else None
    # SLA derivado do nível (auto-resolvidos pela IA = imediato).
    sla_horas = analytics.sla_horas_para(nivel, categoria, auto_resolvido)
    sla_prazo = _add_horas(criado_em, sla_horas) if sla_horas else criado_em
    # KB sugerida pela categoria, quando não informada explicitamente.
    if kb_artigo is None:
        artigo = kb_por_categoria(categoria)
        kb_artigo = artigo["id"] if artigo else None
    # Provenance: registra o que a IA sugeriu (default = a própria classificação).
    if ia_nivel_sugerido is None:
        ia_nivel_sugerido = nivel
    if ia_categoria_sugerida is None:
        ia_categoria_sugerida = categoria
    conn = get_db()
    with conn:
        cur = conn.execute(
            """INSERT INTO tickets
               (titulo, descricao, status, nivel, categoria, confianca, criado_por,
                resolucao, auto_resolvido, sugestao_ia, acao_ia, tempo_estimado,
                criado_em, resolvido_em, canal, sla_horas, sla_prazo, kb_artigo,
                ia_nivel_sugerido, ia_categoria_sugerida)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (titulo, descricao, status, nivel, categoria, confianca, criado_por,
             resolucao, 1 if auto_resolvido else 0,
             sugestao_ia, acao_ia, tempo_estimado, criado_em, resolvido_em,
             canal, sla_horas, sla_prazo, kb_artigo,
             ia_nivel_sugerido, ia_categoria_sugerida),
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


def stats_roi() -> dict:
    """Agregados crus para o painel de Valor/ROI (ver analytics.calcular_roi)."""
    row = get_db().execute("""
        SELECT
            COUNT(*)                                                       AS total,
            SUM(CASE WHEN auto_resolvido=1 THEN 1 ELSE 0 END)             AS auto_resolvidos,
            SUM(CASE WHEN auto_resolvido=1
                      AND criado_em >= datetime('now','-30 days')
                     THEN 1 ELSE 0 END)                                   AS auto_resolvidos_30d,
            SUM(CASE WHEN status IN ('RESOLVIDO','FECHADO') THEN 1 ELSE 0 END) AS resolvidos,
            AVG(csat_nota)                                                AS csat_media,
            SUM(CASE WHEN csat_nota IS NOT NULL THEN 1 ELSE 0 END)        AS csat_n,
            AVG(CASE WHEN auto_resolvido=0 AND resolvido_em IS NOT NULL
                     THEN (julianday(resolvido_em)-julianday(criado_em))*24 END) AS mttr_manual_horas
        FROM tickets
    """).fetchone()
    return dict(row) if row else {}


def stats_canais() -> dict:
    """Contagem de chamados por canal de entrada (multicanal)."""
    rows = get_db().execute(
        "SELECT COALESCE(canal,'PORTAL') AS canal, COUNT(*) AS n "
        "FROM tickets GROUP BY COALESCE(canal,'PORTAL') ORDER BY n DESC"
    ).fetchall()
    return {r["canal"]: r["n"] for r in rows}


def stats_feedback() -> dict:
    """Contagem de feedback humano (👍/👎) — acurácia percebida do agente."""
    row = get_db().execute("""
        SELECT
            SUM(CASE WHEN feedback_humano='POSITIVO' THEN 1 ELSE 0 END) AS positivos,
            SUM(CASE WHEN feedback_humano='NEGATIVO' THEN 1 ELSE 0 END) AS negativos
        FROM tickets
    """).fetchone()
    d = dict(row) if row else {}
    pos = int(d.get("positivos") or 0)
    neg = int(d.get("negativos") or 0)
    total = pos + neg
    d["total"] = total
    d["acuracia"] = (100.0 * pos / total) if total else None
    return d


def stats_shadow() -> dict:
    """Concordância IA × humano no modo sombra (a partir de shadow_log)."""
    row = get_db().execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN ia_nivel = humano_nivel THEN 1 ELSE 0 END)         AS conc_nivel,
            SUM(CASE WHEN ia_categoria = humano_categoria THEN 1 ELSE 0 END) AS conc_categoria
        FROM shadow_log
    """).fetchone()
    d = dict(row) if row else {}
    total = int(d.get("total") or 0)
    d["total"] = total
    d["concordancia_nivel"] = (100.0 * int(d.get("conc_nivel") or 0) / total) if total else None
    d["concordancia_categoria"] = (100.0 * int(d.get("conc_categoria") or 0) / total) if total else None
    return d


def listar_shadow(limit: int = 100) -> list[dict]:
    return _rows(get_db().execute(
        "SELECT * FROM shadow_log ORDER BY criado_em DESC LIMIT ?", (limit,)
    ).fetchall())


def registrar_feedback(ticket_id: int, valor: str) -> dict | None:
    """Registra o feedback humano sobre a triagem ('POSITIVO' ou 'NEGATIVO')."""
    if valor not in ("POSITIVO", "NEGATIVO"):
        return buscar_ticket(ticket_id)
    return atualizar_ticket(ticket_id, feedback_humano=valor)


def registrar_csat(ticket_id: int, nota: int, comentario: str = None) -> dict | None:
    """Registra a avaliação de satisfação (CSAT 1–5) do solicitante."""
    nota = max(1, min(5, int(nota)))
    return atualizar_ticket(ticket_id, csat_nota=nota, csat_comentario=comentario)


# ── Base de conhecimento (KB) — CRUD ─────────────────────────────────────────────

def _kb_row(row) -> dict | None:
    """Normaliza uma linha de kb_artigos, parseando os passos (JSON) para lista."""
    if not row:
        return None
    d = dict(row)
    try:
        d["passos"] = json.loads(d.get("passos") or "[]")
    except (json.JSONDecodeError, TypeError):
        d["passos"] = []
    return d


def listar_kb(incluir_inativos: bool = True) -> list[dict]:
    sql = "SELECT * FROM kb_artigos"
    if not incluir_inativos:
        sql += " WHERE ativo = 1"
    sql += " ORDER BY codigo"
    return [_kb_row(r) for r in get_db().execute(sql).fetchall()]


def buscar_kb(pk: int) -> dict | None:
    return _kb_row(get_db().execute("SELECT * FROM kb_artigos WHERE id=?", (pk,)).fetchone())


def kb_por_categoria(categoria: str | None) -> dict | None:
    """1º artigo ATIVO da categoria, no formato {id: codigo, titulo, passos}.

    Mantém compatibilidade com os call-sites de citação (criar_ticket, ui).
    """
    if not categoria:
        return None
    row = get_db().execute(
        "SELECT * FROM kb_artigos WHERE categoria=? AND ativo=1 ORDER BY codigo LIMIT 1",
        (categoria,),
    ).fetchone()
    art = _kb_row(row)
    if not art:
        return None
    return {"id": art["codigo"], "titulo": art["titulo"], "passos": art["passos"]}


def proximo_codigo_kb() -> str:
    """Próximo código KB sequencial (KB0001, KB0002, …)."""
    rows = get_db().execute("SELECT codigo FROM kb_artigos").fetchall()
    maxn = 0
    for r in rows:
        cod = (r["codigo"] or "").upper()
        if cod.startswith("KB"):
            try:
                maxn = max(maxn, int(cod[2:]))
            except ValueError:
                pass
    return f"KB{maxn + 1:04d}"


def criar_kb(titulo: str, categoria: str = None, passos: list = None,
             codigo: str = None, ativo: bool = True) -> dict:
    codigo = (codigo or "").strip() or proximo_codigo_kb()
    passos_json = json.dumps(passos or [], ensure_ascii=False)
    conn = get_db()
    with conn:
        cur = conn.execute(
            "INSERT INTO kb_artigos (codigo, titulo, categoria, passos, ativo) "
            "VALUES (?, ?, ?, ?, ?)",
            (codigo, titulo, categoria, passos_json, 1 if ativo else 0),
        )
    return buscar_kb(cur.lastrowid)


def atualizar_kb(pk: int, **kwargs) -> dict | None:
    if "passos" in kwargs and isinstance(kwargs["passos"], list):
        kwargs["passos"] = json.dumps(kwargs["passos"], ensure_ascii=False)
    if "ativo" in kwargs:
        kwargs["ativo"] = 1 if kwargs["ativo"] else 0
    kwargs["atualizado_em"] = _now()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [pk]
    conn = get_db()
    with conn:
        conn.execute(f"UPDATE kb_artigos SET {sets} WHERE id=?", vals)
    return buscar_kb(pk)


def deletar_kb(pk: int) -> bool:
    conn = get_db()
    with conn:
        cur = conn.execute("DELETE FROM kb_artigos WHERE id=?", (pk,))
    return cur.rowcount > 0


def contar_resolvidos_por_kb() -> dict:
    """{codigo: nº de chamados resolvidos citando este KB}."""
    rows = get_db().execute(
        "SELECT kb_artigo AS codigo, COUNT(*) AS n FROM tickets "
        "WHERE kb_artigo IS NOT NULL GROUP BY kb_artigo"
    ).fetchall()
    return {r["codigo"]: r["n"] for r in rows}


def seed_kb() -> bool:
    """Popula os artigos-base de KB a partir de kb_data.KB_ARTIGOS (idempotente).

    Só semeia quando a tabela está vazia, sob lock com recheck (mesma proteção de
    concorrência do seed_demo). Assim, artigos editados/excluídos pelo admin não
    ressurgem a cada init_db.
    """
    with _seed_lock:
        total = get_db().execute("SELECT COUNT(*) AS n FROM kb_artigos").fetchone()["n"]
        if total:
            return False
        for cat, art in kb_data.KB_ARTIGOS.items():
            criar_kb(art["titulo"], categoria=cat, passos=art.get("passos"),
                     codigo=art.get("id"), ativo=True)
        return True


# ── Seed de demonstração ────────────────────────────────────────────────────────

def _dt_dias_atras(dias: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ")


# Canais de entrada distribuídos de forma realista (maioria portal/e-mail).
_CANAL_CICLO = ["PORTAL", "EMAIL", "PORTAL", "TEAMS", "PORTAL",
                "WHATSAPP", "EMAIL", "PORTAL", "TEAMS", "EMAIL"]
# Notas de CSAT (1–5) variadas, com viés positivo, para os chamados encerrados.
_CSAT_CICLO = [5, 4, 5, 5, 4, 3, 5, 4, 5, 4, 5, 3]


def _inserir_ticket_seed(t: dict, idx: int = 0) -> None:
    """Insere um ticket de seed com criado_em/resolvido_em derivados de dias_atras
    e os campos de SLA/canal/CSAT/feedback/KB preenchidos de forma realista."""
    criado = _dt_dias_atras(t.get("dias_atras", 0))
    status = t.get("status", "ABERTO")
    encerrado = status in ("RESOLVIDO", "FECHADO")
    resolvido_em = criado if encerrado else None
    resolucao = t.get("sugestao_ia") if encerrado else None
    usuario = buscar_usuario_por_email(t["email"]) if t.get("email") else None
    criado_por = usuario["id"] if usuario else None
    nivel = t.get("nivel")
    categoria = t.get("categoria")
    auto = bool(t.get("auto_resolvido"))

    canal = t.get("canal") or _CANAL_CICLO[idx % len(_CANAL_CICLO)]
    sla_horas = analytics.sla_horas_para(nivel, categoria, auto)
    sla_prazo = _add_horas(criado, sla_horas) if sla_horas else criado
    artigo = kb_por_categoria(categoria) if auto else None
    kb_artigo = artigo["id"] if artigo else None
    # CSAT só nos chamados encerrados (e nem todos avaliam: ~75%).
    csat = _CSAT_CICLO[idx % len(_CSAT_CICLO)] if (encerrado and idx % 4 != 3) else None
    # Feedback humano sobre a triagem automática (amostra).
    feedback = None
    if auto:
        feedback = "NEGATIVO" if idx % 9 == 0 else "POSITIVO"

    conn = get_db()
    with conn:
        conn.execute(
            """INSERT INTO tickets
               (titulo, descricao, status, nivel, categoria, confianca, criado_por,
                resolucao, auto_resolvido, sugestao_ia, acao_ia, tempo_estimado,
                criado_em, resolvido_em, canal, sla_horas, sla_prazo, csat_nota,
                feedback_humano, kb_artigo, ia_nivel_sugerido, ia_categoria_sugerida)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (t["titulo"], t["descricao"], status, nivel, categoria,
             t.get("confianca"), criado_por, resolucao,
             1 if auto else 0,
             t.get("sugestao_ia"), t.get("acao_ia"), t.get("tempo_estimado"),
             criado, resolvido_em, canal, sla_horas, sla_prazo, csat,
             feedback, kb_artigo, nivel, categoria),
        )


def _inserir_shadow_seed(s: dict) -> None:
    criado = _dt_dias_atras(s.get("dias_atras", 0))
    conn = get_db()
    with conn:
        conn.execute(
            """INSERT INTO shadow_log
               (descricao, ia_nivel, ia_categoria, ia_confianca,
                humano_nivel, humano_categoria, criado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (s["descricao"], s.get("ia_nivel"), s.get("ia_categoria"),
             s.get("ia_confianca"), s.get("humano_nivel"),
             s.get("humano_categoria"), criado),
        )


def seed_demo(force: bool = False) -> bool:
    """Popula a massa de demonstração (banco efêmero).

    Reseta para um estado conhecido (apaga tickets/usuários e recria) apenas
    quando o total de tickets < 50, ou quando force=True. Idempotente depois:
    chamadas seguintes não duplicam dados nem apagam chamados criados na demo.

    O lock serializa execuções concorrentes: no Streamlit cada rerun/sessão roda
    em uma thread própria (com conexão própria via threading.local). Sem o lock,
    dois primeiros carregamentos simultâneos passavam juntos pelo check de total,
    entrelaçavam os DELETE/INSERT e colidiam no UNIQUE de usuarios.email.
    """
    import seed_data

    with _seed_lock:
        # Reverifica dentro do lock: se outra thread já semeou, esta não repete.
        total = stats_tickets().get("total") or 0
        if total >= 50 and not force:
            return False

        conn = get_db()
        with conn:
            conn.execute("DELETE FROM tickets")
            conn.execute("DELETE FROM usuarios")
            conn.execute("DELETE FROM shadow_log")
            conn.execute("DELETE FROM kb_artigos")
        # Reinicia os IDs (sqlite_sequence só existe após o 1º INSERT com AUTOINCREMENT)
        try:
            with conn:
                conn.execute(
                    "DELETE FROM sqlite_sequence "
                    "WHERE name IN ('tickets','usuarios','shadow_log','kb_artigos')"
                )
        except sqlite3.OperationalError:
            pass

        for u in seed_data.USUARIOS:
            criar_usuario(
                u["nome"], u["email"], u["departamento"], u.get("ramal"),
                senha=u.get("senha") or gerar_senha(),
                is_admin=u.get("is_admin", False),
            )
        # KB antes dos tickets: _inserir_ticket_seed cita via kb_por_categoria.
        # (criar_kb não adquire _seed_lock, então é seguro chamar aqui dentro.)
        for cat, art in kb_data.KB_ARTIGOS.items():
            criar_kb(art["titulo"], categoria=cat, passos=art.get("passos"),
                     codigo=art.get("id"), ativo=True)
        for i, t in enumerate(seed_data.TICKETS):
            _inserir_ticket_seed(t, i)
        for s in getattr(seed_data, "SHADOW", []):
            _inserir_shadow_seed(s)
        return True


if __name__ == "__main__":
    init_db()
    inserido = seed_demo(force=True)
    print(f"DB inicializado em {DB_PATH}")
    print(f"Seed aplicado: {inserido} | total de tickets: {stats_tickets().get('total')}")
