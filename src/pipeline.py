"""
pipeline.py — Project Pantry Audit: Retail Shelf-Health Scoring


Allowed libraries only: requests, json, csv, pathlib, statistics-free native loops.
Forbidden: pandas, numpy, beautifulsoup4 / bs4.

"""

import csv
import json
from os import path
import requests
from pathlib import Path

OFF_SEARCH_URL = "https://world.openfoodfacts.org/api/v2/search"
SUGAR_SCRAPE_URL = "https://www.sugar.org/blog/making-sense-of-added-sugars-on-the-new-nutrition-facts-label/"
WAREHOUSE_LOG_PATH = Path("data/raw/warehouse_scan_log.csv")
EXTRACTED_IDS_PATH = Path("data/raw/extracted_ids.txt")
CLEAN_DATA_PATH = Path("data/processed/clean_data.csv")


# ---------------------------------------------------------------------------
# Phase 1 / Section 3: Acquisition
# ---------------------------------------------------------------------------

def fetch_products(category="breakfast-cereals", page_size=100, user_agent=None):
    """Call the Open Food Facts search endpoint and return the list of product records."""
    params = {
        "categories_tags_en": category,
        "page_size": page_size,
        "fields": "code,product_name,brands,quantity,categories_tags_en,countries_tags,ingredients_text,nutrition_grades,nutriments",
    }
    headers = {
        "User-Agent": user_agent,
    }
    try:
        response = requests.get(OFF_SEARCH_URL, params=params, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        raise
    payload = response.json()
    return payload["products"]


def scrape_daily_value_sugar_g(url=SUGAR_SCRAPE_URL):
    """Fetch the sugar.org page and extract the FDA Daily Value for added sugars (grams)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    text = response.text

    anchor = "the Daily Value is "
    idx = text.find(anchor)
    if idx == -1:
        raise ValueError(f"Could not find anchor phrase '{anchor}' on page")

    after_anchor = text[idx + len(anchor):]
    window = after_anchor[:50]
    print(f"Window after anchor: {window!r}")

    first_token = after_anchor.strip().split()[0]
    daily_value = float(first_token)
    return daily_value


def write_extracted_ids(products, path=EXTRACTED_IDS_PATH):
    """Write one barcode per line to a text file from the products' code field."""
    barcodes = [str(p["code"]) for p in products if p.get("code")]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(barcodes), encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase 2: Data Understanding (native loops only — this part mostly lives in
# notebooks/exploration.ipynb, but a couple of reusable pieces belong here)
# ---------------------------------------------------------------------------

def sugar_min_max_mean(products):
    """Compute min, max, and mean of sugars_100g across products in a single pass."""
    total = 0
    count = 0
    min_val = None
    max_val = None
    n_missing = 0

    for product in products:
        nutriments = product.get("nutriments")
        if not isinstance(nutriments, dict):
            n_missing += 1
            continue
            
        sugar = nutriments.get("sugars_100g")
        if sugar is None:
            n_missing += 1
            continue
            
        try:
            sugar = float(sugar)
        except (ValueError, TypeError):
            n_missing += 1
            continue
            
        total += sugar
        count += 1
        if min_val is None or sugar < min_val:
            min_val = sugar
        if max_val is None or sugar > max_val:
            max_val = sugar

    mean_val = total / count if count else None

    return {
        "min": min_val,
        "max": max_val,
        "mean": mean_val,
        "n_present": count,
        "n_missing": n_missing,
    }


def field_completeness(products, fields):
    """For each field, compute the percentage of products where that nutriment key is present."""
    counts = {field: 0 for field in fields}

    for product in products:
        nutriments = product.get("nutriments", {})  
        for field in fields:
            if field in nutriments:
                counts[field] += 1

    total = len(products)
    return {field: (counts[field] / total) * 100 for field in fields}


def ingredients_text_state_counts(products):
    """Count products with missing ingredients_text key vs empty string vs real text."""
    missing_key = 0
    empty_string = 0
    has_text = 0

    for product in products:
        if "ingredients_text" not in product:
            missing_key += 1
        elif product.get("ingredients_text") == "":
            empty_string += 1
        else:
            has_text += 1

    return {
        "missing_key": missing_key,
        "empty_string": empty_string,
        "has_text": has_text,
    }

# ---------------------------------------------------------------------------
# Phase 3: Data Preparation
# ---------------------------------------------------------------------------

def parse_quantity_grams(raw):
    """Parse the leading numeric value out of a free-text quantity string like '70 g'."""
    if not raw:
        return None

    digits = ""
    for ch in raw:
        if ch.isdigit() or (ch == "." and "." not in digits):
            digits += ch
        elif digits:
            break

    if not digits:
        return None

    try:
        return float(digits)
    except ValueError:
        return None

def load_warehouse_log(path=WAREHOUSE_LOG_PATH):
    """Load the warehouse scan log CSV into a dict keyed by barcode."""
    log = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            log[row["barcode"]] = row
    return log


def clean_and_engineer(products, daily_value_sugar_g, warehouse_log):
    """Filter, impute, engineer features, and join warehouse data for each product."""
    cohort = [p for p in products if p.get("nutriments", {}).get("sugars_100g") is not None]

    fiber_total, fiber_count = 0, 0
    protein_total, protein_count = 0, 0
    for p in cohort:
        nutriments = p.get("nutriments", {})
        fiber = nutriments.get("fiber_100g")
        if fiber is not None:
            fiber_total += fiber
            fiber_count += 1
        protein = nutriments.get("proteins_100g")
        if protein is not None:
            protein_total += protein
            protein_count += 1

    fiber_mean = fiber_total / fiber_count if fiber_count else 0
    protein_mean = protein_total / protein_count if protein_count else 0

    clean_records = []
    for p in cohort:
        nutriments = p.get("nutriments", {})
        sugar = nutriments.get("sugars_100g")

        fiber = nutriments.get("fiber_100g")
        if fiber is None:
            fiber = fiber_mean

        proteins = nutriments.get("proteins_100g")
        if proteins is None:
            proteins = protein_mean

        quantity_grams = parse_quantity_grams(p.get("quantity"))

        sugar_pct_dv = (sugar / daily_value_sugar_g) * 100
        if sugar_pct_dv < 5:
            sugar_tier = "low"
        elif sugar_pct_dv < 20:
            sugar_tier = "moderate"
        else:
            sugar_tier = "high"

        high_sugar_flag = 1 if (sugar / 50.0) >= 0.20 else 0

        barcode = str(p.get("code", ""))
        log_row = warehouse_log.get(barcode, {})

        record = {
            "barcode": barcode,
            "product_name": p.get("product_name"),
            "brands": p.get("brands"),
            "sugars_100g": sugar,
            "fiber_100g": fiber,
            "proteins_100g": proteins,
            "quantity_grams": quantity_grams,
            "sugar_pct_dv": sugar_pct_dv,
            "sugar_tier": sugar_tier,
            "high_sugar_flag": high_sugar_flag,
            "nutrition_grades": p.get("nutrition_grades"),
            "shelf_location": log_row.get("shelf_location"),
            "units_sold_last_month": log_row.get("units_sold_last_month"),
        }
        clean_records.append(record)

    return clean_records


def min_max_scale(records, field, new_field):
    """Add a min-max scaled version of a field to every record."""
    values = [r[field] for r in records]
    min_x, max_x = min(values), max(values)
    for r in records:
        r[new_field] = (r[field] - min_x) / (max_x - min_x)
    return records


def grade_flag_rate_table(records):
    """Compute the percentage of high_sugar_flag==1 products for each nutrition grade."""
    totals = {}
    flagged = {}
    for r in records:
        grade = r.get("nutrition_grades") or "missing"
        totals[grade] = totals.get(grade, 0) + 1
        if r["high_sugar_flag"] == 1:
            flagged[grade] = flagged.get(grade, 0) + 1
    return {g: (flagged.get(g, 0) / totals[g]) * 100 for g in totals}


def write_clean_data(records, path=CLEAN_DATA_PATH):
    """Write the final cleaned, engineered records to a CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_pipeline(user_agent):
    """Run the full pipeline end-to-end: fetch, clean, engineer, and write results."""
    products = fetch_products(user_agent=user_agent)

    write_extracted_ids(products)

    # NOTE: at this point you must run, from the terminal:
    #   python generate_pantry_log.py --input-ids data/raw/extracted_ids.txt
    # before continuing, since the warehouse log depends on extracted_ids.txt.
    # (You've already done this once manually — for a true one-command
    # end-to-end run you'd import generate_pantry_log and call it here too.)

    daily_value_sugar_g = scrape_daily_value_sugar_g()
    warehouse_log = load_warehouse_log()

    eda_min_max_mean = sugar_min_max_mean(products)
    eda_completeness = field_completeness(
        products,
        ["sugars_100g", "fat_100g", "fiber_100g", "salt_100g", "proteins_100g", "energy-kcal_100g"],
    )
    eda_ingredients_state = ingredients_text_state_counts(products)

    print("Sugar min/max/mean:", eda_min_max_mean)
    print("Field completeness:", eda_completeness)
    print("Ingredients text state:", eda_ingredients_state)

    records = clean_and_engineer(products, daily_value_sugar_g, warehouse_log)
    records = min_max_scale(records, "sugar_pct_dv", "sugar_pct_dv_scaled")

    grade_table = grade_flag_rate_table(records)
    print("Grade -> flag rate:", grade_table)

    n_total = len(records)
    n_flagged = sum(1 for r in records if r["high_sugar_flag"] == 1)
    pct_workload_reduction = (1 - (n_flagged / n_total)) * 100
    print(f"n_total={n_total}, n_flagged={n_flagged}, pct_workload_reduction={pct_workload_reduction:.1f}%")

    write_clean_data(records)
    print(f"Wrote {n_total} records to {CLEAN_DATA_PATH}")

if __name__ == "__main__":
   
    run_pipeline(user_agent="depi-5-KevinRaafat/1.0 (kevinraafat00@gmail.com)")