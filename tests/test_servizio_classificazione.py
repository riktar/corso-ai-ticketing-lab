"""Servizio di classificazione: risposte reali registrate, nessuna rete."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.classificazione.provider import ProviderNonDisponibile, TimeoutProvider
from app.classificazione.provider_simulato import ProviderSimulato
from app.classificazione.servizio import classifica_ticket
from app.models import Categoria, Priorita


RADICE = Path(__file__).resolve().parents[1]


@pytest.fixture
def risposte():
    return json.loads((RADICE / "data/risposte_registrate.json").read_text(encoding="utf-8"))["risposte"]


def test_risposta_valida_produce_una_proposta(risposte):
    provider = Mock(wraps=ProviderSimulato(output=risposte["G01"]))
    esito = classifica_ticket("Password scaduta", "Sono bloccato", provider)
    assert esito.stato == "proposta"
    assert esito.motivo is None
    assert esito.proposta.categoria is Categoria.ACCESSI
    assert esito.proposta.priorita is Priorita.P2
    provider.classifica.assert_called_once()


def test_timeout_del_provider_porta_a_stato_manuale():
    provider = Mock(wraps=ProviderSimulato(errore=TimeoutProvider("dettagli riservati")))
    esito = classifica_ticket("Titolo", "Descrizione", provider)
    assert esito.stato == "manuale"
    assert esito.proposta is None
    assert esito.motivo == "timeout"
    provider.classifica.assert_called_once()


def test_provider_non_disponibile_porta_a_stato_manuale():
    provider = Mock(wraps=ProviderSimulato(errore=ProviderNonDisponibile("quota esaurita")))
    esito = classifica_ticket("Titolo", "Descrizione", provider)
    assert esito.stato == "manuale"
    assert esito.proposta is None
    assert esito.motivo == "provider_non_disponibile"
    provider.classifica.assert_called_once()


def test_output_non_valido_porta_a_stato_manuale(risposte):
    provider = Mock(wraps=ProviderSimulato(output=risposte["G05"]))
    esito = classifica_ticket("Secondo monitor", "Richiesta", provider)
    assert esito.stato == "manuale"
    assert esito.proposta is None
    assert esito.motivo == "output_non_valido"
    provider.classifica.assert_called_once()


def test_confidenza_bassa_porta_a_stato_manuale(risposte):
    provider = Mock(wraps=ProviderSimulato(output=risposte["G20"]))
    esito = classifica_ticket("Problema con il computer", "Non funziona niente", provider)
    assert esito.stato == "manuale"
    assert esito.proposta is None
    assert esito.motivo == "confidenza_bassa"
    provider.classifica.assert_called_once()
