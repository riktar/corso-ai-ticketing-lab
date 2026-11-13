"""Contratto e validazione della risposta grezza del modello, fuori dal provider."""

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.models import Categoria, Priorita


class PropostaClassificazione(BaseModel):
    """Proposta da sottoporre all'operatore, mai una risposta già approvata."""

    model_config = ConfigDict(extra="forbid")

    categoria: Categoria
    priorita: Priorita
    sintesi: str = Field(max_length=300)
    bozza_risposta: str
    confidenza: float = Field(ge=0, le=1, strict=True, allow_inf_nan=False)
    motivazione: str = Field(description="Breve motivazione della categoria e della priorità.")


def valida_risposta(testo_grezzo: str) -> PropostaClassificazione | None:
    """Accetta solo un oggetto JSON completo conforme, altrimenti restituisce None.

    Non estrae JSON da Markdown o prosa e non corregge le risposte del modello.
    La soglia di confidenza per la coda manuale è una regola successiva,
    distinta dalla validità strutturale. Il testo grezzo non viene registrato.
    """
    try:
        return PropostaClassificazione.model_validate_json(testo_grezzo)
    except ValidationError:
        return None
