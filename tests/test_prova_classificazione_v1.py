"""Riproduce la validazione delle cinque risposte della prova didattica v1."""

import json
from pathlib import Path

from app.classificazione.schema import valida_risposta


RADICE = Path(__file__).resolve().parents[1]


def test_cinque_risposte_v1_valide_con_almeno_due_casi_difficili():
    prova = json.loads((RADICE / "docs/specs/classificazione/risposte-v1.json").read_text(encoding="utf-8"))
    golden = {ticket["id"]: ticket for ticket in json.loads(
        (RADICE / "data/golden_dataset.json").read_text(encoding="utf-8")
    )}
    risposte = prova["risposte"]
    assert len(risposte) == 5
    assert set(risposte) <= golden.keys()
    assert sum(
        "caso dubbio" in golden[identificativo]["nota"].lower()
        or "prompt injection" in golden[identificativo]["nota"].lower()
        for identificativo in risposte
    ) >= 2
    for identificativo, testo_grezzo in risposte.items():
        assert isinstance(testo_grezzo, str)
        assert valida_risposta(testo_grezzo) is not None, identificativo
