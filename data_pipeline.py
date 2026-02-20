"""
Olist E‑Commerce Financial Dashboard — Data Cleaning & Analysis Pipeline
======================================================================
Author: IBRAHEM
Date: February 2026
Data Source: Olist Brazilian E‑Commerce Dataset (Kaggle)
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

This script performs:
1. Data loading & validation
2. Cleaning & transformation
3. Financial KPI computation
4. Aggregation for dashboard visualisations
5. JSON export for the interactive dashboard
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

# ─────────────────────────────────────────────
# 1. DATA LOADING
# ─────────────────────────────────────────────
DATA_DIR = "data/"

print("=" * 60)
print("OLIST FINANCIAL DASHBOARD — ETL PIPELINE")
print("=" * 60)
print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

orders = pd.read_csv(f"{DATA_DIR}olist_orders_dataset.csv")
items = pd.read_csv(f"{DATA_DIR}olist_order_items_dataset.csv")
payments = pd.read_csv(f"{DATA_DIR}olist_order_payments_dataset.csv")
reviews = pd.read_csv(f"{DATA_DIR}olist_order_reviews_dataset.csv")
customers = pd.read_csv(f"{DATA_DIR}olist_customers_dataset.csv")
products = pd.read_csv(f"{DATA_DIR}olist_products_dataset.csv")
sellers = pd.read_csv(f"{DATA_DIR}olist_sellers_dataset.csv")
translations = pd.read_csv(f"{DATA_DIR}product_category_name_translation.csv")

print("📂 Datasets loaded:")
for name, df in [("Orders", orders), ("Items", items), ("Payments", payments),
                  ("Reviews", reviews), ("Customers", customers),
                  ("Products", products), ("Sellers", sellers)]:
    print(f"   {name}: {df.shape[0]:,} rows × {df.shape[1]} cols")

# ─────────────────────────────────────────────
# 2. DATA CLEANING & TRANSFORMATION
# ─────────────────────────────────────────────
print("\n🔧 Cleaning & Transforming...")

# Parse date columns
date_cols = ['order_purchase_timestamp', 'order_approved_at',
             'order_delivered_carrier_date', 'order_delivered_customer_date',
             'order_estimated_delivery_date']
for col in date_cols:
    orders[col] = pd.to_datetime(orders[col], errors='coerce')

# Filter to delivered orders only (financial analysis)
delivered = orders[orders['order_status'] == 'delivered'].copy()
print(f"   Filtered to delivered orders: {delivered.shape[0]:,} / {orders.shape[0]:,}")

# Add time dimensions
delivered['year_month'] = delivered['order_purchase_timestamp'].dt.to_period('M').astype(str)
delivered['quarter'] = delivered['order_purchase_timestamp'].dt.to_period('Q').astype(str)
delivered['year'] = delivered['order_purchase_timestamp'].dt.year

# Merge items with product categories (English translation)
items_enriched = (
    items
    .merge(products[['product_id', 'product_category_name']], on='product_id', how='left')
    .merge(translations, on='product_category_name', how='left')
)
items_enriched['product_category_name_english'].fillna('other', inplace=True)

# Aggregate payments per order
order_payments = payments.groupby('order_id').agg(
    payment_value=('payment_value', 'sum'),
    payment_type=('payment_type', 'first'),
    max_installments=('payment_installments', 'max')
).reset_index()

# Build master financial table
master = (
    delivered
    .merge(items_enriched, on='order_id', how='inner')
    .merge(order_payments, on='order_id', how='left')
    .merge(customers[['customer_id', 'customer_state', 'customer_city']], on='customer_id', how='left')
    .merge(sellers[['seller_id', 'seller_state', 'seller_city']], on='seller_id', how='left')
)

# Clean analysis window (exclude incomplete months)
master = master[
    (master['year_month'] >= '2017-01') &
    (master['year_month'] <= '2018-08')
]
print(f"   Master table: {master.shape[0]:,} rows × {master.shape[1]} cols")
print(f"   Date range: {master['year_month'].min()} to {master['year_month'].max()}")

# ─────────────────────────────────────────────
# 3. KPI COMPUTATION
# ─────────────────────────────────────────────
print("\n📊 Computing Financial KPIs...")

# Revenue KPIs
total_revenue = payments.merge(delivered[['order_id']], on='order_id')['payment_value'].sum()
total_orders = delivered.shape[0]
avg_order_value = total_revenue / total_orders if total_orders else 0
total_customers = delivered['customer_id'].nunique()
total_sellers = master['seller_id'].nunique()

# Review KPIs
review_data = reviews.merge(delivered[['order_id']], on='order_id')
avg_review = review_data['review_score'].mean() if not review_data.empty else 0
five_star_pct = (review_data['review_score'] == 5).mean() * 100 if not review_data.empty else 0

# Delivery KPIs
del_data = delivered.dropna(subset=['order_delivered_customer_date', 'order_estimated_delivery_date'])
del_data['delivery_days'] = (del_data['order_delivered_customer_date'] - del_data['order_purchase_timestamp']).dt.days
del_data['on_time'] = del_data['order_delivered_customer_date'] <= del_data['order_estimated_delivery_date']
on_time_pct = del_data['on_time'].mean() * 100 if not del_data.empty else 0
avg_delivery_days = del_data['delivery_days'].mean() if not del_data.empty else 0

# Payment KPIs
pay_merged = payments.merge(delivered[['order_id']], on='order_id')
credit_card_share = pay_merged[pay_merged['payment_type'] == 'credit_card']['payment_value'].sum() / pay_merged['payment_value'].sum() * 100 if not pay_merged.empty else 0

kpis = {
    'total_revenue': round(total_revenue, 2),
    'total_orders': int(total_orders),
    'avg_order_value': round(avg_order_value, 2),
    'total_customers': int(total_customers),
    'total_sellers': int(total_sellers),
    'avg_review_score': round(avg_review, 2),
    'five_star_pct': round(five_star_pct, 1),
    'on_time_pct': round(on_time_pct, 1),
    'avg_delivery_days': round(avg_delivery_days, 1),
    'credit_card_share': round(credit_card_share, 1)
}

print("   ┌──────────────────────────────────────┐")
for k, v in kpis.items():
    label = k.replace('_', ' ').title()
    print(f"   │ {label:<30} {str(v):>6} │")
print("   └──────────────────────────────────────┘")

# ─────────────────────────────────────────────
# 4. AGGREGATIONS FOR DASHBOARD
# ─────────────────────────────────────────────
print("\n📈 Building Dashboard Aggregations...")

# Monthly revenue trend
monthly = master.groupby('year_month').agg(
    revenue=('price', 'sum'),
    freight=('freight_value', 'sum'),
    orders=('order_id', 'nunique')
).reset_index().sort_values('year_month')
monthly['total'] = monthly['revenue'] + monthly['freight']

# Top categories by revenue
categories = master.groupby('product_category_name_english').agg(
    revenue=('price', 'sum'),
    orders=('order_id', 'nunique'),
    avg_price=('price', 'mean')
).reset_index().sort_values('revenue', ascending=False).head(15)

# Payment type distribution
payment_dist = pay_merged.groupby('payment_type').agg(
    total_value=('payment_value', 'sum'),
    order_count=('order_id', 'nunique')
).reset_index().sort_values('total_value', ascending=False)

# Instalments analysis
installments = (
    pay_merged[pay_merged['payment_type'] == 'credit_card']
    .groupby('payment_installments')
    .agg(count=('order_id', 'count'), total=('payment_value', 'sum'))
    .reset_index()
    .sort_values('payment_installments')
    .head(12)
)

# Revenue by state
states = master.groupby('customer_state').agg(
    revenue=('price', 'sum'),
    orders=('order_id', 'nunique'),
    customers=('customer_id', 'nunique')
).reset_index().sort_values('revenue', ascending=False)

# Quarterly growth
quarterly = master.groupby('quarter').agg(
    revenue=('price', 'sum'),
    orders=('order_id', 'nunique')
).reset_index().sort_values('quarter')
quarterly['growth_pct'] = (quarterly['revenue'].pct_change() * 100).round(1)

# Review score distribution
review_dist = review_data['review_score'].value_counts().sort_index().to_dict()

# Category monthly trend (top 5)
top5_cats = categories.head(5)['product_category_name_english'].tolist()
cat_monthly = (
    master[master['product_category_name_english'].isin(top5_cats)]
    .groupby(['year_month', 'product_category_name_english'])
    .agg(revenue=('price', 'sum'))
    .reset_index()
    .sort_values('year_month')
)

# Delivery metrics monthly
del_monthly = (
    del_data
    .groupby(del_data['order_purchase_timestamp'].dt.to_period('M').astype(str))
    .agg(avg_days=('delivery_days', 'mean'), on_time_rate=('on_time', 'mean'))
    .reset_index()
)
del_monthly.columns = ['year_month', 'avg_days', 'on_time_rate']
del_monthly['on_time_rate'] = (del_monthly['on_time_rate'] * 100).round(1)
del_monthly = del_monthly[
    (del_monthly['year_month'] >= '2017-01') &
    (del_monthly['year_month'] <= '2018-08')
]

# ─────────────────────────────────────────────
# 5. EXPORT TO JSON
# ─────────────────────────────────────────────
print("\n💾 Exporting dashboard data...")

dashboard_json = {
    'kpis': kpis,
    'monthly_revenue': monthly.round(2).to_dict('records'),
    'top_categories': categories.round(2).to_dict('records'),
    'payment_types': payment_dist.round(2).to_dict('records'),
    'installments': installments.round(2).to_dict('records'),
    'states': states.round(2).to_dict('records'),
    'quarterly': quarterly.round(2).to_dict('records'),
    'review_distribution': {str(k): int(v) for k, v in review_dist.items()},
    'category_monthly': cat_monthly.round(2).to_dict('records'),
    'delivery_monthly': del_monthly.round(1).to_dict('records'),
    'metadata': {
        'generated_at': datetime.now().isoformat(),
        'source': 'Olist Brazilian E‑Commerce Dataset (Kaggle)',
        'date_range': f"{master['year_month'].min()} to {master['year_month'].max()}",
        'total_records_analyzed': int(master.shape[0])
    }
}

os.makedirs('output', exist_ok=True)
with open('output/dashboard_data.json', 'w') as f:
    json.dump(dashboard_json, f, indent=2)

print(f"   ✅ Exported to output/dashboard_data.json")
print(f"\n{'=' * 60}")
print("PIPELINE COMPLETE")
print(f"{'=' * 60}")