"""Contratto del provider simulato: prima i test, poi l'implementazione."""

import pytest

from app.classificazione.provider import TimeoutProvider
from app.classificazione.provider_simulato import ProviderSimulato


def test_provider_simulato_restituisce_output_configurato():
    provider = ProviderSimulato(output="risposta grezza")
    assert provider.classifica("prompt di prova") == "risposta grezza"


def test_provider_simulato_solleva_errore_configurato():
    errore = TimeoutProvider("timeout simulato")
    provider = ProviderSimulato(errore=errore)
    with pytest.raises(TimeoutProvider) as sollevato:
        provider.classifica("prompt di prova")
    assert sollevato.value is errore


@pytest.mark.parametrize("errore", [None, TimeoutProvider("timeout")])
def test_provider_simulato_ricorda_ultimo_prompt_anche_in_errore(errore):
    provider = ProviderSimulato(errore=errore)
    assert provider.ultimo_prompt is None
    for prompt in ("primo prompt", "secondo prompt"):
        if errore is None:
            provider.classifica(prompt)
        else:
            with pytest.raises(TimeoutProvider):
                provider.classifica(prompt)
        assert provider.ultimo_prompt == prompt
