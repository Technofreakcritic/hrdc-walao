import streamlit as st
import pandas as pd
import math

# 🔹 Easter egg image path
EASTER_EGG_IMAGE_PATH = "penguins.webp"  # change this to your image file

# 🔹 Session state to track if the easter egg is open
if "show_easter_egg" not in st.session_state:
    st.session_state.show_easter_egg = False

st.set_page_config(page_title="Training Providers Search", layout="wide")

st.title("HRDC Training Providers Search Simplified")

st.write(
    "This app reads from a local CSV with these headers: "
    "`Training Provider Name, Address, Telephone No., Email`"
)

# 🔧 Set your CSV file path here
CSV_PATH = "woohoo.csv"  # e.g. "./data/training_providers.csv"

# Optional: allow editing the path from the UI
csv_path = CSV_PATH  # no text_input – just use the constant

# ---- READ CSV ----
try:
    df = pd.read_csv(csv_path)
except FileNotFoundError:
    st.error(f"CSV file not found at: {csv_path}")
    st.stop()
except Exception as e:
    st.error(f"Error reading CSV: {e}")
    st.stop()

# Expected columns
expected_cols = [
    "Training Provider Name",
    "Address",
    "Telephone No.",
    "Email",
]

# Validate columns
missing_cols = [col for col in expected_cols if col not in df.columns]
if missing_cols:
    st.error(
        f"These required columns are missing from the CSV: {', '.join(missing_cols)}"
    )
    st.stop()

# ---- SEARCH + FILTERS ----
st.subheader("Search & Filters")

# Global search
search_query = st.text_input(
    "Global Search (name, address, phone, email):",
    placeholder="Type anything to filter across all columns..."
)

with st.expander("Advanced column filters"):
    col1, col2 = st.columns(2)
    with col1:
        name_filter = st.text_input("Filter by Training Provider Name")
        tel_filter = st.text_input("Filter by Telephone No.")
    with col2:
        addr_filter = st.text_input("Filter by Address")
        email_filter = st.text_input("Filter by Email")

filtered_df = df.copy()

# Apply global search
if search_query:
    mask = (
        df["Training Provider Name"].astype(str).str.contains(search_query, case=False, na=False)
        | df["Address"].astype(str).str.contains(search_query, case=False, na=False)
        | df["Telephone No."].astype(str).str.contains(search_query, case=False, na=False)
        | df["Email"].astype(str).str.contains(search_query, case=False, na=False)
    )
    filtered_df = filtered_df[mask]

# Apply column-specific filters
if name_filter:
    filtered_df = filtered_df[
        filtered_df["Training Provider Name"].astype(str).str.contains(name_filter, case=False, na=False)
    ]

if addr_filter:
    filtered_df = filtered_df[
        filtered_df["Address"].astype(str).str.contains(addr_filter, case=False, na=False)
    ]

if tel_filter:
    filtered_df = filtered_df[
        filtered_df["Telephone No."].astype(str).str.contains(tel_filter, case=False, na=False)
    ]

if email_filter:
    filtered_df = filtered_df[
        filtered_df["Email"].astype(str).str.contains(email_filter, case=False, na=False)
    ]

total_rows = len(df)
filtered_rows = len(filtered_df)

if filtered_rows == 0:
    st.warning("No rows match your search/filters.")
    st.caption(f"Filtered from {total_rows} total rows.")
    st.stop()

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
            EASTER_EGG_IMAGE_PATH,
            caption="You found the hidden surprise 🎉",
            use_container_width=True,
        )

        if st.button("Close surprise", key="close_easter_egg"):
            st.session_state.show_easter_egg = False


