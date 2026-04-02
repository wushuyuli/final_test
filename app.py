import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import geopandas as gpd
import json

st.set_page_config(layout="wide", page_title="City Safety Dashboard")

import os

def get_file_path(filename):
    """
    Tries multiple locations to find the file.
    Works in VS Code, Colab, and deployment.
    """
    possible_paths = [
        filename,                          # same folder
        f"./{filename}",
        f"/content/{filename}",            # Colab
        f"/mnt/data/{filename}",           # some environments
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    raise FileNotFoundError(f"{filename} not found in any known location.")

st.markdown("""
<style>

/* MULTISELECT TAGS (force override) */
div[data-baseweb="tag"],
div[data-baseweb="tag"] span,
div[data-baseweb="tag"] div {
    background-color: #4C78A8 !important;  /* calm blue */
    color: white !important;
}

/* Remove default red close button background */
div[data-baseweb="tag"] svg {
    fill: white !important;
}

/* Hover state */
div[data-baseweb="tag"]:hover {
    background-color: #3B5F8A !important;
}

/* Selected dropdown items */
div[role="listbox"] div[aria-selected="true"] {
    background-color: #E6EEF6 !important;
    color: black !important;
}

/* Checkbox */
input[type="checkbox"] {
    accent-color: #4C78A8;
}

/* Fix for new Streamlit versions (VERY IMPORTANT) */
span[data-baseweb="tag"] {
    background-color: #4C78A8 !important;
    color: white !important;
}

/* Remove red theme overrides */
:root {
    --red-50: #4C78A8 !important;
    --red-60: #4C78A8 !important;
    --red-70: #3B5F8A !important;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>

/* Sidebar background */
section[data-testid="stSidebar"] {
    background-color: #F7F9FC;
}

/* Main app background */
[data-testid="stAppViewContainer"] {
    background-color: #FAFBFD;
}

/* Buttons */
.stButton > button {
    background-color: #4C78A8;
    color: white;
    border-radius: 6px;
    border: none;
}

.stButton > button:hover {
    background-color: #3B5F8A;
}

/* Headers */
h1, h2, h3 {
    color: #2C3E50;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>

/* Main app background */
[data-testid="stAppViewContainer"] {
    background-color: #F5F7FA;  /* light blue-grey */
}

/* Sidebar background */
section[data-testid="stSidebar"] {
    background-color: #EEF2F7;  /* slightly darker for contrast */
}

/* Optional: content block background (makes cards pop) */
[data-testid="stVerticalBlock"] {
    background-color: transparent;
}

/* Remove white block effect */
.main {
    background-color: transparent;
}

</style>
""", unsafe_allow_html=True)

# =========================
# LOAD FILES (LOCAL ONLY)
# =========================
import os
import pandas as pd
import geopandas as gpd
import streamlit as st

# =========================
# LOAD DATA (WORKS EVERYWHERE)
# =========================
@st.cache_data
def load_data():
    return pd.read_csv("incidents_17952.csv")

@st.cache_data
def load_geo():
    with open("zones_17952.geojson") as f:
        return json.load(f)


# =========================
# CLEANING PIPELINE
# =========================
def clean_data(df):
    df = df.copy()

    # Datetime
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    df["closed_at"] = pd.to_datetime(df["closed_at"], errors="coerce", utc=True)

    # Deduplicate
    df = df.sort_values("created_at")
    df = df.drop_duplicates("incident_id", keep="last")

    # Category
    df["category"] = df["category"].astype(str).str.strip().str.lower()
    df["category"] = df["category"].replace({
        "theftt": "theft",
        "assult": "assault"
    }).str.title()

    # Priority
    df["priority"] = df["priority"].astype(str).str.lower().replace({
        "low": 1, "medium": 3, "med": 3, "high": 5
    })
    df["priority"] = pd.to_numeric(df["priority"], errors="coerce")

    # Cost
    df["cost_estimate"] = (
        df["cost_estimate"].astype(str)
        .str.replace(r"[^\d.]", "", regex=True)
    )
    df["cost_estimate"] = pd.to_numeric(df["cost_estimate"], errors="coerce")

    # Coordinates
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    # Fix swapped
    swap = (df["lat"].abs() > 90) | (df["lon"].abs() > 180)
    df.loc[swap, ["lat", "lon"]] = df.loc[swap, ["lon", "lat"]].values

    df = df[
        df["lat"].between(-90, 90) &
        df["lon"].between(-180, 180)
    ]

    # Features
    today = pd.Timestamp.now(tz="UTC")
    df["open_days"] = (df["closed_at"].fillna(today) - df["created_at"]).dt.days
    df["month"] = df["created_at"].dt.to_period("M").astype(str)
    df["is_open"] = df["closed_at"].isna()

    df["week"] = df["created_at"].dt.to_period("W").astype(str)
    df["valid_coords"] = (
        df["lat"].between(-90, 90) &
        df["lon"].between(-180, 180)
    )

    return df


# =========================
# SPATIAL JOIN (FIXED)
# =========================
def spatial_join(df, zones_gdf):
    try:
        import geopandas as gpd

        # Create points GeoDataFrame
        gdf = gpd.GeoDataFrame(
            df.copy(),
            geometry=gpd.points_from_xy(df["lon"], df["lat"]),
            crs="EPSG:4326"
        )

        # Ensure CRS is set
        if zones_gdf.crs is None:
            zones_gdf = zones_gdf.set_crs(epsg=4326)

        # Spatial join
        joined = gpd.sjoin(gdf, zones_gdf, how="left", predicate="within")

        # Reset index to avoid duplicate index error
        joined = joined.reset_index(drop=True)
        df = df.reset_index(drop=True)

        # Assign zone (adjust column name if needed)
        zone_col = "zone_name" if "zone_name" in joined.columns else joined.columns[-1]
        df["zone"] = joined[zone_col]

    except Exception as e:
        # fallback
        df["zone"] = df.get("zone_hint", "Unknown")

    return df

# =========================
# LOAD + CLEAN
# =========================
df_raw = load_data()
zones_gdf = load_geo()

df = clean_data(df_raw)
df = spatial_join(df, zones_gdf)


# =========================
# SIDEBAR FILTERS (CLEAN)
# =========================
st.sidebar.title("Filters")

date_range = st.sidebar.date_input(
    "Date range",
    [df["created_at"].min(), df["created_at"].max()]
)

categories = st.sidebar.multiselect(
    "Category",
    options=sorted(df["category"].dropna().unique()),
    default=sorted(df["category"].dropna().unique())
)

zones = st.sidebar.multiselect(
    "Zone",
    options=sorted(df["zone"].dropna().unique()),
    default=sorted(df["zone"].dropna().unique())
)

open_only = st.sidebar.checkbox("Open only")

# =========================
# APPLY FILTERS
# =========================
df_f = df[
    (df["created_at"].dt.date >= date_range[0]) &
    (df["created_at"].dt.date <= date_range[1]) &
    (df["category"].isin(categories)) &
    (df["zone"].isin(zones))
]

if open_only:
    df_f = df_f[df_f["is_open"]]


# =========================
# DASHBOARD
# =========================
st.title("🚔 City Safety Dashboard")

# KPI
col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Incidents", len(df_f))
col2.metric("% Open", f"{df_f['is_open'].mean()*100:.1f}%")
col3.metric("Median Open Days", f"{df_f['open_days'].median():.1f}")
col4.metric("Total Cost", f"${df_f['cost_estimate'].sum():,.0f}")

# =========================
# MAP
# =========================
metric_label = st.selectbox("Map metric:", ["Incident Count", "Average Open Days"])

metric = "count" if metric_label == "Incident Count" else "avg_open_days"

agg = df_f.groupby("zone").agg({
    "incident_id": "count",
    "open_days": "mean"
}).reset_index()

agg.columns = ["zone", "count", "avg_open_days"]

# =========================
# SLA LOGIC
# =========================
SLA_TARGET = 7  # days (you can change)

agg["over_sla"] = agg["avg_open_days"] > SLA_TARGET
agg["over_sla_label"] = agg["over_sla"].map({True: "Over SLA", False: "Within SLA"})
agg["sla_target"] = SLA_TARGET

fig_map = px.choropleth(
    agg,
    geojson=zones_gdf,
    locations="zone",
    featureidkey="properties.zone_name",
    color=metric,
    
    # 🔴 RED SCALE LIKE YOUR IMAGE
    color_continuous_scale=[
        "#f5e0d6",
        "#f4a582",
        "#d6604d",
        "#b2182b",
        "#67000d"
    ],

    # ✅ HOVER DATA
    hover_data={
        "zone": True,
        "count": True,
        "avg_open_days": ":.2f",
        "sla_target": True,
        "over_sla_label": True
    }
)

fig_map.update_traces(
    hovertemplate=
    "<b>%{customdata[0]}</b><br>" +
    "Value: %{customdata[3]:.2f}<br>" +
    "SLA Target: %{customdata[1]} days<br>" +
    "Status: %{customdata[2]}<extra></extra>",

    customdata=np.stack([
        agg["zone"],
        agg["sla_target"],
        agg["over_sla_label"],
        agg[metric]   # 👈 dynamic metric FIX
    ], axis=-1)
)

fig_map.update_geos(fitbounds="locations", visible=False)

# =========================
# ADD ZONE LABELS
# =========================
# =========================
# ADD ZONE LABELS (NO GEOPANDAS)
# =========================

import numpy as np

lons = []
lats = []
labels = []

for feature in zones_geojson["features"]:
    coords = feature["geometry"]["coordinates"]

    # Handle Polygon vs MultiPolygon
    if feature["geometry"]["type"] == "Polygon":
        polygon = coords[0]
    else:  # MultiPolygon
        polygon = coords[0][0]

    xs = [point[0] for point in polygon]
    ys = [point[1] for point in polygon]

    # Simple centroid (average)
    lons.append(np.mean(xs))
    lats.append(np.mean(ys))

    # Use zone_id or fallback
    props = feature["properties"]
    labels.append(props.get("zone_id", props.get("zone_name", "")))

# Add labels to map
fig_map.add_scattergeo(
    lon=lons,
    lat=lats,
    text=labels,
    mode="text",
    showlegend=False
)


# =========================
# TIME SERIES
# =========================
ts = df_f.groupby(["month", "category"]).size().reset_index(name="count")

fig_ts = px.line(ts, x="month", y="count", color="category")

fig_ts.update_layout(
    title="Incidents Over Time by Category",
    title_x=0.02
)

st.plotly_chart(fig_ts, use_container_width=True)


# =========================
# BAR
# =========================
top = df_f["category"].value_counts().reset_index()
top.columns = ["category", "count"]

fig_bar = px.bar(top, x="category", y="count", color="category")

fig_bar.update_layout(
    title="Top Incident Categories",
    title_x=0.02
)

st.plotly_chart(fig_bar, use_container_width=True)


# =========================
# INSIGHTS
# =========================
st.subheader("Insights")

zone_perf = df_f.groupby("zone")["open_days"].mean().sort_values(ascending=False)

if len(zone_perf) > 0:
    st.write(f"Most over-SLA zone: **{zone_perf.index[0]}** ({zone_perf.iloc[0]:.1f} days)")

recent = df_f[df_f["created_at"] > df_f["created_at"].max() - pd.Timedelta(days=30)]

if len(recent) > 0:
    best = recent.groupby("category")["open_days"].mean().sort_values().index[0]
    st.write(f"Fastest improving category: **{best}**")


# =========================
# EXPORT BUTTON
# =========================
st.download_button(
    label="📥 Download Filtered Data",
    data=df_f.to_csv(index=False),
    file_name="filtered_data.csv",
    mime="text/csv"
)
