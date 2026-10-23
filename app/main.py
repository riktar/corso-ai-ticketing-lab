"""API REST del ticketing interno (versione base, senza IA)."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException

from app import config
from app.db import get_conn, init_db
from app.models import (
    CambioStato,
    Commento,
    CommentoCreate,
    Stato,
    Ticket,
    TicketCreate,
    TicketUpdate,
)

logging.basicConfig(level=config.LOG_LEVEL)
log = logging.getLogger("ticketing")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Ticketing interno", version="0.1.0", lifespan=lifespan)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_ticket(row) -> Ticket:
    return Ticket(**dict(row))


def _get_ticket_or_404(conn, ticket_id: int):
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Ticket non trovato")
    return row


def _valida_testi_ticket(titolo: Optional[str], descrizione: Optional[str]) -> None:
    if titolo is not None:
        if len(titolo.strip()) < 5 or len(titolo) > 120:
            raise HTTPException(status_code=422, detail="Il titolo deve avere tra 5 e 120 caratteri")
    if descrizione is not None:
        if not descrizione.strip():
            raise HTTPException(status_code=422, detail="La descrizione non puo' essere vuota")
        if len(descrizione) > 5000:
            raise HTTPException(status_code=422, detail="La descrizione supera i 5000 caratteri")


@app.post("/tickets", response_model=Ticket, status_code=201)
def crea_ticket(payload: TicketCreate):
    log.info("Nuovo ticket ricevuto: %s", payload.model_dump())

    _valida_testi_ticket(payload.titolo, payload.descrizione)
    if "@" not in payload.email_richiedente:
        raise HTTPException(status_code=422, detail="Email del richiedente non valida")

    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO tickets
               (titolo, descrizione, email_richiedente, categoria, priorita, stato, creato_il, aggiornato_il)
               VALUES (?, ?, ?, ?, ?, 'aperto', ?, ?)""",
            (
                payload.titolo.strip(),
                payload.descrizione.strip(),
                payload.email_richiedente,
                payload.categoria.value if payload.categoria else None,
                payload.priorita.value if payload.priorita else None,
                now,
                now,
            ),
        )
        row = _get_ticket_or_404(conn, cur.lastrowid)
    return _row_to_ticket(row)


@app.get("/tickets/{ticket_id}", response_model=Ticket)
def leggi_ticket(ticket_id: int):
    with get_conn() as conn:
        return _row_to_ticket(_get_ticket_or_404(conn, ticket_id))


@app.get("/tickets", response_model=List[Ticket])
def elenca_ticket(stato: Optional[Stato] = None, q: Optional[str] = None):
    query = "SELECT * FROM tickets WHERE 1=1"
    params: list = []
    if stato:
        query += " AND stato = ?"
        params.append(stato.value)
    if q:
        query += f" AND (titolo LIKE '%{q}%' OR descrizione LIKE '%{q}%')"
    query += " ORDER BY id DESC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_ticket(r) for r in rows]


@app.patch("/tickets/{ticket_id}", response_model=Ticket)
def aggiorna_ticket(ticket_id: int, payload: TicketUpdate):
    _valida_testi_ticket(payload.titolo, payload.descrizione)

    campi = {k: (v.value if hasattr(v, "value") else v) for k, v in payload.model_dump(exclude_none=True).items()}
    with get_conn() as conn:
        _get_ticket_or_404(conn, ticket_id)
        if campi:
            assegnazioni = ", ".join(f"{k} = ?" for k in campi)
            conn.execute(
                f"UPDATE tickets SET {assegnazioni}, aggiornato_il = ? WHERE id = ?",
                (*campi.values(), _now(), ticket_id),
            )
        row = _get_ticket_or_404(conn, ticket_id)
    return _row_to_ticket(row)


@app.post("/tickets/{ticket_id}/stato", response_model=Ticket)
def cambia_stato(ticket_id: int, payload: CambioStato):
    with get_conn() as conn:
        row = _get_ticket_or_404(conn, ticket_id)
        attuale = row["stato"]
        if payload.stato.value not in config.TRANSIZIONI.get(attuale, []):
            raise HTTPException(
                status_code=409,
                detail=f"Transizione non consentita: {attuale} -> {payload.stato.value}",
            )
        conn.execute(
            "UPDATE tickets SET stato = ?, aggiornato_il = ? WHERE id = ?",
            (payload.stato.value, _now(), ticket_id),
        )
        row = _get_ticket_or_404(conn, ticket_id)
    return _row_to_ticket(row)


@app.post("/tickets/{ticket_id}/commenti", response_model=Commento, status_code=201)
def aggiungi_commento(ticket_id: int, payload: CommentoCreate):
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO commenti (ticket_id, autore, testo, creato_il) VALUES (?, ?, ?, ?)",
            (ticket_id, payload.autore, payload.testo, now),
        )
        row = conn.execute("SELECT * FROM commenti WHERE id = ?", (cur.lastrowid,)).fetchone()
    return Commento(**dict(row))


@app.get("/tickets/{ticket_id}/commenti", response_model=List[Commento])
def elenca_commenti(ticket_id: int):
    with get_conn() as conn:
        _get_ticket_or_404(conn, ticket_id)
        rows = conn.execute(
            "SELECT * FROM commenti WHERE ticket_id = ? ORDER BY id", (ticket_id,)
        ).fetchall()
    return [Commento(**dict(r)) for r in rows]


@app.get("/stats")
def statistiche():
    with get_conn() as conn:
        per_stato = conn.execute("SELECT stato, COUNT(*) AS n FROM tickets GROUP BY stato").fetchall()
        per_categoria = conn.execute(
            "SELECT COALESCE(categoria, 'non_classificato') AS categoria, COUNT(*) AS n FROM tickets GROUP BY categoria"
        ).fetchall()
    return {
        "per_stato": {r["stato"]: r["n"] for r in per_stato},
        "per_categoria": {r["categoria"]: r["n"] for r in per_categoria},
    }


@app.delete("/tickets/{ticket_id}", status_code=204)
def cancella_ticket(ticket_id: int, x_admin_token: Optional[str] = Header(default=None)):
    if x_admin_token != config.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Operazione non autorizzata")
    with get_conn() as conn:
        _get_ticket_or_404(conn, ticket_id)
        conn.execute("DELETE FROM commenti WHERE ticket_id = ?", (ticket_id,))
        conn.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
