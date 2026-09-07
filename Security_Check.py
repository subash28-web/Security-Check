
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# ============================================================
# SECURITY CHECK - Traffic Stop Analytics Dashboard
# Streamlit + PostgreSQL + SQLAlchemy + Plotly
# ============================================================

st.set_page_config(
    page_title="Security Check | Traffic Analytics",
    page_icon="🚔",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------- Styling --------------------------
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0;
    }
    .sub-title {
        color: #6b7280;
        margin-top: 0;
    }
    div[data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,.20);
        padding: 12px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------- Database ----------------------------
def get_engine():
    """Create a PostgreSQL connection from Streamlit secrets or environment variables."""
    try:
        # Preferred: .streamlit/secrets.toml
        if "postgres" in st.secrets:
            cfg = st.secrets["postgres"]
            user = cfg.get("user", "postgres")
            password = cfg.get("password", "")
            host = cfg.get("host", "localhost")
            port = cfg.get("port", 5432)
            database = cfg.get("database", "traffic")
        else:
            user = os.getenv("DB_USER", "postgres")
            password = os.getenv("DB_PASSWORD", "")
            host = os.getenv("DB_HOST", "localhost")
            port = os.getenv("DB_PORT", "5432")
            database = os.getenv("DB_NAME", "traffic")

        if not password:
            st.sidebar.warning("Enter your PostgreSQL password to connect.")
            password = st.sidebar.text_input(
                "PostgreSQL Password",
                type="password",
                help="Your password is used only for this Streamlit session."
            )

        if not password:
            return None

        url = (
            f"postgresql+psycopg2://{user}:{password}"
            f"@{host}:{port}/{database}"
        )
        return create_engine(url, pool_pre_ping=True)

    except Exception as exc:
        st.error(f"Database configuration error: {exc}")
        return None


@st.cache_data(ttl=300)
def run_query(_engine, query, params=None):
    """Run a read-only SQL query and return a DataFrame."""
    params = params or {}
    with _engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


@st.cache_data(ttl=300)
def get_filter_values(_engine):
    values = {}
    for col in ["country_name", "driver_gender", "driver_race", "violation",
                "stop_outcome", "stop_duration", "search_type"]:
        q = f"""
            SELECT DISTINCT {col}
            FROM traffic_stops
            WHERE {col} IS NOT NULL
            ORDER BY {col}
        """
        values[col] = run_query(_engine, q)[col].tolist()
    return values


def build_where(country, gender, race, violation, age_range):
    """Build a safe WHERE clause using SQLAlchemy named parameters."""
    clauses = ["1=1"]
    params = {}

    if country != "All":
        clauses.append("country_name = :country")
        params["country"] = country

    if gender != "All":
        clauses.append("driver_gender = :gender")
        params["gender"] = gender

    if race != "All":
        clauses.append("driver_race = :race")
        params["race"] = race

    if violation != "All":
        clauses.append("violation = :violation")
        params["violation"] = violation

    clauses.append("driver_age BETWEEN :min_age AND :max_age")
    params["min_age"] = age_range[0]
    params["max_age"] = age_range[1]

    return " AND ".join(clauses), params


# ---------------------- Header ------------------------------
st.markdown('<p class="main-title">🚔 Security Check</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-title">Interactive Traffic Stop & Security Analytics Dashboard</p>',
    unsafe_allow_html=True
)

engine = get_engine()

if engine is None:
    st.info(
        "Connect to your PostgreSQL database from the sidebar. "
        "The dashboard expects database **traffic** and table **traffic_stops**."
    )
    st.stop()

# Test connection
try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except SQLAlchemyError as exc:
    st.error(
        "Could not connect to PostgreSQL. Check that PostgreSQL is running "
        "and your host, port, database, username and password are correct."
    )
    st.caption(str(exc))
    st.stop()

# ---------------------- Sidebar -----------------------------
st.sidebar.header("🎛️ Dashboard Filters")

try:
    filters = get_filter_values(engine)
except SQLAlchemyError as exc:
    st.error(
        "Connected to PostgreSQL, but the table `traffic_stops` could not be read."
    )
    st.caption(str(exc))
    st.stop()

country = st.sidebar.selectbox(
    "Country", ["All"] + filters["country_name"]
)
gender = st.sidebar.selectbox(
    "Driver Gender", ["All"] + filters["driver_gender"]
)
race = st.sidebar.selectbox(
    "Driver Race", ["All"] + filters["driver_race"]
)
violation = st.sidebar.selectbox(
    "Violation", ["All"] + filters["violation"]
)

age_range = st.sidebar.slider(
    "Driver Age",
    min_value=0,
    max_value=100,
    value=(0, 100)
)

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

where_sql, params = build_where(
    country, gender, race, violation, age_range
)

# ---------------------- KPI cards ---------------------------
kpi_query = f"""
SELECT
    COUNT(*) AS total_stops,
    COUNT(*) FILTER (WHERE is_arrested = TRUE) AS arrests,
    COUNT(*) FILTER (WHERE search_conducted = TRUE) AS searches,
    COUNT(*) FILTER (WHERE drugs_related_stop = TRUE) AS drug_stops,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_arrested = TRUE)
        / NULLIF(COUNT(*), 0), 2
    ) AS arrest_rate
FROM traffic_stops
WHERE {where_sql}
"""

kpi = run_query(engine, kpi_query, params).iloc[0]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🚗 Total Stops", f"{int(kpi['total_stops']):,}")
c2.metric("⚖️ Arrests", f"{int(kpi['arrests']):,}")
c3.metric("🔎 Searches", f"{int(kpi['searches']):,}")
c4.metric("💊 Drug-Related Stops", f"{int(kpi['drug_stops']):,}")
c5.metric("📊 Arrest Rate", f"{float(kpi['arrest_rate'] or 0):.2f}%")

st.divider()

# ------------------------- Tabs -----------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Overview",
    "🚗 Vehicle Analysis",
    "🧍 Demographics",
    "🕒 Time & Duration",
    "⚖️ Violation Analysis",
    "🌍 Location Analysis",
])

# ============================================================
# TAB 1 - OVERVIEW
# ============================================================
with tab1:
    st.subheader("Traffic Stop Overview")

    col1, col2 = st.columns(2)

    with col1:
        q = f"""
        SELECT stop_outcome, COUNT(*) AS total
        FROM traffic_stops
        WHERE {where_sql}
        GROUP BY stop_outcome
        ORDER BY total DESC
        """
        df = run_query(engine, q, params)
        fig = px.bar(
            df, x="stop_outcome", y="total",
            title="Stop Outcomes",
            labels={"stop_outcome": "Outcome", "total": "Stops"},
            text_auto=True
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        q = f"""
        SELECT driver_gender, COUNT(*) AS total
        FROM traffic_stops
        WHERE {where_sql}
        GROUP BY driver_gender
        ORDER BY total DESC
        """
        df = run_query(engine, q, params)
        fig = px.pie(
            df, names="driver_gender", values="total",
            title="Driver Gender Distribution",
            hole=0.45
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top Violations")
    q = f"""
    SELECT violation, COUNT(*) AS total_stops
    FROM traffic_stops
    WHERE {where_sql}
    GROUP BY violation
    ORDER BY total_stops DESC
    LIMIT 10
    """
    df = run_query(engine, q, params)
    fig = px.bar(
        df.sort_values("total_stops"),
        x="total_stops", y="violation",
        orientation="h",
        title="Top 10 Violations",
        text_auto=True
    )
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# TAB 2 - VEHICLE
# ============================================================
with tab2:
    st.subheader("Vehicle-Based Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**1. Top 10 vehicles involved in drug-related stops**")
        q = f"""
        SELECT vehicle_number, COUNT(*) AS drug_stop_count
        FROM traffic_stops
        WHERE drugs_related_stop = TRUE
          AND {where_sql}
        GROUP BY vehicle_number
        ORDER BY drug_stop_count DESC
        LIMIT 10
        """
        df = run_query(engine, q, params)
        fig = px.bar(
            df.sort_values("drug_stop_count"),
            x="drug_stop_count", y="vehicle_number",
            orientation="h",
            title="Drug-Related Stops by Vehicle",
            text_auto=True
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**2. Most frequently searched vehicles**")
        q = f"""
        SELECT vehicle_number, COUNT(*) AS search_count
        FROM traffic_stops
        WHERE search_conducted = TRUE
          AND {where_sql}
        GROUP BY vehicle_number
        ORDER BY search_count DESC
        LIMIT 10
        """
        df = run_query(engine, q, params)
        fig = px.bar(
            df.sort_values("search_count"),
            x="search_count", y="vehicle_number",
            orientation="h",
            title="Most Frequently Searched Vehicles",
            text_auto=True
        )
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 3 - DEMOGRAPHICS
# ============================================================
with tab3:
    st.subheader("Demographic Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**3. Arrests by driver age**")
        q = f"""
        SELECT driver_age, COUNT(*) AS arrests
        FROM traffic_stops
        WHERE is_arrested = TRUE
          AND {where_sql}
        GROUP BY driver_age
        ORDER BY driver_age
        """
        df = run_query(engine, q, params)
        fig = px.line(
            df, x="driver_age", y="arrests",
            markers=True,
            title="Arrests by Driver Age",
            labels={"driver_age": "Age", "arrests": "Arrests"}
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**4. Gender distribution by country and outcome**")
        q = f"""
        SELECT country_name, driver_gender, stop_outcome, COUNT(*) AS total
        FROM traffic_stops
        WHERE {where_sql}
        GROUP BY country_name, driver_gender, stop_outcome
        ORDER BY country_name, driver_gender, stop_outcome
        """
        df = run_query(engine, q, params)
        fig = px.bar(
            df, x="country_name", y="total",
            color="driver_gender",
            facet_col="stop_outcome",
            barmode="group",
            title="Gender Distribution by Country and Outcome",
            labels={"total": "Stops", "country_name": "Country"}
        )
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**5. Search activity by race and gender**")
    q = f"""
    SELECT driver_gender, driver_race, search_type, COUNT(*) AS search_count
    FROM traffic_stops
    WHERE search_conducted = TRUE
      AND {where_sql}
    GROUP BY driver_gender, driver_race, search_type
    ORDER BY search_count DESC
    """
    df = run_query(engine, q, params)
    fig = px.bar(
        df, x="driver_race", y="search_count",
        color="driver_gender",
        facet_col="search_type",
        barmode="group",
        title="Search Activity by Race, Gender and Search Type"
    )
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# TAB 4 - TIME & DURATION
# ============================================================
with tab4:
    st.subheader("Time & Stop Duration")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**6. Traffic stops by hour**")
        q = f"""
        SELECT EXTRACT(HOUR FROM stop_time::time)::int AS hour,
               COUNT(*) AS total_stops
        FROM traffic_stops
        WHERE {where_sql}
        GROUP BY hour
        ORDER BY hour
        """
        df = run_query(engine, q, params)
        fig = px.line(
            df, x="hour", y="total_stops",
            markers=True,
            title="Traffic Stops by Hour",
            labels={"hour": "Hour of Day", "total_stops": "Stops"}
        )
        fig.update_xaxes(dtick=1)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**7. Average stop duration by violation**")
        q = f"""
        SELECT violation,
               AVG(
                   CASE
                       WHEN stop_duration = '0-15 Min' THEN 7.5
                       WHEN stop_duration = '16-30 Min' THEN 23
                       WHEN stop_duration = '30+ Min' THEN 35
                   END
               ) AS avg_stop_minutes
        FROM traffic_stops
        WHERE {where_sql}
        GROUP BY violation
        ORDER BY avg_stop_minutes DESC
        """
        df = run_query(engine, q, params)
        fig = px.bar(
            df, x="violation", y="avg_stop_minutes",
            title="Average Stop Duration by Violation",
            labels={"avg_stop_minutes": "Average Minutes", "violation": "Violation"},
            text_auto=".2f"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**8. Day vs Night arrest rate**")
    q = f"""
    SELECT
        CASE
            WHEN EXTRACT(HOUR FROM stop_time::time) >= 18
              OR EXTRACT(HOUR FROM stop_time::time) < 6
            THEN 'Night'
            ELSE 'Day'
        END AS time_period,
        COUNT(*) AS total_stops,
        COUNT(*) FILTER (WHERE is_arrested = TRUE) AS arrests,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE is_arrested = TRUE)
            / NULLIF(COUNT(*), 0), 2
        ) AS arrest_rate
    FROM traffic_stops
    WHERE {where_sql}
    GROUP BY time_period
    ORDER BY arrest_rate DESC
    """
    df = run_query(engine, q, params)
    fig = px.bar(
        df, x="time_period", y="arrest_rate",
        text="arrest_rate",
        title="Arrest Rate: Day vs Night",
        labels={"arrest_rate": "Arrest Rate (%)", "time_period": "Period"}
    )
    fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# TAB 5 - VIOLATION
# ============================================================
with tab5:
    st.subheader("Violation-Based Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**9. Violations associated with searches or arrests**")
        q = f"""
        SELECT violation,
               COUNT(*) AS searches_or_arrests
        FROM traffic_stops
        WHERE (search_conducted = TRUE OR is_arrested = TRUE)
          AND {where_sql}
        GROUP BY violation
        ORDER BY searches_or_arrests DESC
        """
        df = run_query(engine, q, params)
        fig = px.bar(
            df.sort_values("searches_or_arrests"),
            x="searches_or_arrests", y="violation",
            orientation="h",
            title="Searches or Arrests by Violation",
            text_auto=True
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**10. Most common violations among younger drivers (<25)**")
        q = f"""
        SELECT violation, COUNT(*) AS driver_age_below25
        FROM traffic_stops
        WHERE driver_age < 25
          AND {where_sql}
        GROUP BY violation
        ORDER BY driver_age_below25 DESC
        """
        df = run_query(engine, q, params)
        fig = px.bar(
            df, x="violation", y="driver_age_below25",
            title="Violations Among Drivers Under 25",
            text_auto=True,
            labels={"driver_age_below25": "Stops", "violation": "Violation"}
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**11. Search/arrest rate by violation**")
    q = f"""
    SELECT violation,
           COUNT(*) AS total_stops,
           COUNT(*) FILTER (
               WHERE search_conducted = TRUE OR is_arrested = TRUE
           ) AS searches_or_arrests,
           ROUND(
               100.0 * COUNT(*) FILTER (
                   WHERE search_conducted = TRUE OR is_arrested = TRUE
               ) / NULLIF(COUNT(*), 0), 2
           ) AS search_arrest_rate
    FROM traffic_stops
    WHERE {where_sql}
    GROUP BY violation
    ORDER BY search_arrest_rate ASC
    """
    df = run_query(engine, q, params)
    fig = px.bar(
        df, x="violation", y="search_arrest_rate",
        text="search_arrest_rate",
        title="Search/Arrest Rate by Violation",
        labels={"search_arrest_rate": "Rate (%)", "violation": "Violation"}
    )
    fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# TAB 6 - LOCATION
# ============================================================
with tab6:
    st.subheader("Location-Based Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**12. Drug-related stop rate by country**")
        q = f"""
        SELECT country_name,
               ROUND(
                   100.0 * COUNT(*) FILTER (WHERE drugs_related_stop = TRUE)
                   / NULLIF(COUNT(*), 0), 2
               ) AS drug_related_rate
        FROM traffic_stops
        WHERE {where_sql}
        GROUP BY country_name
        ORDER BY drug_related_rate DESC
        """
        df = run_query(engine, q, params)
        fig = px.bar(
            df, x="country_name", y="drug_related_rate",
            text="drug_related_rate",
            title="Drug-Related Stop Rate by Country",
            labels={"drug_related_rate": "Rate (%)", "country_name": "Country"}
        )
        fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**14. Country with the most searched stops**")
        q = f"""
        SELECT country_name, COUNT(*) AS search_count
        FROM traffic_stops
        WHERE search_conducted = TRUE
          AND {where_sql}
        GROUP BY country_name
        ORDER BY search_count DESC
        """
        df = run_query(engine, q, params)
        fig = px.bar(
            df, x="country_name", y="search_count",
            text_auto=True,
            title="Searches by Country",
            labels={"search_count": "Searches", "country_name": "Country"}
        )
        st.plotly_chart(fig, use_container_width=True)

        if not df.empty:
            top_country = df.iloc[0]["country_name"]
            top_count = int(df.iloc[0]["search_count"])
            st.success(f"Highest searched-stop count: {top_country} ({top_count:,})")

    st.markdown("**13. Arrest rate by country and violation**")
    q = f"""
    SELECT country_name, violation,
           ROUND(
               100.0 * COUNT(*) FILTER (WHERE is_arrested = TRUE)
               / NULLIF(COUNT(*), 0), 2
           ) AS arrest_rate
    FROM traffic_stops
    WHERE {where_sql}
    GROUP BY country_name, violation
    ORDER BY country_name, arrest_rate DESC
    """
    df = run_query(engine, q, params)
    fig = px.bar(
        df, x="violation", y="arrest_rate",
        color="country_name",
        barmode="group",
        text="arrest_rate",
        title="Arrest Rate by Country and Violation",
        labels={"arrest_rate": "Arrest Rate (%)", "violation": "Violation"}
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

