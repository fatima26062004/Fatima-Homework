# Lebanon Tourism Explorer

An interactive Streamlit page on the **Tourism Lebanon 2023** dataset (Impact Open Data / AUB CODEC).
It shows where Lebanon's hotels, restaurants, cafés and guest houses are concentrated and whether towns
with more of them score higher on the Tourism Index (0–10).

**Live app:** (https://fatima-homework-l9hu3bzrwiafw5kahsot3g.streamlit.app)

## Features
- **Facility type** (radio): switches both charts between hotels, restaurants, cafés and guest houses.
- **Area to drill into** (dropdown): lists only areas that have the chosen facility, ranked by count, so the
  two controls are linked (facility → area → towns).
- Bar chart of the top 10 areas with the selected area highlighted, and a line chart comparing the
  area's average Tourism Index with the national average.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Files
- `app.py` – the Streamlit app
- `Tourism_Lebanon_2023.csv` – dataset
- `requirements.txt` – Python dependencies

Data source: https://impact.cib.gov.lb/home#open_data_section via http://linked.aub.edu.lb/CODEC
