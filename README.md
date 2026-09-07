# Security Check - Streamlit Dashboard

<img width="1364" height="599" alt="Screenshot 2026-09-07 142922" src="https://github.com/user-attachments/assets/93e1d7dc-6310-4dcc-a079-a2c8fe2e2bff" />

<img width="1365" height="602" alt="Screenshot 2026-09-07 143004" src="https://github.com/user-attachments/assets/bc5d41e7-4790-4219-ba77-603054abd4c1" />

This project converts the `SECURITY_CHECK.ipynb` traffic-stop SQL analysis into an interactive Streamlit dashboard.

## Stack
- Python
- PostgreSQL
- SQLAlchemy
- SQL
- Plotly
- Streamlit
- Pandas

## Database expected
- Host: `localhost`
- Port: `5432`
- Database: `traffic`
- Table: `traffic_stops`
- User: `postgres`

The app only reads from the existing table. It does not run the notebook's `to_sql(..., if_exists="replace")` step.

## 1. Install packages

```bash
pip install -r requirements.txt
```

## 2. Configure PostgreSQL

Recommended: create this file:

`.streamlit/secrets.toml`

Use the template in `.streamlit/secrets.toml.example`.

Do NOT upload your real password to GitHub.

## 3. Run the dashboard

```bash
streamlit run app.py
```

The browser will open the interactive dashboard.

## Dashboard sections

1. Overview
2. Vehicle Analysis
3. Demographics
4. Time & Duration
5. Violation Analysis
6. Location Analysis

The sidebar provides interactive filters for:
- Country
- Driver gender
- Driver race
- Violation
- Driver age

The original notebook contains 14 SQL business questions; this app keeps those analyses and converts their results into interactive Plotly charts.
