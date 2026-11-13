"""Confini del servizio e guasti accessori, senza chiamate di rete."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.classificazione import servizio
from app.classificazione.provider import ErroreProvider
from app.classificazione.provider_simulato import ProviderSimulato


RADICE = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("confidenza, stato", [(0, "manuale"), (0.6999, "manuale"), (0.7, "proposta"), (1, "proposta")])
def test_soglia_confidenza_inclusiva(confidenza, stato):
    risposte = json.loads((RADICE / "data/risposte_registrate.json").read_text(encoding="utf-8"))["risposte"]
    dati = json.loads(risposte["G01"])
    dati["confidenza"] = confidenza
    esito = servizio.classifica_ticket("Titolo", "Descrizione", ProviderSimulato(output=json.dumps(dati)))
    assert esito.stato == stato
    assert (esito.proposta is None) == (stato == "manuale")


def test_errore_provider_generico_non_arriva_al_chiamante():
    provider = Mock(wraps=ProviderSimulato(errore=ErroreProvider("dettagli da non esporre")))
    esito = servizio.classifica_ticket("Titolo", "Descrizione", provider)
    assert esito.stato == "manuale"
    assert esito.motivo == "errore_provider"
    assert esito.proposta is None
    provider.classifica.assert_called_once()


@pytest.mark.parametrize("contenuto", [None, "modello senza segnaposto", "\n{{ticket_json}}\n\n{{ticket_json}}\n"])
def test_prompt_assente_o_incoerente_porta_a_manuale_senza_chiamare_provider(tmp_path, monkeypatch, contenuto):
    percorso = tmp_path / "prompt.md"
    if contenuto is not None:
        percorso.write_text(contenuto, encoding="utf-8")
    monkeypatch.setattr(servizio, "PERCORSO_PROMPT", percorso)
    provider = Mock()
    esito = servizio.classifica_ticket("Titolo", "Descrizione", provider)
    assert esito.stato == "manuale"
    assert esito.proposta is None
    assert esito.motivo == "prompt_non_disponibile"
    provider.classifica.assert_not_called()
