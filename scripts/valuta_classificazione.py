"""Replay locale: python -m scripts.valuta_classificazione.

Non genera risposte e non contatta un modello: misura il servizio sulle risposte
registrate. Stampa solo identificativi e metriche, mai testo o dati personali.
"""

import json
from collections import defaultdict
from pathlib import Path

from app.classificazione.provider_simulato import ProviderSimulato
from app.classificazione.servizio import classifica_ticket


RADICE = Path(__file__).resolve().parents[1]


def valuta_ticket(ticket: list[dict], risposte: dict[str, str]) -> dict:
    """I manuali contano come non corretti, secondo la regola del PO."""
    dettagli = []
    motivi_manuale = defaultdict(list)
    proposte = categorie_giuste = coppie_giuste = 0
    p1_sottovalutati = []
    for dati in ticket:
        identificativo = dati["id"]
        provider = ProviderSimulato(output=risposte[identificativo])
        esito = classifica_ticket(dati["titolo"], dati["descrizione"], provider)
        proposta = esito.proposta
        categoria = proposta.categoria.value if proposta is not None else None
        priorita = proposta.priorita.value if proposta is not None else None
        categoria_giusta = categoria == dati["categoria_attesa"]
        coppia_giusta = categoria_giusta and priorita == dati["priorita_attesa"]
        if esito.stato == "proposta":
            proposte += 1
            categorie_giuste += categoria_giusta
            coppie_giuste += coppia_giusta
            if dati["priorita_attesa"] == "P1" and priorita in ("P3", "P4"):
                p1_sottovalutati.append(identificativo)
        else:
            motivi_manuale[esito.motivo].append(identificativo)
        dettagli.append({
            "id": identificativo,
            "stato": esito.stato,
            "motivo": esito.motivo,
            "categoria": categoria,
            "priorita": priorita,
            "categoria_attesa": dati["categoria_attesa"],
            "priorita_attesa": dati["priorita_attesa"],
            "categoria_giusta": categoria_giusta,
            "coppia_giusta": coppia_giusta,
        })
    return {
        "totale": len(ticket),
        "proposte": proposte,
        "manuali": len(ticket) - proposte,
        "categorie_giuste": categorie_giuste,
        "coppie_giuste": coppie_giuste,
        "motivi_manuale": dict(motivi_manuale),
        "p1_sottovalutati": p1_sottovalutati,
        "dettagli": dettagli,
    }


def main() -> None:
    ticket = json.loads((RADICE / "data/golden_dataset.json").read_text(encoding="utf-8"))
    risposte = json.loads((RADICE / "data/risposte_registrate.json").read_text(encoding="utf-8"))["risposte"]
    if len(ticket) != 40 or len({dati["id"] for dati in ticket}) != 40 or {dati["id"] for dati in ticket} != set(risposte):
        raise ValueError("Attesi 40 ticket univoci con le rispettive risposte registrate")
    print(json.dumps(valuta_ticket(ticket, risposte), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
