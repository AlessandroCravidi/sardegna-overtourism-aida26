# Sardegna Overtourism — AIDA26

Project work del Master **Artificial Intelligence & Data Analytics for Business**, modulo *ETL & Data Visualization*.

L'overtourism — la pressione turistica che eccede la capacità di un territorio — non colpisce la Sardegna in modo uniforme: poche mete costiere concentrano flussi altissimi mentre decine di comuni restano fuori da ogni statistica. Questo progetto costruisce, comune per comune e mese per mese (2022–2025), un indice di pressione turistica e un indice di attrattività indipendente dai flussi, per distinguere dove il turismo è già eccessivo da dove esiste ancora margine di crescita sostenibile.

## Obiettivo e domande di ricerca

- Quantificare la pressione turistica per comune e seguirne l'evoluzione nel tempo (**Indice di Overtourism**)
- Valutare il potenziale attrattivo di un territorio a prescindere dai flussi attuali (**Indice di Attrattività**)
- Stimare il **sommerso turistico**: quanta parte dei flussi reali sfugge alle statistiche ufficiali
- Individuare le **gemme nascoste**: comuni ad alta attrattività e bassa pressione turistica
- Fornire uno strumento operativo e aggiornabile, non un'analisi one-off

## Stakeholder e utilità

Enti del turismo regionale/locale, comuni costieri, operatori ricettivi, residenti e decisori politici — a cui l'analisi offre una base dati per regolamentare dove serve, promuovere in modo destagionalizzato e indirizzare gli investimenti; ai turisti, uno strumento per scoprire mete valide ma meno affollate.

## Sorgenti dati

| Fonte | Dato | Aggiornamento |
|---|---|---|
| ISTAT | anagrafica comuni, popolazione residente, superficie, abitazioni non occupate | annuale |
| Regione Sardegna — Osservatorio del Turismo (SIRED) | arrivi/presenze ufficiali, capacità ricettiva | mensile / annuale |
| sardegnamobilità | flussi giornalieri porti e aeroporti | giornaliero |
| OpenStreetMap (Overpass API) | punti di interesse (POI), 5 pilastri: turismo, natura, ristorazione, servizi, infrastrutture | statico |

## Pipeline ETL

**Data Collection → Data Cleaning & Optimization → Data Distribution → Data Presentation**

Lo strato ETL è implementato in DuckDB (`db/sardegna_overtourism.duckdb`) su tre schemi: `raw` (tabelle sorgente, una per fonte, caricate as-is), `staging` (join, normalizzazione chiavi comune, gestione missing) e `presentation` (data warehouse di consumo: un indicatore per tabella, più `indicatori_comune_anno` come tabella wide per Tableau). I CSV/geojson in `data/` e `File x Tableau/` sono l'export di distribuzione di questo stesso strato.

| # | Notebook | Cosa fa |
|---|---|---|
| 01 | `pipeline_ingestion` | Ingestion e pulizia delle fonti ISTAT/SIRED/porti-aeroporti; costruzione schema `raw`→`staging`→`presentation`; calcolo Herfindahl-Hirschman, sommerso turistico, stagionalità mercati; export per Tableau |
| 02 | `dati_osm` | Raccolta POI da OpenStreetMap (Overpass API), allocazione ai comuni via GeoPandas |
| 03 | `indice_da_osm` | Calcolo dell'Indice di Attrattività dai POI |
| 04 | `indicatore_densita` | Densità Turistica (comune × mese × anno) |
| 05 | `densita_ricettiva` | Densità Ricettiva (comune × anno) |
| 06 | `intensita_turistica` | Intensità Turistica (comune × mese × anno) |
| 07 | `indicatore_utilizzazione_lorda` | Utilizzazione Lorda (comune × anno) |
| 08 | `indice_overtourism` | Composizione dell'Indice di Overtourism |
| 09 | `calcolo_gem_score` | Combinazione Attrattività × Overtourism, quadranti, gem score |
| 10 | `genera_mappa_gemme` | Mappa Leaflet interattiva, autocontenuta (`data/mappa_gemme_nascoste/`) |

## Indicatori calcolati

| Indicatore | Definizione |
|---|---|
| Densità Turistica | Presenze / superficie comunale (km²) |
| Densità Ricettiva | Letti totali / superficie comunale (km²) |
| Intensità Turistica | Presenze / popolazione residente |
| Utilizzazione Lorda | Presenze / (letti disponibili × 365) — valore annuo, % |
| Indice di Overtourism | Media geometrica dei 4 indicatori sopra, dopo winsorizzazione p99 e min-max; missing gestiti come dato mancante, mai come zero |
| Indice di Attrattività | Punteggio 0–100 sui 5 pilastri OSM (turismo 30%, natura 25%, ristorazione 20%, servizi 15%, infrastrutture 10%), densità per km² su area regolarizzata (buffer = mediana delle superfici, per non premiare i comuni microscopici), poi trasformazione logaritmica e min-max |
| Gem Score | `attrattività × (1 − overtourism)`, normalizzato 0–100; quadranti sulle mediane (Gemma Nascosta / Destinazione Popolare / Territorio Autentico / Zona Satura); un comune entra in "Gemma Nascosta" solo se ha una base minima di dati turistici reali (≥3 sotto-indicatori disponibili e densità ricettiva > 0), per non confondere l'assenza di offerta turistica con l'autenticità |

## Struttura della repository

```
data/                          dataset grezzi, intermedi e output (CSV, GeoJSON, HTML)
  raw/                         fonti pulite + originali/ (download non modificati)
  presentation/                export della data warehouse (schema presentation)
  indicatore_*/                output per singolo indicatore
  mappa_gemme_nascoste/        mappa Leaflet interattiva finale
notebooks/                     pipeline ETL e calcolo indicatori, 01→10 in ordine
db/                             sardegna_overtourism.duckdb (non tracciato, rigenerabile)
File x Tableau/                export dedicati alla dashboard Tableau (HHI, provenienze, stagionalità)
presentazione/                 slide e grafici della presentazione
```

## Tecnologie

Python (pandas, numpy, geopandas, shapely, duckdb, folium, matplotlib, requests), Jupyter Notebook, DuckDB come data warehouse locale, OpenStreetMap/Overpass API, Tableau per la dashboard di visualizzazione.

## Autori

Davide Colucci, Alessandro Cravidi, Giuseppe Gatto, Matteo Rovedo — Master AIDA26, Gruppo 3.

## Come eseguire

Richiede Python ≥3.10. Installare le dipendenze (`pip install pandas numpy geopandas shapely duckdb folium matplotlib requests jupyter`) ed eseguire i notebook in `notebooks/` in ordine 01→10; ciascuno legge gli output del precedente da `data/` e da `db/sardegna_overtourism.duckdb`.
