"""Provider locale e deterministico per esercitazioni e test."""

from app.classificazione.provider import ErroreProvider


class ProviderSimulato:
    def __init__(self, output: str = "", errore: ErroreProvider | None = None):
        self.output = output
        self.errore = errore
        self.ultimo_prompt: str | None = None

    def classifica(self, testo_prompt: str) -> str:
        self.ultimo_prompt = testo_prompt
        if self.errore is not None:
            raise self.errore
        return self.output
