# Warehouse Pantry Audit & Data Pipeline

A complete end-to-end data analysis and interactive dashboard project built to process, clean, and visualize warehouse inventory scan logs.

## Project Structure

* **`src/`**: Contains core Python scripts for data generation and cleaning pipelines.
* **`data/`**: Stores raw inventory logs and processed CSV datasets.
* **`app.py`**: The interactive Streamlit web dashboard script.

## Features

* **Data Cleaning Pipeline**: Automatically processes raw inventory scans, handles missing values, and standardizes formats.
* **Interactive Dashboard**: Built with Streamlit to provide real-time filtering by shelf location and data overview tables.
* **Local Caching**: Uses `@st.cache_data` for optimized performance and faster data loading.

## Installation & Running

1. Clone the repository and navigate to the project directory.
2. Install the required dependencies:
 3. Run the Streamlit dashboard app:
    ```bash
    streamlit run app.py