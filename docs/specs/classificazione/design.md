# Classificazione — contratto e servizio (lab 3.1 e 4.1)

## Confine di validazione

`provider.py` riceve il prompt già composto e restituisce il testo grezzo.
`schema.py` valida quel testo fuori dal provider, riutilizzando `Categoria` e
`Priorita` di `app/models.py`, coerenti con `docs/categorie.md` e
`docs/processo-supporto.md`. Il lab 4.1 usa solo un provider simulato, senza rete.

`valida_risposta(testo_grezzo)` restituisce una `PropostaClassificazione` oppure
`None` in caso di JSON o schema non validi. Tutti i sei campi sono obbligatori;
non sono ammessi campi aggiuntivi. La sintesi ha al massimo 300 caratteri e la
confidenza è un numero finito tra 0 e 1, senza conversione da stringhe o booleani.
La motivazione deve essere breve nel prompt; non viene inventata una soglia di
lunghezza non specificata dal lab.

## Decisione sul parsing

Si accetta solo un singolo oggetto JSON completo, con eventuali spazi esterni.
Si rifiutano prosa prima o dopo il JSON, blocchi Markdown, JSON malformato,
array e valori non oggetto. Non si estrae, ripara o completa il JSON: una
risposta non conforme restituisce `None`, senza registrare il testo nei log.

La validità strutturale non garantisce la correttezza della classificazione.
La confidenza sotto 0,7 resta valida per lo schema: la regola della coda manuale
è applicata successivamente dal servizio, non dal validatore. Anche il divieto
di link e l'approvazione della bozza restano requisiti del flusso completo;
il prompt v1 li esplicita, ma lo schema non è un filtro semantico.

## Prompt ed esempi

Il prompt versionato è `prompts/classificazione_v1.md`. Contiene definizioni,
formato JSON e delimitatori per il ticket, trattato come dato non fidato.
Il servizio legge il file con percorso relativo al modulo (non alla directory
corrente) e sostituisce solo la riga `{{ticket_json}}`, lasciando intatta la
citazione del segnaposto nel testo delle istruzioni. Inserisce un oggetto JSON
con solo `titolo` e `descrizione`, serializzato con escaping JSON.
Il campo `email_richiedente` non è un parametro del servizio e non viene incluso.

**Precondizione per servizi esterni:** titolo e descrizione devono essere già
mascherati dal chiamante. Il nucleo del lab 4.1 non implementa il mascheramento
di email/telefoni/dati sanitari dentro il testo. Il replay è esclusivamente
locale e non autorizza un invio di dati a servizi esterni. I delimitatori e le
istruzioni nel prompt non sono una garanzia di protezione dalla prompt injection.

`tests/test_schema_classificazione.py` contiene gli otto esempi richiesti
(cinque validi e tre invalidi: categoria inesistente, confidenza 1,4, campo
mancante), oltre ai test sui limiti, sui tipi e sul parsing rigoroso.

## Prova su cinque ticket (lab 3.1, punto 4)

La prova è documentata in `errori-v1.md`, con cinque righe di confronto tra
atteso e ottenuto e le ipotesi sulle osservazioni. Le risposte grezze simulate
sono in `risposte-v1.json`; `tests/test_prova_classificazione_v1.py` ne verifica
la validità strutturale e la selezione di almeno due casi difficili.

Si tratta di una simulazione didattica dell'assistente con etichette attese già
visibili, non di un benchmark cieco o di una chiamata a un provider esterno.
Il replay successivo del lab 4.1 usa invece le quaranta risposte registrate.

## Servizio e fallback implementati (lab 4.1)

Non erano presenti `issues.md` o un design completo del lab 3.2: l'implementazione
segue il contratto di `provider.py`, i passi del lab 4.1 e le decisioni del PO.

Interfaccia: `classifica_ticket(titolo, descrizione, provider)` in
`app/classificazione/servizio.py`. Restituisce un `EsitoClassificazione`:

- `stato="proposta"`, proposta validata e `motivo=None`;
- `stato="manuale"`, `proposta=None` e un motivo stabile senza dettagli riservati.

Il servizio non modifica gli stati di `app.models.Stato`, non salva nel DB,
non invia risposte e non implementa una coda persistente: il chiamante dovrà
usare l'esito per l'instradamento. Non sono cambiati gli endpoint esistenti.

Sequenza implementata:

1. Lettura del prompt da file e controllo di una sola riga segnaposto.
2. Composizione JSON di titolo e descrizione; una sola chiamata al provider.
3. In caso di errore contrattuale del provider, esito manuale immediato.
4. Validazione del testo grezzo fuori dal provider.
5. Esito manuale se l'output non è valido o la confidenza è sotto 0,7;
   proposta solo se valida e con confidenza **maggiore o uguale a 0,7**.
6. Log dell'esito e della latenza, senza contenuti del ticket o della risposta.

| Condizione | Motivo manuale | Test |
| --- | --- | --- |
| `TimeoutProvider` | `timeout` | `test_timeout_del_provider_porta_a_stato_manuale` |
| `ProviderNonDisponibile` | `provider_non_disponibile` | `test_provider_non_disponibile_porta_a_stato_manuale` |
| JSON/schema non valido | `output_non_valido` | `test_output_non_valido_porta_a_stato_manuale` |
| Confidenza < 0,7 | `confidenza_bassa` | `test_confidenza_bassa_porta_a_stato_manuale` |
| Altro `ErroreProvider` | `errore_provider` | `test_errore_provider_generico_non_arriva_al_chiamante` |
| File prompt illeggibile o segnaposto assente/duplicato | `prompt_non_disponibile` | `test_prompt_assente_o_incoerente_porta_a_manuale_senza_chiamare_provider` |

Nessun retry. Gli adapter futuri devono tradurre gli errori del servizio esterno
in `ErroreProvider`; il servizio intercetta l'intera gerarchia, non maschera
indiscriminatamente gli errori di programmazione con `except Exception`.
Il contratto restituisce testo: il provider non esegue la validazione.

`ProviderSimulato(output=..., errore=...)` restituisce la stringa configurata,
oppure solleva l'istanza di errore configurata (che ha precedenza sull'output).
Memorizza sempre `ultimo_prompt`, anche quando solleva un errore. È un oggetto
locale per test, non un provider di produzione; non conserva una cronologia.

### Log disponibili

| Campo | Comportamento |
| --- | --- |
| Stato e motivo | Valori controllati del servizio, mai messaggio dell'eccezione |
| Latenza | Millisecondi dell'intero servizio misurati con orologio monotono |
| Prompt | Versione `classificazione_v1` |
| Token e modello | Non disponibili nel contratto corrente; non vengono inventati |
| Testo, dati personali, risposta grezza | Mai registrati dal servizio |

Il logger usa il livello INFO e la configurazione dell'applicazione; i test
abilitano esplicitamente la cattura. Il provider simulato conserva il prompt
in memoria per l'ispezione, ma il servizio non lo copia nei log.

### Evidenza test-prima e verifiche

La baseline iniziale era di 78 test verdi. Il provider simulato è stato costruito
con cicli rosso/verde per output, errore e memoria del prompt. I cinque test
richiesti del servizio sono stati introdotti uno alla volta: import del modulo
assente per il percorso valido; timeout e indisponibilità inizialmente propagati;
G05 e G20 inizialmente erroneamente proposti. Dopo ogni correzione sono stati
rieseguiti i test già presenti. Il test del prompt è fallito sul prompt vuoto
prima di implementare la composizione da file. Anche il log e la gestione dei
guasti del file prompt sono stati aggiunti dopo test rossi osservati.

I test aggiuntivi verificano il confine inclusivo di 0,7, l'assenza di retry e
la soppressione della proposta negli esiti manuali. Il replay completo e i
conteggi sono riproducibili con `python -m scripts.valuta_classificazione`.
Risultati e **criteri di qualità del PO non soddisfatti** sono in `errori-v1.md`;
la suite verde non costituisce accettazione della qualità delle classificazioni.

Questa è documentazione del componente realizzato, non una consegna retroattiva
del lab 3.2 (diagramma completo e issue restano fuori da questa richiesta).
