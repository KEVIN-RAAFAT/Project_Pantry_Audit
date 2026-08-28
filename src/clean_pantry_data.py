import pandas as pd


def clean_warehouse_data(input_path, output_path):
    df = pd.read_csv(input_path)
    print(f"Original shape: {df.shape}")

    df.columns = df.columns.str.strip()

    df['barcode'] = df['barcode'].astype(str).str.strip()

    df['shelf_location'] = df['shelf_location'].astype(str).str.strip()
    df['shelf_location'] = df['shelf_location'].replace({
        'nan': 'Unknown',
        'None': 'Unknown'
    })

    def clean_units(val):
        if pd.isna(val) or str(val).lower() in ['null', 'none', '']:
            return 0
        val_str = str(val).replace(',', '').strip()
        try:
            return int(float(val_str))
        except ValueError:
            return 0

    df['units_sold_last_month'] = df['units_sold_last_month'].apply(clean_units)

    df = df.drop_duplicates()

    df.to_csv(output_path, index=False)
    print(f"Cleaned data saved to {output_path}. Final shape: {df.shape}")
    print(df.head(10))


if __name__ == '__main__':
    INPUT_FILE = 'data/raw/warehouse_scan_log.csv'
    OUTPUT_FILE = 'data/processed/cleaned_warehouse_scan.csv'
    clean_warehouse_data(INPUT_FILE, OUTPUT_FILE)