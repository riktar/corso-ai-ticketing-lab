"""Controlli sul prompt effettivamente ricevuto dal provider locale."""

import json
from pathlib import Path

from app.classificazione.provider_simulato import ProviderSimulato
from app.classificazione.servizio import classifica_ticket


RADICE = Path(__file__).resolve().parents[1]


def test_prompt_contiene_titolo_e_descrizione_ma_non_email_richiedente():
    ticket = json.loads((RADICE / "data/golden_dataset.json").read_text(encoding="utf-8"))[0]
    provider = ProviderSimulato(output="non valido")
    classifica_ticket(ticket["titolo"], ticket["descrizione"], provider)
    prompt = provider.ultimo_prompt
    assert ticket["titolo"] in prompt
    assert ticket["email_richiedente"] not in prompt
    dati = prompt.rsplit("<INIZIO_DATI_TICKET>\n", 1)[1].split("\n<FINE_DATI_TICKET>", 1)[0]
    assert json.loads(dati) == {"titolo": ticket["titolo"], "descrizione": ticket["descrizione"]}
    modello = (RADICE / "prompts/classificazione_v1.md").read_text(encoding="utf-8")
    assert prompt == modello.replace("\n{{ticket_json}}\n", "\n" + dati + "\n")
