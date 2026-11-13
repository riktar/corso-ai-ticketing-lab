"""Log degli esiti, senza contenuti del ticket, output o dettagli degli errori."""

import json
import logging
from pathlib import Path

import pytest

from app.classificazione.provider import ProviderNonDisponibile, TimeoutProvider
from app.classificazione.provider_simulato import ProviderSimulato
from app.classificazione.servizio import classifica_ticket


@pytest.mark.parametrize("caso, motivo", [
    ("G01", None), ("G05", "output_non_valido"), ("G20", "confidenza_bassa"),
    ("timeout", "timeout"), ("indisponibile", "provider_non_disponibile"),
])
def test_log_esito_e_latenza_senza_dati_personali(caplog, caso, motivo):
    radice = Path(__file__).resolve().parents[1]
    risposte = json.loads((radice / "data/risposte_registrate.json").read_text(encoding="utf-8"))["risposte"]
    errore = {"timeout": TimeoutProvider("DETTAGLIO_RISERVATO"), "indisponibile": ProviderNonDisponibile("DETTAGLIO_RISERVATO")}.get(caso)
    provider = ProviderSimulato(output=risposte.get(caso, ""), errore=errore)
    with caplog.at_level(logging.INFO, logger="app.classificazione.servizio"):
        esito = classifica_ticket("TITOLO_RISERVATO", "utente@example.com 333 1234567", provider)
    registrazioni = [r for r in caplog.records if r.name == "app.classificazione.servizio"]
    assert len(registrazioni) == 1
    messaggio = registrazioni[0].getMessage()
    assert f"stato={esito.stato}" in messaggio
    assert f"motivo={motivo}" in messaggio
    assert "latenza_ms=" in messaggio
    assert "classificazione_v1" in messaggio
    for riservato in ("TITOLO_RISERVATO", "utente@example.com", "333 1234567", "DETTAGLIO_RISERVATO", "bozza_risposta"):
        assert riservato not in caplog.text
