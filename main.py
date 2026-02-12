import streamlit as st
import pandas as pd
import math
import os
from dotenv import load_dotenv
from supabase import create_client
from rapidfuzz import process, fuzz

load_dotenv()

def get_config(key: str, default=None):
    if key in st.secrets:
        return st.secrets[key]
    return os.getenv(key, default)


SUPABASE_URL = get_config("SUPABASE_URL")
SUPABASE_KEY = get_config("SUPABASE_ANON_KEY")
SUPABASE_TABLE = get_config("SUPABASE_TABLE", "wooohoo")

# Session state
if "show_easter_egg" not in st.session_state:
    st.session_state.show_easter_egg = False

# Cache data to avoid repeated queries
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data():
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Fetch all data in chunks of 1000 rows
        all_data = []
        offset = 0
        batch_size = 1000

        while True:
            response = supabase.table(SUPABASE_TABLE).select("*").range(offset, offset + batch_size - 1).execute()
            batch = response.data
            if not batch:
                break
            all_data.extend(batch)
            offset += batch_size
            # Stop if we got fewer rows than batch_size
            if len(batch) < batch_size:
                break

        return pd.DataFrame(all_data)
    except Exception as e:
        st.error(f"❌ Error fetching data from Supabase: {e}")
        st.stop()

st.set_page_config(page_title="Training Providers Search", layout="wide")

st.title("HRDC Training Providers Search Simplified")

st.write(f"This app reads from Supabase database table `{SUPABASE_TABLE}`.")

# ---- READ DATA FROM SUPABASE ----
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Supabase credentials not found. Please check `.env` or `.streamlit/secrets.toml`.")
    st.stop()

df = load_data()

if df.empty:
    st.warning(f"No rows found in table `{SUPABASE_TABLE}`.")
    st.stop()

all_columns = df.columns.tolist()

# ---- SEARCH SETTINGS ----
st.subheader("Search Settings")

# Search mode toggle
search_mode = st.radio("Search Mode", ["Standard", "Fuzzy Match", "Advanced (Boolean)"], horizontal=True)

use_fuzzy = search_mode == "Fuzzy Match"
use_advanced = search_mode == "Advanced (Boolean)"

# Fuzzy threshold (only shown for fuzzy mode)
if use_fuzzy:
    fuzzy_threshold = st.slider("Fuzzy Match Threshold (%)", 50, 100, 75,
                                 help="Higher = more exact match, Lower = more lenient")

# Advanced search operator (only shown for advanced mode)
if use_advanced:
    search_operator = st.selectbox("Match Type", ["OR (any word)", "AND (all words)"], horizontal=True)

# ---- SEARCH INPUT ----
search_query = st.text_input(
    "Global Search (all columns):",
    placeholder="Type anything to filter across all columns..."
)

# ---- FILTERS ----
with st.expander("Advanced Filters", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        name_filter = st.text_input("Filter by Training Provider Name") if "Training Provider Name" in df.columns else ""
        tel_filter = st.text_input("Filter by Telephone No.") if "Telephone No." in df.columns else ""
        # Industry filter
        if "Industry" in df.columns:
            industry_filter = st.selectbox(
                "Filter by Industry",
                ["All"] + sorted(df["Industry"].dropna().unique().tolist())
            )
        else:
            industry_filter = None
    with col2:
        addr_filter = st.text_input("Filter by Address") if "Address" in df.columns else ""
        email_filter = st.text_input("Filter by Email") if "Email" in df.columns else ""
        # Website presence filter
        if "Website Link" in df.columns:
            website_filter = st.selectbox(
                "Website",
                ["All", "Has Website", "No Website"],
                help="Filter by whether provider has a website link"
            )
        else:
            website_filter = "All"

# ---- SORTING ----
with st.expander("Sorting", expanded=False):
    col_sort_col, col_sort_dir = st.columns([2, 1])
    with col_sort_col:
        sort_col = st.selectbox("Sort by", df.columns.tolist())
    with col_sort_dir:
        sort_dir = st.radio("Order", ["Ascending", "Descending"], horizontal=True)

# ---- APPLY FILTERS ----
filtered_df = df.copy()

# Apply column-specific filters
if name_filter and "Training Provider Name" in filtered_df.columns:
    filtered_df = filtered_df[
        filtered_df["Training Provider Name"].astype(str).str.contains(name_filter, case=False, na=False)
    ]

if addr_filter and "Address" in filtered_df.columns:
    filtered_df = filtered_df[
        filtered_df["Address"].astype(str).str.contains(addr_filter, case=False, na=False)
    ]

if tel_filter and "Telephone No." in filtered_df.columns:
    filtered_df = filtered_df[
        filtered_df["Telephone No."].astype(str).str.contains(tel_filter, case=False, na=False)
    ]

if email_filter and "Email" in filtered_df.columns:
    filtered_df = filtered_df[
        filtered_df["Email"].astype(str).str.contains(email_filter, case=False, na=False)
    ]

# Apply Industry filter
if industry_filter and industry_filter != "All":
    filtered_df = filtered_df[filtered_df["Industry"] == industry_filter]

# Apply Website presence filter
if website_filter != "All":
    if website_filter == "Has Website":
        filtered_df = filtered_df[filtered_df["Website Link"].notna() &
                              (filtered_df["Website Link"].astype(str).str.strip() != "")]
    else:  # No Website
        filtered_df = filtered_df[(filtered_df["Website Link"].isna()) |
                              (filtered_df["Website Link"].astype(str).str.strip() == "")]

# Apply search based on mode
if search_query:
    search_cols = all_columns

    if use_fuzzy:
        # Fuzzy search using RapidFuzz
        threshold = fuzzy_threshold

        # Collect all indices that match any column with fuzzy search
        matching_indices = set()

        for col in search_cols:
            if col in df.columns:
                # Get fuzzy matches for this column
                matches = process.extract(
                    search_query,
                    df[col].fillna("").astype(str).tolist(),
                    limit=None,
                    scorer=fuzz.WRatio,
                    score_cutoff=threshold
                )
                matching_indices.update(idx for idx, score, _ in matches)

        filtered_df = filtered_df.loc[list(matching_indices)]

    elif use_advanced:
        # Advanced boolean search
        words = search_query.split()

        if search_operator == "AND (all words)":
            # All words must be present
            for word in words:
                mask = pd.Series(False, index=filtered_df.index)
                for col in search_cols:
                    mask = mask | filtered_df[col].astype(str).str.contains(word, case=False, na=False)
                filtered_df = filtered_df[mask]
        else:  # OR (any word)
            # At least one word must be present
            mask = pd.Series(False, index=filtered_df.index)
            for word in words:
                word_mask = pd.Series(False, index=filtered_df.index)
                for col in search_cols:
                    word_mask = word_mask | filtered_df[col].astype(str).str.contains(word, case=False, na=False)
                mask = mask | word_mask
            filtered_df = filtered_df[mask]

    else:  # Standard search
        mask = pd.Series(False, index=filtered_df.index)
        for col in search_cols:
            mask = mask | filtered_df[col].astype(str).str.contains(search_query, case=False, na=False)
        filtered_df = filtered_df[mask]

# Apply sorting
filtered_df = filtered_df.sort_values(by=sort_col, ascending=(sort_dir == "Ascending"))

total_rows = len(df)
filtered_rows = len(filtered_df)

if filtered_rows == 0:
    st.warning("No rows match your search/filters.")
    st.caption(f"Filtered from {total_rows} total rows.")
    st.stop()

# ---- RESULTS STATS ----
st.subheader("Results")

# Quick stats
col_stat1, col_stat2, col_stat3 = st.columns(3)
with col_stat1:
    st.metric("Total Providers", total_rows)
with col_stat2:
    st.metric("Filtered Results", filtered_rows)
with col_stat3:
    if "Website Link" in df.columns:
        with_website = filtered_df[filtered_df["Website Link"].notna() &
                                 (filtered_df["Website Link"].astype(str).str.strip() != "")].shape[0]
        st.metric("Has Website", with_website)

# ---- EXPORT BUTTON ----
st.download_button(
    label="📥 Export to CSV",
    data=filtered_df.to_csv(index=False).encode('utf-8'),
    file_name='training_providers.csv',
    mime='text/csv',
)

# ---- PAGINATION SETTINGS ----
st.subheader("Table")

col_page_size, col_page_num, _ = st.columns([1, 1, 4])

with col_page_size:
    page_size = st.selectbox(
        "Rows per page",
        options=[25, 50, 100, 500, 1000],
        index=0,  # default 25
    )

total_pages = math.ceil(filtered_rows / page_size)
if total_pages == 0:
    total_pages = 1

with col_page_num:
    page_number = st.number_input(
        "Page",
        min_value=1,
        max_value=total_pages,
        value=1,
        step=1,
    )

# Slice data for current page
start_idx = (page_number - 1) * page_size
end_idx = start_idx + page_size
page_df = filtered_df.iloc[start_idx:end_idx]

# Show stats
st.caption(
    f"Showing rows {start_idx + 1}–{min(end_idx, filtered_rows)} "
    f"of {filtered_rows} filtered rows (from {total_rows} total rows)."
)

# Display table
st.dataframe(page_df, use_container_width=True)

# -------------- 🐣 EASTER EGG BUTTON (BOTTOM RIGHT) --------------
st.markdown("")  # small spacer

_, _, right_col = st.columns([6, 3, 1])
with right_col:
    if st.button("🎁", key="easter_egg_button", help="Nothing to see here..."):
        st.session_state.show_easter_egg = True
        st.balloons()

# -------------- 🐣 EASTER EGG POPUP --------------
if st.session_state.show_easter_egg:
    with st.container():
        st.markdown("---")
        st.markdown("### 🐣 Secret unlocked!")

        st.image(
            "penguins.webp",
            caption="You found the hidden surprise 🎉",
            use_container_width=True,
        )

        if st.button("Close surprise", key="close_easter_egg"):
            st.session_state.show_easter_egg = False
