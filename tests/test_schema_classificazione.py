"""Esempi del lab 3.1 e controlli sul contratto della risposta grezza."""

import json

import pytest
from pydantic import ValidationError

from app.classificazione.schema import PropostaClassificazione, valida_risposta
from app.models import Categoria, Priorita


PROPOSTA_BASE = {
    "categoria": "accessi",
    "priorita": "P2",
    "sintesi": "La VPN rifiuta le credenziali di un utente senza alternative.",
    "bozza_risposta": "Verifichiamo lo stato delle credenziali della VPN.",
    "confidenza": 0.9,
    "motivazione": "Errore di autenticazione che blocca una persona senza alternativa.",
}

# Gli otto esempi richiesti: cinque validi e tre non validi.
ESEMPI = [
    pytest.param(PROPOSTA_BASE, True, id="valido-accessi"),
    pytest.param({
        "categoria": "hardware", "priorita": "P4",
        "sintesi": "Richiesta di un secondo monitor.",
        "bozza_risposta": "Verifichiamo la disponibilità di un monitor aggiuntivo.",
        "confidenza": 1.0, "motivazione": "Richiesta di una periferica, senza blocchi.",
    }, True, id="valido-hardware"),
    pytest.param({
        "categoria": "software", "priorita": "P3",
        "sintesi": "Stampa non disponibile da un PC, ma possibile da un altro.",
        "bozza_risposta": "Verifichiamo il driver di stampa sul PC interessato.",
        "confidenza": 0.8, "motivazione": "Problema del driver con alternativa disponibile.",
    }, True, id="valido-software"),
    pytest.param({
        "categoria": "rete", "priorita": "P1",
        "sintesi": "La rete è completamente indisponibile per tutta la sede.",
        "bozza_risposta": "Verifichiamo il guasto di rete che coinvolge la sede.",
        "confidenza": 0.95, "motivazione": "Blocco totale della connettività per più persone.",
    }, True, id="valido-rete"),
    pytest.param({
        "categoria": "amministrazione", "priorita": "P4",
        "sintesi": "Richiesta di informazioni sui buoni pasto.",
        "bozza_risposta": "Verifichiamo con l'amministrazione le informazioni richieste.",
        "confidenza": 0.7, "motivazione": "Richiesta amministrativa di informazioni.",
    }, True, id="valido-amministrazione"),
    pytest.param({**PROPOSTA_BASE, "categoria": "sicurezza"}, False,
                 id="non-valido-categoria-inesistente"),
    pytest.param({**PROPOSTA_BASE, "confidenza": 1.4}, False,
                 id="non-valido-confidenza-oltre-uno"),
    pytest.param({chiave: valore for chiave, valore in PROPOSTA_BASE.items()
                  if chiave != "motivazione"}, False,
                 id="non-valido-campo-mancante"),
]


@pytest.mark.parametrize("dati, valido", ESEMPI)
def test_validatore_distingue_gli_otto_esempi(dati, valido):
    proposta = valida_risposta(json.dumps(dati, ensure_ascii=False))

    if valido:
        assert isinstance(proposta, PropostaClassificazione)
        assert proposta.model_dump(mode="json") == dati
    else:
        assert proposta is None


@pytest.mark.parametrize("categoria", list(Categoria))
def test_accetta_tutte_e_sole_le_categorie_del_ticketing(categoria):
    proposta = valida_risposta(json.dumps({**PROPOSTA_BASE, "categoria": categoria.value}))
    assert proposta is not None
    assert proposta.categoria is categoria


@pytest.mark.parametrize("priorita", list(Priorita))
def test_accetta_le_quattro_priorita(priorita):
    proposta = valida_risposta(json.dumps({**PROPOSTA_BASE, "priorita": priorita.value}))
    assert proposta is not None
    assert proposta.priorita is priorita


@pytest.mark.parametrize("confidenza", [0, 0.69, 0.7, 1])
def test_confidenza_valida_include_estremi_e_valori_sotto_soglia(confidenza):
    # Il fallback sotto 0,7 non appartiene alla validazione strutturale.
    proposta = valida_risposta(json.dumps({**PROPOSTA_BASE, "confidenza": confidenza}))
    assert proposta is not None
    assert proposta.confidenza == confidenza


@pytest.mark.parametrize("campo, valore", [
    ("priorita", "P5"),
    ("sintesi", "a" * 301),
    ("sintesi", 123),
    ("bozza_risposta", None),
    ("bozza_risposta", 123),
    ("motivazione", ["non è testo"]),
    ("confidenza", -0.1),
    ("confidenza", "0.9"),
    ("confidenza", True),
    ("confidenza", float("nan")),
    ("confidenza", float("inf")),
    ("campo_inatteso", "non previsto dal contratto"),
])
def test_rifiuta_valori_fuori_contratto(campo, valore):
    assert valida_risposta(json.dumps({**PROPOSTA_BASE, campo: valore})) is None


@pytest.mark.parametrize("campo", list(PROPOSTA_BASE))
def test_tutti_i_campi_sono_obbligatori(campo):
    dati = {chiave: valore for chiave, valore in PROPOSTA_BASE.items() if chiave != campo}
    assert valida_risposta(json.dumps(dati)) is None


def test_sintesi_accetta_esattamente_trecento_caratteri():
    proposta = valida_risposta(json.dumps({**PROPOSTA_BASE, "sintesi": "è" * 300}))
    assert proposta is not None
    assert len(proposta.sintesi) == 300


@pytest.mark.parametrize("testo_grezzo", [
    "", "non è JSON", '{"categoria":', "null", "[]", '"testo"',
    "Ecco la proposta: " + json.dumps(PROPOSTA_BASE),
    "```json\n" + json.dumps(PROPOSTA_BASE) + "\n```",
    json.dumps(PROPOSTA_BASE) + " testo finale",
    json.dumps(PROPOSTA_BASE) + json.dumps(PROPOSTA_BASE),
])
def test_rifiuta_testo_che_non_e_un_singolo_oggetto_json(testo_grezzo):
    assert valida_risposta(testo_grezzo) is None


def test_accetta_spazi_attorno_al_json():
    assert valida_risposta(" \n" + json.dumps(PROPOSTA_BASE) + "\n ") is not None


def test_schema_pydantic_applica_i_vincoli_anche_direttamente():
    with pytest.raises(ValidationError):
        PropostaClassificazione(**{**PROPOSTA_BASE, "sintesi": "a" * 301})
