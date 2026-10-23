# Diario di lab

Nome: Riccardo Tartaglia
Coppia con: Pierluigi Ricci

## Lab 1.1: esplorazione del repository

Attività tecniche svolte tramite l'assistente di questa sessione Knotic, non avviando un processo Claude Code separato. I passi 2-5 sono stati richiesti insieme; nella tabella i passi 3 e 4 sono riassunti, non presentati come ulteriori prompt digitati. Tempi indicativi ignorati come richiesto. Lo scambio dei ruoli e una review umana non sono attestati dalla sessione.

| # | Prompt usato | Cosa ha risposto l'assistente | Corretto? Cosa ho verificato |
| --- | --- | --- | --- |
| 1 | Spiegami com'è organizzato questo repository: moduli, percorso di una richiesta "apri ticket" dall'endpoint al database, dove sono le regole sugli stati. | API FastAPI con SQLite; endpoint e SQL in `main.py`, modelli in `models.py`, connessioni in `db.py`, transizioni in `config.py`. Ha segnalato discrepanze fra codice e processo. | Confermato leggendo i file: `crea_ticket()` inserisce lo stato `aperto`, rilegge il record e restituisce 201; `get_conn()` effettua il commit alla normale uscita dal contesto. Mancava il problema del payload completo nei log. |
| 2 | Passo 3 della richiesta: trovare un endpoint senza test, aggiungere un test, eseguire pytest, introdurre un errore e annullarlo. | Scelto `PATCH /tickets/{ticket_id}` e aggiunto `test_aggiorna_ticket_persiste_modifiche`, con ulteriori casi di errore e regressione. | Il test verifica 200, campi aggiornati, campi invariati e persistenza tramite una successiva GET. Cambiando temporaneamente la risposta in 202, è fallito su `assert 202 == 200`; dopo il ripristino la suite è tornata verde. |
| 3 | Passo 4 della richiesta: estrarre in un punto solo la validazione duplicata di titolo e descrizione, leggere il diff e rieseguire i test. | Aggiunta `_valida_testi_ticket()` in `app/main.py`, richiamata da creazione e aggiornamento. | Diff proposto esaminato prima dell'applicazione e diff effettivo controllato dopo. Limiti, messaggi 422, controlli su `None` e comportamento degli endpoint conservati; 22 test passati. |

### Verifica della spiegazione e del processo

Una cosa corretta nella spiegazione del repository:

- Non esistono livelli service/repository né un ORM separato: `app/main.py` contiene endpoint, logica applicativa e query SQL. Letti almeno due file citati: `app/main.py` e `app/db.py`; riletti anche `app/models.py`, i test e `docs/processo-supporto.md`.
- Percorso verificato: `POST /tickets` → modello `TicketCreate` → validazioni in `crea_ticket()` → `get_conn()` → INSERT e SELECT → commit e chiusura → modello `Ticket`, risposta 201. Dopo il refactoring, i controlli sui testi passano dalla funzione condivisa.

Una cosa imprecisa o mancante:

- La spiegazione iniziale non evidenziava che `crea_ticket()` passa `payload.model_dump()` a `log.info()`: nel payload sono presenti email e descrizione, quindi il codice registra potenzialmente dati personali. `docs/processo-supporto.md`, sezione "Dati personali", lo vieta. Verifica tramite lettura del codice, non acquisizione di log reali.

Confronto con `docs/processo-supporto.md`: **non torna completamente**.

- `config.TRANSIZIONI` consente `aperto → chiuso`, mentre il processo impone prima una presa in carico (`in_lavorazione`).
- Consente anche `chiuso → aperto`, mentre il documento considera la chiusura definitiva.
- `cambia_stato()` applica il dizionario e restituisce 409 per le transizioni non consentite: la regola effettiva è quella del codice, non quella del documento.
- Il documento prevede la chiusura dopo cinque giorni lavorativi senza risposta; nei moduli applicativi esaminati non è presente l'automatismo corrispondente.
- Queste sono verifiche statiche del codice e della documentazione, non nuovi test dinamici delle transizioni. Le discrepanze sono annotate ma non corrette: il lab richiede un test e un refactoring, non una modifica del processo di business.


Test aggiunto (nome e cosa verifica):

- File nuovo: `tests/test_aggiornamento.py`.
- `test_aggiorna_ticket_persiste_modifiche`: crea un ticket, aggiorna titolo, descrizione, categoria e priorità con PATCH, controlla HTTP 200 e i valori restituiti; verifica che ID, email, stato e data di creazione restino invariati, che il timestamp di aggiornamento non arretri e che la successiva GET restituisca il record aggiornato.
- Ulteriori test: PATCH di un ticket inesistente (404); titolo troppo corto dopo `strip()` o troppo lungo; descrizione vuota o troppo lunga, sia in POST sia in PATCH, con verifica del dettaglio 422 e assenza di modifiche persistite; limiti inclusivi di 5/120 caratteri per il titolo e 5000 per la descrizione; PATCH con testi omessi o `null` che lascia il ticket invariato.
- Totale: 16 nuovi casi parametrizzati/eseguibili, oltre ai 6 test originali. I test usano il database temporaneo della fixture, non il database applicativo.

Modifica manuale fatta per far fallire il test:

- Introdotta dall'assistente una modifica esplicita e temporanea al decoratore del PATCH: aggiunto `status_code=202` al posto del comportamento predefinito 200. Non è stata una modifica manuale eseguita dalla coppia.
- Eseguito il solo `tests/test_aggiornamento.py::test_aggiorna_ticket_persiste_modifiche`: risultato **1 failed**, sulla riga `assert risposta.status_code == 200`, con errore `assert 202 == 200`. Il processo pytest ha restituito exit code 1, come atteso.
- Ripristino nel blocco `finally` dello script di prova, verificando che `app/main.py` fosse identico byte per byte alla versione prima della mutazione. Nessun reset Git e nessuna modifica ai test per farli passare.
- Suite rieseguita dopo il ripristino: **22 passed**. La modifica errata non è rimasta nel codice finale.

Refactoring chiesto e perché ho accettato (o rifiutato) il diff:

- Estrarre la validazione duplicata in `_valida_testi_ticket(titolo, descrizione)`, nello stesso modulo, senza introdurre nuovi livelli o cambiare il comportamento.
- La review tecnica dell'assistente ha letto un unified diff generato in memoria **prima** della modifica del file, poi il `git diff -- app/main.py` effettivo dopo l'applicazione. Non si attribuisce alla coppia un'approvazione umana non osservata.
- Diff ritenuto accettabile tecnicamente perché sostituisce i due blocchi duplicati con due chiamate alla stessa funzione; mantiene `None` come campo non aggiornato nel PATCH, le soglie, lo `strip()` nei controlli, i messaggi e il codice 422. Non modifica query, stato, controllo email o normalizzazione dei dati salvati. Eliminata una riga vuota superflua dalla proposta iniziale.
- I test di caratterizzazione erano già verdi prima del refactoring e restano verdi dopo: **22 passed**. Anche `git diff --check` è passato.

## Lab 1.2: CLAUDE.md e server MCP

Server MCP collegato e comando usato:

Le tre domande fatte tramite il server:

1.
2.
3.

Cosa è successo con l'operazione fuori perimetro:

## Cosa porto a casa

Una cosa che farò diversamente da lunedì:

Usare l'assistente per orientarmi, ma verificare almeno due sorgenti e il processo documentato; prima di accettare un refactoring leggere il diff, eseguire i test e controllare che almeno un test rilevi davvero una regressione intenzionale.
