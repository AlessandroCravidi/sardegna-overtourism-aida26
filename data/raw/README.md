# data/raw/ - Guida alla cartella

## Struttura

- **originali/** — file scaricati tali e quali dalle fonti ufficiali (ISTAT, Regione Sardegna). 
  MAI modificati a mano. Servono come riferimento se occorre rifare una pulizia da zero.

- **file nella root di data/raw/** (es. porti_aeroporti.csv, arrivi_presenze_sired.csv) — 
  versioni pulite/concatenate/filtrate su Sardegna, prodotte dal notebook 
  notebooks/01_pipeline_ingestion.ipynb. Sono questi i file che il codice usa 
  per caricare le tabelle raw.* in DuckDB.

## Corrispondenza originale -> pulito

| File originale (in originali/) | File pulito |
|---|---|
| bollettino_arrivi_partenze(1).csv | porti_aeroporti.csv |
| csv_opendata_comuni_2022/23/24/25.csv | arrivi_presenze_sired.csv |
| capacita_strutture_ricettive_annuale_2022/23/24/25.csv | capacita_ricettiva.csv |
| Abitazioni occupate e non occupate - comuni.csv | abitazioni_non_occupate.csv |
| Residenti 2022/23/24/25_Sardegna_totali_comune.csv | popolazione_residente.csv |
| Superficie_2025_Sardegna_totali_comune.csv | superficie_comunale.csv |
