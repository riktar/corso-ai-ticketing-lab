"""Orchestrazione della classificazione, indipendente dal provider."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Literal

from app.classificazione.provider import (
    ClassificatoreProvider,
    ErroreProvider,
    ProviderNonDisponibile,
    TimeoutProvider,
)
from app.classificazione.schema import PropostaClassificazione, valida_risposta


SOGLIA_CONFIDENZA = 0.7
PERCORSO_PROMPT = Path(__file__).resolve().parents[2] / "prompts/classificazione_v1.md"
SEGNAPOSTO_DATI = "\n{{ticket_json}}\n"
REGISTRO = logging.getLogger(__name__)


@dataclass(frozen=True)
class EsitoClassificazione:
    """Esito del componente, non una modifica dello stato persistente del ticket."""

    stato: Literal["proposta", "manuale"]
    proposta: PropostaClassificazione | None = None
    motivo: str | None = None


def classifica_ticket(
    titolo: str, descrizione: str, provider: ClassificatoreProvider
) -> EsitoClassificazione:
    """Restituisce una proposta o un esito manuale, senza retry o invii di risposte.

    Il chiamante deve mascherare i dati personali contenuti in titolo/descrizione
    prima dell'uso con servizi esterni. Non riceve l'email del richiedente.
    L'adapter deve tradurre gli errori del servizio esterno in ErroreProvider.
    """
    inizio = perf_counter()
    esito = _ottieni_esito(titolo, descrizione, provider)
    REGISTRO.info(
        "classificazione stato=%s motivo=%s latenza_ms=%.3f prompt=classificazione_v1",
        esito.stato, esito.motivo, (perf_counter() - inizio) * 1000,
    )
    return esito


def _ottieni_esito(
    titolo: str, descrizione: str, provider: ClassificatoreProvider
) -> EsitoClassificazione:
    try:
        modello = PERCORSO_PROMPT.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return EsitoClassificazione(stato="manuale", motivo="prompt_non_disponibile")
    if modello.count(SEGNAPOSTO_DATI) != 1:
        return EsitoClassificazione(stato="manuale", motivo="prompt_non_disponibile")
    dati = json.dumps({"titolo": titolo, "descrizione": descrizione}, ensure_ascii=False)
    testo_prompt = modello.replace(SEGNAPOSTO_DATI, "\n" + dati + "\n")
    try:
        testo_grezzo = provider.classifica(testo_prompt)
    except TimeoutProvider:
        return EsitoClassificazione(stato="manuale", motivo="timeout")
    except ProviderNonDisponibile:
        return EsitoClassificazione(stato="manuale", motivo="provider_non_disponibile")
    except ErroreProvider:
        return EsitoClassificazione(stato="manuale", motivo="errore_provider")
    proposta = valida_risposta(testo_grezzo)
    if proposta is None:
        return EsitoClassificazione(stato="manuale", motivo="output_non_valido")
    if proposta.confidenza < SOGLIA_CONFIDENZA:
        return EsitoClassificazione(stato="manuale", motivo="confidenza_bassa")
    return EsitoClassificazione(stato="proposta", proposta=proposta)
