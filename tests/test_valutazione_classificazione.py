"""Controlla i conteggi usando proposte e fallback reali del servizio."""

import json
from pathlib import Path

from scripts.valuta_classificazione import valuta_ticket


RADICE = Path(__file__).resolve().parents[1]


def test_valutazione_distingue_proposte_manuali_e_categorie_giuste():
    golden = json.loads((RADICE / "data/golden_dataset.json").read_text(encoding="utf-8"))
    risposte = json.loads((RADICE / "data/risposte_registrate.json").read_text(encoding="utf-8"))["risposte"]
    selezionati = [ticket for ticket in golden if ticket["id"] in ("G01", "G05", "G20")]
    risultato = valuta_ticket(selezionati, risposte)
    assert risultato["totale"] == 3
    assert risultato["proposte"] == 1
    assert risultato["manuali"] == 2
    assert risultato["categorie_giuste"] == 1
    assert risultato["coppie_giuste"] == 1
    assert risultato["motivi_manuale"] == {"output_non_valido": ["G05"], "confidenza_bassa": ["G20"]}
    assert risultato["p1_sottovalutati"] == []
    assert len(risultato["dettagli"]) == 3


def test_replay_quaranta_ticket_riproduce_le_metriche_osservate_non_accettazione_po():
    golden = json.loads((RADICE / "data/golden_dataset.json").read_text(encoding="utf-8"))
    risposte = json.loads((RADICE / "data/risposte_registrate.json").read_text(encoding="utf-8"))["risposte"]
    risultato = valuta_ticket(golden, risposte)
    assert risultato["totale"] == len(golden) == 40
    assert risultato["proposte"] == 31
    assert risultato["manuali"] == 9
    assert risultato["categorie_giuste"] == 28  # Non raggiunge le 32 richieste dal PO.
    assert risultato["coppie_giuste"] == 26
    assert risultato["motivi_manuale"] == {
        "output_non_valido": ["G05", "G12", "G27", "G29", "G33"],
        "confidenza_bassa": ["G09", "G15", "G20", "G39"],
    }
    assert risultato["p1_sottovalutati"] == ["G24"]  # Difetto della risposta registrata, non corretto dal validatore.
    assert {riga["id"] for riga in risultato["dettagli"]} == set(risposte)
