"""
Lebanon Tourism Explorer — Streamlit app
Dataset: Tourism Lebanon 2023 (Impact Open Data / AUB CODEC linked data)
Author: Fatima Hazime
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Lebanon Tourism Explorer", page_icon="🏨", layout="wide")

HIGHLIGHT = "#2a78d6"   # selected area / area line
NATIONAL = "#eb6834"    # national comparison line
MUTED = "#c9c8c2"       # all other bars

FACILITIES = {
    "Hotels": "Total number of hotels",
    "Restaurants": "Total number of restaurants",
    "Cafés": "Total number of cafes",
    "Guest houses": "Total number of guest houses",
}

# Buckets used for the "number of facilities per town" axis of the line chart
BINS = [-1, 0, 1, 2, 5, 10, float("inf")]
BIN_LABELS = ["0", "1", "2", "3–5", "6–10", "11+"]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def _area_name(uri: str) -> str:
    """Turn a DBpedia URI into a readable area name.

    The CSV stores names like 'ZahlÃ©_District' (UTF-8 bytes read as
    Latin-1), so we re-decode them to get 'Zahlé District'.
    """
    name = uri.rstrip("/").split("/")[-1].replace("_", " ")
    try:
        name = name.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return name.replace(", Lebanon", "")


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv("Tourism_Lebanon_2023.csv")
    df["Area"] = df["refArea"].apply(_area_name)
    df["Town"] = df["Town"].str.strip()
    keep = ["Town", "Area", "Tourism Index"] + list(FACILITIES.values())
    return df[keep]


df = load_data()

# ---------------------------------------------------------------------------
# Header and context
# ---------------------------------------------------------------------------
st.title("Where is Lebanon's tourism infrastructure?")
st.markdown(
    f"""
This page uses the **Tourism Lebanon 2023** dataset published by Impact Open Data
and the AUB CODEC linked-data project. Each row is one town
(**{len(df):,} towns** in **{df['Area'].nunique()} districts/governorates**) and records how many
hotels, restaurants, cafés and guest houses it has, as well as **Tourism Index from 0 to 10**
that scores the town's tourism development. Towns score higher when they have restaurants,
cafés and hotels.

Pick a facility type and an area below to see **which areas lead**, and **whether towns with more of that
facility also score higher on the Tourism Index**.
"""
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Towns covered", f"{len(df):,}")
k2.metric("Hotels nationwide", f"{int(df[FACILITIES['Hotels']].sum()):,}")
k3.metric("Restaurants nationwide", f"{int(df[FACILITIES['Restaurants']].sum()):,}")
k4.metric("Average Tourism Index", f"{df['Tourism Index'].mean():.2f} / 10")

st.subheader("Key insights")
st.markdown(
    """
1. **Hotels are concentrated in a few mountain districts.** Bsharri District has only 20 of the 1,137
   towns (under 2%) but 41 of the country's 383 hotels (10.7%), more than any other area.
2. **The "leader" depends on the facility you look at.** Bsharri leads for hotels, Baabda for
   restaurants, and Akkar for both cafés and guest houses, so no single area dominates every type of
   tourism infrastructure.
3. **More facilities go with a higher Tourism Index.** Towns with no restaurants average 0.87 on the
   index, while the 48 towns with 11 or more restaurants average 8.6.
"""
)

st.divider()

# ---------------------------------------------------------------------------
# Interaction features (linked)
# ---------------------------------------------------------------------------
st.subheader("Explore")
c1, c2 = st.columns([1, 1])

with c1:
    facility = st.radio(
        "1 · Facility type",
        list(FACILITIES.keys()),
        horizontal=True,
        help="Changes the measure in both charts and re-ranks the area list on the right.",
    )
col = FACILITIES[facility]

# Link: the facility choice decides WHICH areas can be picked and in WHAT order.
area_totals = df.groupby("Area")[col].sum().sort_values(ascending=False)
area_totals = area_totals[area_totals > 0]
area_options = area_totals.index.tolist()

# Keep the user's area if it is still valid for the new facility; otherwise
# fall back to the top area (prevents an invalid value in session_state).
if st.session_state.get("area") not in area_options:
    st.session_state["area"] = area_options[0]

with c2:
    area = st.selectbox(
        f"2 · Area to drill into (ranked by {facility.lower()})",
        area_options,
        key="area",
        format_func=lambda a: f"{a} ({int(area_totals[a])} {facility.lower()})",
        help="Areas are ranked by how many of the selected facility they have.",
    )

area_df = df[df["Area"] == area]

# ---------------------------------------------------------------------------
# Chart 1 — bar: top 10 areas for the chosen facility, selected area highlighted
# ---------------------------------------------------------------------------
top = area_totals.head(10)
if area not in top.index:  # always show the selected area, even outside the top 10
    top = pd.concat([top, area_totals.loc[[area]]])

bar_colors = [HIGHLIGHT if a == area else MUTED for a in top.index]
share = top / df[col].sum() * 100

fig_bar = go.Figure(
    go.Bar(
        x=top.index,
        y=top.values,
        marker=dict(color=bar_colors, cornerradius=4),
        customdata=share.values,
        hovertemplate="<b>%{x}</b><br>%{y} " + facility.lower() + " (%{customdata:.1f}% of national)<extra></extra>",
    )
)
fig_bar.add_annotation(
    x=area, y=area_totals[area], text=f"<b>{int(area_totals[area])}</b>",
    showarrow=False, yshift=12, font=dict(color=HIGHLIGHT, size=13),
)
fig_bar.update_layout(
    title=f"Total {facility.lower()} — top 10 areas" + (" + your selection" if len(top) > 10 else ""),
    xaxis_title=None, yaxis_title=f"Number of {facility.lower()}",
    plot_bgcolor="rgba(0,0,0,0)", height=430, margin=dict(t=60, b=10, l=10, r=10),
    bargap=0.25,
)
fig_bar.update_xaxes(tickangle=-35)
fig_bar.update_yaxes(gridcolor="rgba(128,128,128,0.2)")

# ---------------------------------------------------------------------------
# Chart 2 — line: average Tourism Index by number of facilities in a town
# ---------------------------------------------------------------------------
def index_by_bucket(data: pd.DataFrame) -> pd.DataFrame:
    bucket = pd.cut(data[col], bins=BINS, labels=BIN_LABELS)
    out = data.groupby(bucket, observed=False)["Tourism Index"].agg(["mean", "size"])
    return out[out["size"] > 0].reset_index(names="bucket")


nat = index_by_bucket(df)
loc = index_by_bucket(area_df)

fig_line = go.Figure()
fig_line.add_trace(go.Scatter(
    x=nat["bucket"], y=nat["mean"], name="All of Lebanon", mode="lines+markers",
    line=dict(color=NATIONAL, width=2, dash="dot"), marker=dict(size=8),
    customdata=nat["size"],
    hovertemplate="Lebanon · %{x} " + facility.lower() + "<br>Avg index %{y:.2f} (%{customdata} towns)<extra></extra>",
))
fig_line.add_trace(go.Scatter(
    x=loc["bucket"], y=loc["mean"], name=area, mode="lines+markers",
    line=dict(color=HIGHLIGHT, width=2.5), marker=dict(size=9),
    customdata=loc["size"],
    hovertemplate=area + " · %{x} " + facility.lower() + "<br>Avg index %{y:.2f} (%{customdata} towns)<extra></extra>",
))
fig_line.update_layout(
    title=f"Average Tourism Index by number of {facility.lower()} in a town",
    xaxis=dict(title=f"{facility} in the town", categoryorder="array", categoryarray=BIN_LABELS),
    yaxis=dict(title="Average Tourism Index (0–10)", range=[0, 10.5], gridcolor="rgba(128,128,128,0.2)"),
    plot_bgcolor="rgba(0,0,0,0)", height=430, margin=dict(t=60, b=10, l=10, r=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
    hovermode="x unified",
)

g1, g2 = st.columns(2)
g1.plotly_chart(fig_bar)
g2.plotly_chart(fig_line)

# ---------------------------------------------------------------------------
# Dynamic insight for the current selection
# ---------------------------------------------------------------------------
has = area_df[col] > 0
n_has, n_all = int(has.sum()), len(area_df)
rank = area_options.index(area) + 1
msg = (
    f"**{area}** ranks **#{rank} of {len(area_options)}** areas for {facility.lower()} "
    f"with **{int(area_totals[area])}** ({area_totals[area] / df[col].sum() * 100:.1f}% of the national total). "
    f"{n_has} of its {n_all} towns have at least one."
)
if 0 < n_has < n_all:
    msg += (
        f" Those towns average **{area_df.loc[has, 'Tourism Index'].mean():.1f}** on the Tourism Index, "
        f"versus **{area_df.loc[~has, 'Tourism Index'].mean():.1f}** for towns without any."
    )
st.info(msg)

with st.expander(f"See the towns in {area} (table view)"):
    table = (
        area_df[["Town", col, "Tourism Index"]]
        .rename(columns={col: facility})
        .sort_values([facility, "Tourism Index"], ascending=False)
        .reset_index(drop=True)
    )
    st.dataframe(table, hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Design justifications
# ---------------------------------------------------------------------------
st.subheader("Design justification")

with st.expander("Feature 1 — Facility type (radio buttons)"):
    st.markdown(
        """
**User question:** *"Which areas lead Lebanon in hotels, and is it the same areas for restaurants,
cafés or guest houses?"* Switching the facility re-ranks the bar chart and re-draws the line chart, so the
reader sees at once that Bsharri leads for hotels but Baabda leads for restaurants and Akkar for cafés.

**Why this widget:** there are only four options and the user needs exactly one at a time, so a horizontal
radio shows every choice on screen with one click to switch. I considered a dropdown, but it hides the
options behind a click, and a multiselect would allow mixing hotels with cafés, which adds up counts that
do not mean the same thing.

**Course concept — reducing clutter:** instead of four bar charts and four line charts side by side, one
control swaps the measure inside the same two charts. The page stays short, and the four facility types are
still one click away.
"""
    )

with st.expander("Feature 2 — Area to drill into (dropdown linked to Feature 1)"):
    st.markdown(
        """
**User question:** *"How does a specific area compare with the rest of the country: does it rank high,
and do its towns with more facilities score higher on the Tourism Index?"*

**How it is linked:** the list of areas is rebuilt from the facility chosen in Feature 1. Areas are re-ranked
from most to fewest of that facility and each label shows the count (e.g. "Bsharri District (41 hotels)" when
Hotels is chosen, "Baabda District (301 restaurants)" at the top when Restaurants is chosen). The area you
picked stays selected, and its rank, share and town table update to the new facility. This is a drill-down
(facility → area → towns) rather than two independent filters.

**Why this widget:** with up to 25 areas, a radio list would take too much space and a multiselect would
put several areas on the line chart at once, making it hard to read. A single-select dropdown keeps one area
in focus. I considered a clickable map, but the data has no coordinates or boundaries.

**Course concept — focusing attention and providing context:** the selected area is the only coloured bar
(everything else is grey), and on the line chart it is drawn against the national average. The reader's eye
goes to the chosen area, and the national line gives the context to judge whether it is above or below
typical.
"""
    )

st.caption(
    "Source: Tourism Lebanon 2023 — Impact Open Data (impact.cib.gov.lb) via "
    "linked.aub.edu.lb/CODEC. Built with Streamlit and Plotly."
)
