import pytest


def test_aggiorna_ticket_persiste_modifiche(client, ticket_base):
    creazione = client.post("/tickets", json=ticket_base)
    assert creazione.status_code == 201
    originale = creazione.json()
    ticket_id = originale["id"]
    modifiche = {
        "titolo": "VPN ripristinata in ufficio",
        "descrizione": "Il problema riguarda anche la connessione in ufficio.",
        "categoria": "rete",
        "priorita": "P2",
    }

    risposta = client.patch(f"/tickets/{ticket_id}", json=modifiche)

    assert risposta.status_code == 200
    aggiornato = risposta.json()
    for campo, valore in modifiche.items():
        assert aggiornato[campo] == valore
    for campo in ("id", "email_richiedente", "stato", "creato_il"):
        assert aggiornato[campo] == originale[campo]
    assert aggiornato["aggiornato_il"] >= originale["aggiornato_il"]
    rilettura = client.get(f"/tickets/{ticket_id}")
    assert rilettura.status_code == 200
    assert rilettura.json() == aggiornato


def test_aggiorna_ticket_inesistente_restituisce_404(client):
    risposta = client.patch("/tickets/999", json={"titolo": "Titolo aggiornato"})
    assert risposta.status_code == 404


@pytest.mark.parametrize("metodo", ["post", "patch"])
@pytest.mark.parametrize(
    "campo,valore,dettaglio",
    [
        ("titolo", "    a    ", "Il titolo deve avere tra 5 e 120 caratteri"),
        ("titolo", "a" * 121, "Il titolo deve avere tra 5 e 120 caratteri"),
        ("descrizione", "   ", "La descrizione non puo' essere vuota"),
        ("descrizione", "a" * 5001, "La descrizione supera i 5000 caratteri"),
    ],
    ids=["titolo-corto-dopo-strip", "titolo-lungo", "descrizione-vuota", "descrizione-lunga"],
)
def test_validazione_testi_restituisce_422(client, ticket_base, metodo, campo, valore, dettaglio):
    if metodo == "patch":
        originale = client.post("/tickets", json=ticket_base).json()
        url = f"/tickets/{originale['id']}"
        payload = {campo: valore}
    else:
        url = "/tickets"
        payload = {**ticket_base, campo: valore}

    risposta = getattr(client, metodo)(url, json=payload)

    assert risposta.status_code == 422
    assert risposta.json()["detail"] == dettaglio
    if metodo == "patch":
        assert client.get(url).json() == originale
    else:
        assert client.get("/tickets").json() == []


@pytest.mark.parametrize("metodo", ["post", "patch"])
@pytest.mark.parametrize("lunghezza_titolo", [5, 120])
def test_validazione_accetta_limiti_inclusivi(client, ticket_base, metodo, lunghezza_titolo):
    testi = {"titolo": "a" * lunghezza_titolo, "descrizione": "b" * 5000}
    if metodo == "patch":
        ticket_id = client.post("/tickets", json=ticket_base).json()["id"]
        url = f"/tickets/{ticket_id}"
        payload = testi
    else:
        url = "/tickets"
        payload = {**ticket_base, **testi}

    risposta = getattr(client, metodo)(url, json=payload)

    assert risposta.status_code == (201 if metodo == "post" else 200)
    for campo, valore in testi.items():
        assert risposta.json()[campo] == valore


@pytest.mark.parametrize("payload", [{}, {"titolo": None, "descrizione": None}])
def test_patch_testi_omessi_o_null_non_modifica_ticket(client, ticket_base, payload):
    originale = client.post("/tickets", json=ticket_base).json()
    url = f"/tickets/{originale['id']}"

    risposta = client.patch(url, json=payload)

    assert risposta.status_code == 200
    assert risposta.json() == originale
    assert client.get(url).json() == originale
