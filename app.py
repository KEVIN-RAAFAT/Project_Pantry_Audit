import pandas as pd
import streamlit as st

st.set_page_config(page_title="Pantry Audit Dashboard", layout="wide")

st.title("Warehouse Pantry Audit Dashboard")
st.write("Welcome to the data analysis and inventory pipeline dashboard.")

@st.cache_data
def load_data():
    return pd.read_csv("data/processed/cleaned_warehouse_scan.csv")

df = load_data()

st.subheader("Cleaned Warehouse Data Overview")
st.dataframe(df, width="stretch")

st.sidebar.header("Filter Options")
selected_shelf = st.sidebar.selectbox("Select Shelf Location", options=["All"] + list(df["shelf_location"].unique()))

if selected_shelf != "All":
    filtered_df = df[df["shelf_location"] == selected_shelf]
else:
    filtered_df = df

st.subheader("Filtered Data Results")
st.dataframe(filtered_df, width="stretch")