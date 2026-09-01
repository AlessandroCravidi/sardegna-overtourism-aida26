#!/usr/bin/env python3
"""
Genera index.html ("Sardegna: Gemme Nascoste") a partire da un DataFrame.

Riusa esattamente l'HTML/CSS/JS di index(1).html (front-end con tendine
Mese/Anno, sidebar con classifica, mappa Leaflet) leggendo due frammenti
di template (template_head.html, template_tail.html, nella stessa
cartella di questo script) e iniettando in mezzo un blocco JSON
"embedded-data" costruito dal DataFrame.

NON si occupa di reperire i dati (OSM, ISTAT, ecc.): assume che tutto sia
già disponibile in un DataFrame "lungo" (una riga per comune-anno-mese),
così come descritto in `COLONNE_ATTESE` qui sotto. Sostituisci la funzione
`carica_dati_di_esempio()` con il tuo caricamento reale (es. dal
02_indice_da_osm.ipynb + il calcolo mensile di overtourism).

------------------------------------------------------------------------
COLONNE ATTESE nel DataFrame `df` (long format):

Statiche per comune (ripetute su ogni riga dello stesso comune):
    name              str    nome del comune
    code              int    codice ISTAT (chiave univoca del comune)
    lat, lng          float  coordinate del comune
    coastal           bool   comune costiero
    mountain          bool   comune montano
    population        int    popolazione residente
    area_kmq          float  superficie in km²
    beds              int    posti letto ricettivi

Mensili (una riga per anno/mese):
    year              int
    month             int    1-12
    presenze          float  presenze turistiche nel mese
    presenze_annue    float  presenze turistiche nell'anno (per contesto)
    densita_turistica     float
    intensita_turistica   float
    densita_ricettiva     float
    utilizzazione_lorda   float
    overtourism           float  indice di overtourism (0-1 circa)
    p75_overtourism       float  75° percentile mensile dell'overtourism
    n_indicatori_disponibili int
    eligible              bool   (informativo: il fronte-end lo ricalcola comunque)
    gem_score             float  (informativo, mostrato come "rank dataset")
    gem_score_norm        float  (informativo)
    gem_rank              int/None (informativo, mostrato in UI)
    seasonal_adjustment   float  aggiustamento stagionale (-0.2 .. +0.25 circa)
    norm_densita_turistica, norm_intensita_turistica,
    norm_densita_ricettiva, norm_utilizzazione_lorda   float (0-1)
        -> le 4 componenti normalizzate, usate per le barre nel popup

Il fronte-end ricalcola comunque lo score "gemme nascoste" a runtime
(client-side) usando `overtourism`, `p75_overtourism`, `presenze`,
`seasonal_adjustment` e le caratteristiche statiche del comune (population,
beds, coastal) — le colonne gem_score/gem_score_norm/gem_rank/eligible
servono solo come informazione aggiuntiva mostrata in UI, non sono
ricalcolate. Le colonne norm_* sono invece quelle mostrate come barre
nel popup di ogni comune.
------------------------------------------------------------------------
"""

import json
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_HEAD = SCRIPT_DIR / "template_head.html"
TEMPLATE_TAIL = SCRIPT_DIR / "template_tail.html"

MESI_ITALIANI = [
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
]

COLONNE_STATICHE = [
    "name", "code", "lat", "lng", "coastal", "mountain",
    "population", "area_kmq", "beds",
]

COLONNE_MENSILI = [
    "year", "month", "presenze", "presenze_annue",
    "densita_turistica", "intensita_turistica",
    "densita_ricettiva", "utilizzazione_lorda",
    "overtourism", "p75_overtourism", "n_indicatori_disponibili",
    "eligible", "gem_score", "seasonal_adjustment",
    "gem_score_norm", "gem_rank",
]

COLONNE_NORM = [
    "norm_densita_turistica", "norm_intensita_turistica",
    "norm_densita_ricettiva", "norm_utilizzazione_lorda",
]


def df_to_comuni(df: pd.DataFrame) -> list:
    """Converte il DataFrame lungo in una lista di comuni con `monthly` annidato,
    nello stesso formato di DATA.comuni in index(1).html."""

    mancanti = set(COLONNE_STATICHE + COLONNE_MENSILI + COLONNE_NORM) - set(df.columns)
    if mancanti:
        raise ValueError(f"Colonne mancanti nel DataFrame: {sorted(mancanti)}")

    comuni = []
    for code, gruppo in df.groupby("code", sort=False):
        prima_riga = gruppo.iloc[0]
        monthly = []
        for _, r in gruppo.sort_values(["year", "month"]).iterrows():
            monthly.append({
                "year": int(r["year"]),
                "month": int(r["month"]),
                "presenze": float(r["presenze"]),
                "presenze_annue": float(r["presenze_annue"]),
                "densita_turistica": float(r["densita_turistica"]),
                "intensita_turistica": float(r["intensita_turistica"]),
                "densita_ricettiva": float(r["densita_ricettiva"]),
                "utilizzazione_lorda": float(r["utilizzazione_lorda"]),
                "norms": [
                    None if pd.isna(r[c]) else float(r[c])
                    for c in COLONNE_NORM
                ],
                "overtourism": None if pd.isna(r["overtourism"]) else float(r["overtourism"]),
                "n_indicatori_disponibili": int(r["n_indicatori_disponibili"]),
                "coastal": bool(prima_riga["coastal"]),
                "mountain": bool(prima_riga["mountain"]),
                "p75_overtourism": None if pd.isna(r["p75_overtourism"]) else float(r["p75_overtourism"]),
                "eligible": bool(r["eligible"]),
                "gem_score": None if pd.isna(r["gem_score"]) else float(r["gem_score"]),
                "seasonal_adjustment": float(r["seasonal_adjustment"]),
                "gem_score_norm": None if pd.isna(r["gem_score_norm"]) else float(r["gem_score_norm"]),
                "gem_rank": None if pd.isna(r["gem_rank"]) else int(r["gem_rank"]),
            })

        comuni.append({
            "name": str(prima_riga["name"]),
            "code": int(code),
            "lat": float(prima_riga["lat"]),
            "lng": float(prima_riga["lng"]),
            "coastal": bool(prima_riga["coastal"]),
            "mountain": bool(prima_riga["mountain"]),
            "population": int(prima_riga["population"]),
            "area_kmq": float(prima_riga["area_kmq"]),
            "beds": float(prima_riga["beds"]),
            "monthly": monthly,
        })

    return comuni


def calcola_pesi_stagionali(df: pd.DataFrame) -> list:
    """Pesi stagionali di default (uno per mese, sommano a 1): media delle
    presenze mensili sul dataset, normalizzata. Sostituibile passando
    `seasonal_weights` esplicitamente a `genera_html`."""
    medie = df.groupby("month")["presenze"].mean().reindex(range(1, 13), fill_value=0)
    totale = medie.sum() or 1
    return [round(v / totale, 3) for v in medie]


def calcola_ancore_normalizzazione(df: pd.DataFrame, percentile: float = 0.99) -> dict:
    """Ancore di default per la normalizzazione (winsorization al 99° percentile
    di ciascun indicatore grezzo). Sostituibile passando `normalization_anchors`
    esplicitamente a `genera_html`."""
    colonne = ["densita_turistica", "intensita_turistica", "densita_ricettiva", "utilizzazione_lorda"]
    return {c: round(float(df[c].quantile(percentile)), 2) for c in colonne}


def genera_html(
    df: pd.DataFrame,
    region_geojson: dict,
    output_path: str = "index.html",
    title: str = "Sardegna: Gemme Nascoste",
    seasonal_weights: list | None = None,
    normalization_anchors: dict | None = None,
    data_note: str = "Dati elaborati dalla pipeline di indice di attrattività/overtourism.",
    source_geometry: str = "openpolis/geojson-italy limits_R_20_municipalities.geojson",
) -> str:
    """Costruisce l'HTML completo e lo scrive su `output_path`. Ritorna il path."""

    comuni = df_to_comuni(df)
    years = sorted(df["year"].dropna().unique().tolist())
    years = [int(y) for y in years]

    if seasonal_weights is None:
        seasonal_weights = calcola_pesi_stagionali(df)
    if normalization_anchors is None:
        normalization_anchors = calcola_ancore_normalizzazione(df)

    embedded_data = {
        "meta": {
            "title": title,
            "generated": pd.Timestamp.now().isoformat(),
            "data_note": data_note,
            "source_geometry": source_geometry,
            "years": years,
            "months": MESI_ITALIANI,
            "seasonal_weights": seasonal_weights,
            "normalization_anchors": normalization_anchors,
            "algorithm": (
                "base_seclusion × quality_multiplier × (1 + seasonal_adjustment); "
                "eligibility: n_indicatori_disponibili >= 2, presenze > 0, "
                "overtourism < p75 mensile"
            ),
        },
        "region": region_geojson,
        "comuni": comuni,
    }

    head = TEMPLATE_HEAD.read_text(encoding="utf-8")  # termina con '...id="embedded-data">'
    tail = TEMPLATE_TAIL.read_text(encoding="utf-8")   # inizia con '</script>...' -> NO, vedi sotto

    # head termina subito dopo l'apertura del tag <script id="embedded-data">,
    # quindi qui inseriamo il JSON e chiudiamo il tag prima di appendere il tail
    # (che contiene il secondo <script> con la logica applicativa).
    html = head + json.dumps(embedded_data, ensure_ascii=False, separators=(",", ":")) + "</script>\n" + tail

    Path(output_path).write_text(html, encoding="utf-8")
    return output_path


# ------------------------------------------------------------------------
# ESEMPIO DI USO / DATI FITTIZI DI PROVA
# Sostituisci `carica_dati_di_esempio()` con il caricamento del tuo df reale
# (es. output del notebook 02_indice_da_osm.ipynb + calcolo mensile).
# ------------------------------------------------------------------------

def carica_dati_di_esempio() -> tuple[pd.DataFrame, dict]:
    import random

    random.seed(42)
    comuni_static = [
        {"name": "Baunei", "code": 91013, "lat": 40.0339, "lng": 9.6425,
         "coastal": True, "mountain": True, "population": 3800, "area_kmq": 210.0, "beds": 900},
        {"name": "Tresnuraghes", "code": 95067, "lat": 40.2182, "lng": 8.4932,
         "coastal": True, "mountain": False, "population": 2788, "area_kmq": 31.28, "beds": 104},
        {"name": "Tuili", "code": 111091, "lat": 39.7098, "lng": 8.9646,
         "coastal": False, "mountain": False, "population": 1874, "area_kmq": 24.26, "beds": 46},
    ]

    righe = []
    for c in comuni_static:
        for year in (2023, 2024, 2025):
            for month in range(1, 13):
                presenze = max(1.0, random.gauss(50, 30))
                riga = dict(c)
                riga.update({
                    "year": year, "month": month,
                    "presenze": presenze, "presenze_annue": presenze * 12,
                    "densita_turistica": presenze / c["area_kmq"],
                    "intensita_turistica": presenze / c["population"],
                    "densita_ricettiva": c["beds"] / c["area_kmq"],
                    "utilizzazione_lorda": presenze / max(c["beds"], 1),
                    "overtourism": min(0.99, presenze / 5000),
                    "p75_overtourism": 0.02,
                    "n_indicatori_disponibili": 4,
                    "eligible": True,
                    "gem_score": random.uniform(0.7, 1.6),
                    "seasonal_adjustment": [0.2, 0.2, 0.1, 0.1, 0.1, 0.05, 0.05, 0.05,
                                             0.15, 0.15, 0.15, 0.2][month - 1],
                    "gem_score_norm": random.uniform(50, 100),
                    "gem_rank": random.randint(1, 300),
                    "norm_densita_turistica": random.uniform(0, 0.3),
                    "norm_intensita_turistica": random.uniform(0, 0.3),
                    "norm_densita_ricettiva": random.uniform(0, 0.3),
                    "norm_utilizzazione_lorda": random.uniform(0, 0.3),
                })
                righe.append(riga)

    df = pd.DataFrame(righe)

    # Geometria di esempio (un rettangolo attorno alla Sardegna): sostituiscila
    # con la geometria reale (es. unione dei confini comunali dal geojson).
    region_geojson = {
        "type": "Polygon",
        "coordinates": [[
            [8.1, 38.9], [9.9, 38.9], [9.9, 41.3], [8.1, 41.3], [8.1, 38.9],
        ]],
    }

    return df, region_geojson


if __name__ == "__main__":
    df, region_geojson = carica_dati_di_esempio()
    out = genera_html(df, region_geojson, output_path="index.html")
    print(f"Creato: {out}")
