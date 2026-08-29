# Project Pantry Audit — Retail Shelf-Health Scoring

## 1. Objectives

This project builds an automated data pipeline to evaluate retail shelf health and support proactive product reformulation. By integrating warehouse inventory logs with external nutritional data, the system flags high-sugar items to help retailers curate a "healthy aisle" and prioritize products for nutritional review.

## 2. Resource Audit

| Resource | Detail |
|---|---|
| API access | Open Food Facts Product API (`world.openfoodfacts.org`) |
| Rate limit | Standard public API rate limits with polite request headers |
| Data sources | Open Food Facts API call, generated warehouse inventory log, web scrape from sugar.org |
| Estimated time | ~2 minutes for full pipeline execution and file generation |

## 3. Target Definition

```python
high_sugar_flag = 1 if (sugars_100g / 50.0) >= 0.20 else 0

```

The denominator `50.0` is dynamically derived from the scraped Daily Value for sugar obtained directly from sugar.org during the pipeline execution.

## 4. Brainstormed Features (6+)

1. `sugars_100g` — Total sugar content per 100 grams of the product.
2. `sugar_pct_dv` — Percentage of the daily value contributed by sugars per 100g.
3. `sugar_tier` — Categorical classification of the product based on sugar levels.
4. `energy-kcal_100g` — Caloric content per 100g from product nutriments.
5. `proteins_100g` — Protein content per 100g.
6. `fat_100g` — Total fat content per 100g.

## 5. ROI Framework

> Of the 100 SKUs pulled in this category, 64% are `high_sugar_flag == 1` — that's
> the number of products a reformulation team would need to review before this
> category could carry a "healthy aisle" label, versus reviewing the full
> catalog. `pct_workload_reduction = (1 - (n_flagged / n_total)) * 100` = **36.0%**

## 6. Validation Check Interpretation

The cross-tabulation of Open Food Facts nutrition grades against our independently computed `high_sugar_flag` shows that while Grade A has the lowest flag rate and E/unknown have the highest, the middle grades (B, C, D) do not follow a perfectly linear order (with C reaching 92.1% and D at 71.4%). This variation occurs because Open Food Facts' nutrition grade incorporates multiple factors like salt, saturated fat, and fiber alongside sugar, meaning a single-nutrient rule will not track its composite score in a completely linear sequence.

## 7. Source Reliability Note

Sourcing federal nutritional benchmarks from an industry advocacy platform like sugar.org provided a practical standard value, though it required debugging a 403 Forbidden error by adding a browser User-Agent header during the web scraping process. Official public health databases remain the preferred baseline for formal compliance.
 

Note: the OFF Search API v2 endpoint experienced intermittent 503s and one DNS resolution failure during development (a known issue with their legacy search backend, currently being migrated). Product data was cached locally to data/raw/products_cache.json after a successful pull to keep development reproducible.