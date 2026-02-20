"""
Olist E‑Commerce Financial Intelligence Dashboard
==================================================
Streamlit Live Dashboard
Deploy: streamlit run streamlit_app.py
Or deploy to Streamlit Cloud: https://streamlit.io/cloud

Author: IBRAHEM
Data: Olist Brazilian E‑Commerce Dataset (Kaggle)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Olist Financial Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
    
    .stApp { background-color: #0a0e1a; }
    .main .block-container { padding-top: 2rem; max-width: 1400px; }
    
    h1, h2, h3 { font-family: 'DM Sans', sans-serif !important; color: #f1f5f9 !important; }
    p, span, div { color: #94a3b8; }
    
    [data-testid="stMetricValue"] {
        font-family: 'Space Mono', monospace !important;
        font-size: 28px !important;
        color: #f5a623 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 12px !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        color: #64748b !important;
    }
    [data-testid="stMetricDelta"] { font-family: 'Space Mono', monospace !important; }
    
    div[data-testid="stMetric"] {
        background: #1a2035;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 20px 24px;
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 4px; background: rgba(255,255,255,0.03); border-radius: 10px; padding: 4px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px;
        color: #64748b;
        font-size: 13px;
        padding: 8px 20px;
    }
    .stTabs [aria-selected="true"] { background: #1a2035 !important; color: #f1f5f9 !important; }
    
    .plot-container { background: #1a2035; border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 8px; }
    
    hr { border-color: rgba(255,255,255,0.06) !important; }
    
    .insight-box {
        background: #1a2035;
        border: 1px solid rgba(255,255,255,0.06);
        border-left: 3px solid;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────
@st.cache_data
def load_data():
    """Load datasets from the local data directory. Returns multiple DataFrames."""
    try:
        orders = pd.read_csv("data/olist_orders_dataset.csv")
        items = pd.read_csv("data/olist_order_items_dataset.csv")
        payments = pd.read_csv("data/olist_order_payments_dataset.csv")
        reviews = pd.read_csv("data/olist_order_reviews_dataset.csv")
        customers = pd.read_csv("data/olist_customers_dataset.csv")
        products = pd.read_csv("data/olist_products_dataset.csv")
        sellers = pd.read_csv("data/olist_sellers_dataset.csv")
        translations = pd.read_csv("data/product_category_name_translation.csv")
    except FileNotFoundError:
        st.error("Data files not found. Please ensure the CSV files are in the `data/` folder.")
        return None, None, None, None, None
    
    # Parse dates
    for col in ['order_purchase_timestamp', 'order_approved_at', 'order_delivered_carrier_date',
                'order_delivered_customer_date', 'order_estimated_delivery_date']:
        orders[col] = pd.to_datetime(orders[col], errors='coerce')
    
    # Filter delivered
    delivered = orders[orders['order_status'] == 'delivered'].copy()
    delivered['year_month'] = delivered['order_purchase_timestamp'].dt.to_period('M').astype(str)
    delivered['quarter'] = delivered['order_purchase_timestamp'].dt.to_period('Q').astype(str)
    
    # Enrich items
    items_e = items.merge(products[['product_id', 'product_category_name']], on='product_id', how='left')
    items_e = items_e.merge(translations, on='product_category_name', how='left')
    items_e['category'] = items_e['product_category_name_english'].fillna('other')
    
    # Master table
    master = delivered.merge(items_e, on='order_id', how='inner')
    master = master.merge(customers[['customer_id', 'customer_state']], on='customer_id', how='left')
    master = master[(master['year_month'] >= '2017-01') & (master['year_month'] <= '2018-08')]
    
    # Delivery metrics
    del_data = delivered.dropna(subset=['order_delivered_customer_date', 'order_estimated_delivery_date'])
    del_data['delivery_days'] = (del_data['order_delivered_customer_date'] - del_data['order_purchase_timestamp']).dt.days
    del_data['on_time'] = del_data['order_delivered_customer_date'] <= del_data['order_estimated_delivery_date']
    
    return master, delivered, payments, reviews, del_data

master, delivered, payments, reviews, del_data = load_data()

# Guard if data loading failed
if master is None:
    st.stop()

# ─────────────────────────────────────────────
# PLOTLY THEME
# ─────────────────────────────────────────────
COLORS = {
    'gold': '#f5a623', 'blue': '#4a9eff', 'green': '#34d399',
    'purple': '#a78bfa', 'cyan': '#22d3ee', 'red': '#f87171',
    'bg': '#0a0e1a', 'card': '#1a2035', 'text': '#94a3b8', 'grid': 'rgba(255,255,255,0.04)'
}

LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='DM Sans', color=COLORS['text'], size=11),
    margin=dict(l=40, r=20, t=40, b=40),
    xaxis=dict(gridcolor=COLORS['grid'], showline=False),
    yaxis=dict(gridcolor=COLORS['grid'], showline=False),
    legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=11)),
    hoverlabel=dict(bgcolor=COLORS['card'], bordercolor='rgba(255,255,255,0.1)', font=dict(family='DM Sans', size=12))
)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("# 📊 Olist Financial Intelligence")
    st.markdown("*E‑Commerce Revenue Analytics · Brazilian Marketplace · Jan 2017 — Aug 2018*")
with col_h2:
    st.markdown(
        """
        <div style="text-align:right; padding-top:20px;">
            <span style="background:rgba(52,211,153,0.12); color:#34d399; padding:6px 14px; border-radius:20px; font-size:12px; font-weight:600; border:1px solid rgba(52,211,153,0.2);">● Interactive</span>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

# ─────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────
pay_merged = payments.merge(delivered[['order_id']], on='order_id')
total_rev = pay_merged['payment_value'].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue", f"R$ {total_rev/1e6:.1f}M", "Gross + Freight")
c2.metric("Total Orders", f"{delivered.shape[0]:,}", "Delivered only")
c3.metric("Avg Order Value", f"R$ {total_rev/delivered.shape[0]:.2f}")
c4.metric("Unique Customers", f"{delivered['customer_id'].nunique():,}", f"★ {reviews.merge(delivered[['order_id']])['review_score'].mean():.2f} avg review")

st.markdown("")
c5, c6, c7, c8 = st.columns(4)
c5.metric("Avg Delivery", f"{del_data['delivery_days'].mean():.1f} days")
c6.metric("On‑Time Rate", f"{del_data['on_time'].mean()*100:.1f}%")
c7.metric("Credit Card Share", f"{pay_merged[pay_merged['payment_type']=='credit_card']['payment_value'].sum()/pay_merged['payment_value'].sum()*100:.1f}%")
rev_scores = reviews.merge(delivered[['order_id']])
c8.metric("5‑Star Reviews", f"{(rev_scores['review_score']==5).mean()*100:.1f}%")

st.markdown("---")

# ─────────────────────────────────────────────
# REVENUE TREND
# ─────────────────────────────────────────────
st.markdown("### Monthly Revenue & Order Trend")

monthly = master.groupby('year_month').agg(
    revenue=('price', 'sum'), freight=('freight_value', 'sum'), orders=('order_id', 'nunique')
).reset_index().sort_values('year_month')

tab1, tab2, tab3 = st.tabs(["Combined", "Revenue Only", "Orders Only"])

with tab1:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=monthly['year_month'], y=monthly['revenue'], name='Product Revenue',
                              fill='tozeroy', fillcolor='rgba(245,166,35,0.1)', line=dict(color=COLORS['gold'], width=2)), secondary_y=False)
    fig.add_trace(go.Scatter(x=monthly['year_month'], y=monthly['freight'], name='Freight',
                              fill='tozeroy', fillcolor='rgba(74,158,255,0.06)', line=dict(color=COLORS['blue'], width=1.5)), secondary_y=False)
    fig.add_trace(go.Scatter(x=monthly['year_month'], y=monthly['orders'], name='Orders',
                              line=dict(color=COLORS['purple'], width=2, dash='dash')), secondary_y=True)
    fig.update_layout(**LAYOUT, height=400)
    fig.update_yaxes(title_text="Revenue (R$)", secondary_y=False, gridcolor=COLORS['grid'])
    fig.update_yaxes(title_text="Orders", secondary_y=True, gridcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=monthly['year_month'], y=monthly['revenue'], name='Revenue',
                               fill='tozeroy', fillcolor='rgba(245,166,35,0.15)', line=dict(color=COLORS['gold'], width=2.5)))
    fig2.update_layout(**LAYOUT, height=400)
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=monthly['year_month'], y=monthly['orders'], name='Orders',
                               fill='tozeroy', fillcolor='rgba(167,139,250,0.12)', line=dict(color=COLORS['purple'], width=2.5)))
    fig3.update_layout(**LAYOUT, height=400)
    st.plotly_chart(fig3, use_container_width=True)

# ─────────────────────────────────────────────
# CATEGORY + PAYMENT ROW
# ─────────────────────────────────────────────
col_a, col_b = st.columns([2, 1])

with col_a:
    st.markdown("### Top Revenue Categories")
    cats = master.groupby('category')['price'].sum().sort_values(ascending=True).tail(10)
    fig_cat = go.Figure(go.Bar(
        x=cats.values, y=cats.index, orientation='h',
        marker=dict(color=cats.values, colorscale=[[0, COLORS['blue']], [1, COLORS['gold']]], cornerradius=5)
    ))
    fig_cat.update_layout(**LAYOUT, height=400, showlegend=False)
    st.plotly_chart(fig_cat, use_container_width=True)

with col_b:
    st.markdown("### Payment Methods")
    pay_dist = pay_merged.groupby('payment_type')['payment_value'].sum().sort_values(ascending=False)
    fig_pay = go.Figure(go.Pie(
        labels=pay_dist.index, values=pay_dist.values,
        hole=0.65, marker=dict(colors=[COLORS['gold'], COLORS['blue'], COLORS['purple'], COLORS['cyan']]),
        textinfo='percent+label', textfont=dict(size=11, color='#f1f5f9')
    ))
    fig_pay.update_layout(**LAYOUT, height=400, showlegend=False)
    st.plotly_chart(fig_pay, use_container_width=True)

# ─────────────────────────────────────────────
# QUARTERLY + INSTALLMENTS
# ─────────────────────────────────────────────
col_c, col_d = st.columns(2)

with col_c:
    st.markdown("### Quarterly Revenue Growth")
    quarterly = master.groupby('quarter').agg(revenue=('price', 'sum')).reset_index().sort_values('quarter')
    quarterly = quarterly[quarterly['quarter'] >= '2017Q1']
    quarterly['growth'] = quarterly['revenue'].pct_change() * 100
    
    fig_q = make_subplots(specs=[[{"secondary_y": True}]])
    colors_q = [COLORS['red'] if g < 0 else COLORS['gold'] for g in quarterly['growth'].fillna(0)]
    fig_q.add_trace(go.Bar(x=quarterly['quarter'], y=quarterly['revenue'], name='Revenue',
                            marker=dict(color=colors_q, cornerradius=8)), secondary_y=False)
    fig_q.add_trace(go.Scatter(x=quarterly['quarter'], y=quarterly['growth'], name='QoQ Growth %',
                                line=dict(color=COLORS['cyan'], width=2), mode='lines+markers'), secondary_y=True)
    fig_q.update_layout(**LAYOUT, height=350)
    st.plotly_chart(fig_q, use_container_width=True)

with col_d:
    st.markdown("### Credit Card Installments")
    cc = pay_merged[pay_merged['payment_type'] == 'credit_card']
    inst = cc.groupby('payment_installments').agg(total=('payment_value', 'sum'), count=('order_id', 'count')).reset_index()
    inst = inst[inst['payment_installments'].between(1, 10)]
    
    fig_i = make_subplots(specs=[[{"secondary_y": True}]])
    fig_i.add_trace(go.Bar(x=inst['payment_installments'].astype(str) + 'x', y=inst['total'], name='Total Value',
                            marker=dict(color=COLORS['purple'], cornerradius=5)), secondary_y=False)
    fig_i.add_trace(go.Scatter(x=inst['payment_installments'].astype(str) + 'x', y=inst['count'], name='Count',
                                line=dict(color=COLORS['gold'], width=2), mode='lines+markers'), secondary_y=True)
    fig_i.update_layout(**LAYOUT, height=350)
    st.plotly_chart(fig_i, use_container_width=True)

# ─────────────────────────────────────────────
# STATES + REVIEWS
# ─────────────────────────────────────────────
col_e, col_f = st.columns([2, 1])

with col_e:
    st.markdown("### Revenue by State (Top 10)")
    states = master.groupby('customer_state').agg(
        revenue=('price', 'sum'), orders=('order_id', 'nunique')
    ).reset_index().sort_values('revenue', ascending=False).head(10)
    
    state_names = {'SP':'São Paulo','RJ':'Rio de Janeiro','MG':'Minas Gerais','RS':'R.G. do Sul',
                   'PR':'Paraná','SC':'Santa Catarina','BA':'Bahia','DF':'Distrito Federal','GO':'Goiás','ES':'Espírito Santo'}
    states['name'] = states['customer_state'].map(state_names).fillna(states['customer_state'])
    
    fig_s = go.Figure(go.Bar(
        x=states['revenue'], y=states['name'], orientation='h',
        marker=dict(color=states['revenue'], colorscale=[[0, COLORS['blue']], [1, COLORS['gold']]], cornerradius=5),
        text=[f"R${v/1e6:.1f}M" if v > 1e6 else f"R${v/1e3:.0f}K" for v in states['revenue']],
        textposition='outside', textfont=dict(size=11, color=COLORS['text'])
    ))
    fig_s.update_layout(**LAYOUT, height=380, showlegend=False, yaxis=dict(autorange='reversed', gridcolor='rgba(0,0,0,0)'))
    st.plotly_chart(fig_s, use_container_width=True)

with col_f:
    st.markdown("### Review Distribution")
    rev_dist = reviews.merge(delivered[['order_id']])['review_score'].value_counts().sort_index()
    review_colors = [COLORS['red'], '#fb923c', '#fbbf24', '#a3e635', COLORS['green']]
    
    fig_r = go.Figure(go.Bar(
        x=['1★','2★','3★','4★','5★'], y=rev_dist.values,
        marker=dict(color=review_colors, cornerradius=5),
        text=[f"{v/1e3:.1f}K" for v in rev_dist.values],
        textposition='outside', textfont=dict(size=11, color=COLORS['text'])
    ))
    fig_r.update_layout(**LAYOUT, height=380, showlegend=False)
    st.plotly_chart(fig_r, use_container_width=True)

# ─────────────────────────────────────────────
# INSIGHTS
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 💡 Key Insights")

ci1, ci2, ci3 = st.columns(3)
with ci1:
    st.markdown(
        """
        <div class="insight-box" style="border-left-color:#f5a623;">
            <strong style="color:#f5a623;">Growth Trajectory</strong><br>
            Revenue grew <strong style="color:#f1f5f9;">17.5x</strong> from Q3'16 to Q1'18, peaking at <strong style="color:#f1f5f9;">R$2.7M</strong>. 
            November Black Friday drove a <strong style="color:#f1f5f9;">43.7% QoQ</strong> surge.
        </div>
        """,
        unsafe_allow_html=True
    )
with ci2:
    st.markdown(
        """
        <div class="insight-box" style="border-left-color:#4a9eff;">
            <strong style="color:#4a9eff;">Payment Behavior</strong><br>
            <strong style="color:#f1f5f9;">78.5%</strong> of revenue via credit cards. The 10‑installment plan captures 
            <strong style="color:#f1f5f9;">R$2.1M</strong> — customers prefer longer plans for large purchases.
        </div>
        """,
        unsafe_allow_html=True
    )
with ci3:
    st.markdown(
        """
        <div class="insight-box" style="border-left-color:#34d399;">
            <strong style="color:#34d399;">Geographic Concentration</strong><br>
            São Paulo drives <strong style="color:#f1f5f9;">41.4%</strong> of revenue. Top 3 states = 54.5%. 
            Northern expansion represents a major growth opportunity.
        </div>
        """,
        unsafe_allow_html=True
    )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align:center; padding:20px 0;">
        <p style="font-size:12px; color:#64748b;">
            Data Source: <a href="https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce" style="color:#f5a623;" target="_blank">Olist Brazilian E‑Commerce Dataset (Kaggle)</a><br>
            Built by IBRAHEM · Quality Assurance & Data Analytics · February 2026
        </p>
    </div>
    """,
    unsafe_allow_html=True
)