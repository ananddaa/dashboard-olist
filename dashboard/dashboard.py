import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit import config as _cfg

# tema terang walau OS/browser dark mode 
for _k, _v in {"theme.base": "light", "theme.backgroundColor": "#F3F4F6",
               "theme.secondaryBackgroundColor": "#FFFFFF", "theme.textColor": "#111111",
               "theme.primaryColor": "#111111"}.items():
    try:
        _cfg.set_option(_k, _v)
    except Exception:
        pass

HIGHLIGHT = "#6C4BD6"   # warna utama
GREY = "#D9DBE3"        # warna pembanding
GRID = "rgba(128,128,128,0.15)"
BLUE = "#3B6FD4"       # warna sekunder
PLOT_CONFIG = {"displayModeBar": False}

st.set_page_config(page_title="Olist E-Commerce Dashboard", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_text(filename):
    with open(os.path.join(BASE_DIR, filename), encoding="utf-8") as fh:
        return fh.read()


st.markdown(f"<style>{load_text('style.css')}</style>", unsafe_allow_html=True)


@st.cache_data
def load_data():
    path = os.path.join(BASE_DIR, "main_data.csv")
    df = pd.read_csv(path, parse_dates=["order_purchase_timestamp"])
    df["order_month"] = df["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    df["is_late"] = df["is_late"].astype(bool)
    return df


# HELPER GRAFIK
def style_fig(fig, height=360, grid="y"):
    fig.update_layout(
        height=height,
        margin=dict(l=16, r=6, t=48, b=27),
        title=dict(font=dict(size=15), x=0, xanchor="left"),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font_size=13),
        font=dict(family="Figtree, -apple-system, Segoe UI, sans-serif", color="#333"),
        bargap=0.3,
    )
    fig.update_xaxes(title=None, showgrid=(grid == "x"), gridcolor=GRID, zeroline=False, showline=False,
                     linecolor="rgba(128,128,128,0.4)", automargin=True, tickfont=dict(color="#555"))
    fig.update_yaxes(title=None, showgrid=(grid == "y"), gridcolor=GRID, zeroline=False, automargin=True,
                     tickfont=dict(color="#555"))
    return fig


def line_chart(df, y, title, hover_label, prefix="", peak_label=""):
    fig = go.Figure(go.Scatter(
        x=df["order_month"], y=df[y], mode="lines+markers",
        line=dict(color=HIGHLIGHT, width=2.5),
        marker=dict(size=7, color=HIGHLIGHT, line=dict(color="white", width=1.5)),
        hovertemplate="<b>%{x|%b %Y}</b><br>" + hover_label + ": " + prefix + "%{y:,.0f}<extra></extra>",
    ))
    i = df[y].idxmax()
    fig.add_annotation(x=df.loc[i, "order_month"], y=df.loc[i, y], text=peak_label, showarrow=True,
                       arrowhead=0, arrowcolor="rgba(128,128,128,0.6)", ax=-55, ay=-28, font=dict(size=12))
    fig.update_yaxes(rangemode="tozero")
    fig.update_xaxes(tickformat="%b %Y")
    return style_fig(fig, height=340, grid="y").update_layout(title_text=title)


def hbar(df, x, y, colors, title, text_fmt, customdata=None, hover=None, height=None, x_pad=1.05):
    fig = go.Figure(go.Bar(
        x=df[x], y=df[y], orientation="h", marker_color=colors,
        text=df[x], texttemplate=text_fmt, textposition="outside", cliponaxis=False,
        customdata=customdata, hovertemplate=hover,
    ))
    fig.update_xaxes(range=[0, df[x].max() * x_pad], showticklabels=False, showline=False)
    fig = style_fig(fig, height=height or max(320, 34 * len(df) + 70), grid="none")
    # jarak antara label sumbu Y dan batang
    fig.update_yaxes(ticks="outside", ticklen=10, tickcolor="rgba(0,0,0,0)")
    fig.update_layout(margin=dict(l=16, r=6, t=48, b=7))
    return fig.update_layout(title_text=title)


def card_chart(container, fig):
    with container.container(border=True):
        st.plotly_chart(fig, config=PLOT_CONFIG, theme=None)


def show_table(df, fmt=None, max_height=420):
    """Tabel HTML biasa (putih), tidak ikut tema dark Streamlit."""
    d = df.copy()
    for col, f in (fmt or {}).items():
        d[col] = d[col].map(lambda v, f=f: "-" if pd.isna(v) else f.format(v))
    html = d.to_html(index=False, classes="tbl", border=0, escape=True)
    st.markdown(f'<div class="tbl-wrap" style="max-height:{max_height}px">{html}</div>', unsafe_allow_html=True)


df = load_data()

# SIDEBAR
st.sidebar.markdown(load_text("index.html"), unsafe_allow_html=True)
months = sorted(df["order_month"].unique())
month_labels = [pd.Timestamp(m).strftime("%b %Y") for m in months]
start_label, end_label = st.sidebar.select_slider(
    "Periode (bulan pembelian)", options=month_labels, value=(month_labels[0], month_labels[-1])
)
start_m = months[month_labels.index(start_label)]
end_m = months[month_labels.index(end_label)]

regions = sorted(df["region"].dropna().unique())
# Filter kosong = "Semua" (tidak ada pilihan berarti seluruh data dipakai)
picked_regions = st.sidebar.multiselect("Wilayah", regions, placeholder="Semua")
sel_regions = picked_regions or regions
state_options = sorted(df.loc[df["region"].isin(sel_regions), "customer_state"].unique())
picked_states = st.sidebar.multiselect("State", state_options, placeholder="Semua")
sel_states = picked_states or state_options

f = df[(df["order_month"] >= start_m) & (df["order_month"] <= end_m) & (df["customer_state"].isin(sel_states))]

# HEADER
st.title("Olist E-Commerce Dashboard")

if f.empty:
    st.warning("Tidak ada data untuk filter yang dipilih.")
    st.stop()

orders_f = f.drop_duplicates("order_id")

# KPI
kpi = st.container(key="kpi")
c1, c2, c3, c4, c5 = kpi.columns(5)
c1.metric("Total Pesanan", f"{orders_f['order_id'].nunique():,}")
c2.metric("Total Revenue", f"R$ {f['price'].sum() / 1e6:,.2f} jt")
c3.metric("Jumlah Pelanggan", f"{f['customer_unique_id'].nunique():,}")
c4.metric("Pesanan Terlambat", f"{orders_f['is_late'].mean() * 100:.1f}%")
c5.metric("Rata-rata Review", f"{orders_f['review_score'].mean():.2f} / 5")

st.write("")
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Tren Penjualan", "Kategori Produk", "Pengiriman & Review", "Segmentasi RFM", "Geospasial"]
)

# TAB 1
with tab1:
    st.subheader("Bagaimana tren pesanan dan revenue bulanan?")
    monthly = (f.groupby("order_month")
                 .agg(order_count=("order_id", "nunique"), revenue=("price", "sum")).reset_index())
    monthly["revenue_mom_pct"] = monthly["revenue"].pct_change() * 100
    pk = monthly.loc[monthly["revenue"].idxmax()]
    pk_o = monthly.loc[monthly["order_count"].idxmax()]

    left, right = st.columns(2)
    card_chart(left, line_chart(monthly, "order_count", "Jumlah Pesanan per Bulan", "Pesanan",
                                peak_label=f"Puncak: {int(pk_o['order_count']):,}"))
    card_chart(right, line_chart(monthly, "revenue", "Total Revenue per Bulan (R$)", "Revenue", prefix="R$ ",
                                 peak_label=f"Puncak: R$ {pk['revenue'] / 1e3:,.0f} rb"))

    mom = monthly.dropna(subset=["revenue_mom_pct"])
    if len(mom) > 0:
        fig = go.Figure(go.Bar(
            x=mom["order_month"], y=mom["revenue_mom_pct"],
            marker_color=[HIGHLIGHT if v >= 0 else GREY for v in mom["revenue_mom_pct"]],
            hovertemplate="<b>%{x|%b %Y}</b><br>Revenue MoM: %{y:+.1f}%<extra></extra>",
        ))
        fig.add_hline(y=0, line_color="rgba(128,128,128,0.5)", line_width=1)
        up, dn = mom.loc[mom["revenue_mom_pct"].idxmax()], mom.loc[mom["revenue_mom_pct"].idxmin()]
        fig.add_annotation(x=up["order_month"], y=up["revenue_mom_pct"], text=f"{up['revenue_mom_pct']:+.1f}%",
                           showarrow=False, yshift=12, font=dict(size=12))
        if dn["order_month"] != up["order_month"]:
            fig.add_annotation(x=dn["order_month"], y=dn["revenue_mom_pct"], text=f"{dn['revenue_mom_pct']:+.1f}%",
                               showarrow=False, yshift=-12, font=dict(size=12))
        fig.update_xaxes(tickformat="%b %Y")
        fig = style_fig(fig, height=300, grid="y").update_layout(
            title_text="Perubahan Revenue Bulanan (Month-over-Month, %)")
        card_chart(st, fig)

    bulan_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
                "September", "Oktober", "November", "Desember"]
    pk_bulan = f"{bulan_id[pk['order_month'].month - 1]} {pk['order_month'].year}"
    st.info(f"Revenue bulanan tertinggi pada periode terpilih: **{pk_bulan}** "
            f"(R\\$ {pk['revenue']:,.0f}, yang berasal dari {int(pk['order_count']):,} pesanan). "
            "Pada data, puncak terjadi di November 2017 dengan hari tertinggi 24 November 2017 (bertepatan dengan Black Friday).")
    with st.expander("Lihat tabel bulanan"):
        tbl = monthly.assign(order_month=monthly["order_month"].dt.strftime("%b %Y"))
        show_table(tbl.rename(columns={"order_month": "Bulan", "order_count": "Pesanan", "revenue": "Revenue (R$)",
                                       "revenue_mom_pct": "Revenue MoM (%)"}),
                   {"Pesanan": "{:,.0f}", "Revenue (R$)": "{:,.0f}", "Revenue MoM (%)": "{:.1f}"})

# TAB 2
with tab2:
    st.subheader("Kategori produk apa yang menyumbang revenue terbesar dan terkecil?")
    cat = (f.groupby("product_category").agg(revenue=("price", "sum"), items=("price", "count"))
             .sort_values("revenue", ascending=False).reset_index())
    cat["share"] = cat["revenue"] / cat["revenue"].sum() * 100
    cat["revenue_k"] = cat["revenue"] / 1e3
    n = st.slider("Jumlah kategori yang ditampilkan", 5, 20, 10)

    hover = "<b>%{y}</b><br>Revenue: R$ %{customdata[0]:,.0f}<br>Kontribusi: %{customdata[1]:.2f}%<br>Item terjual: %{customdata[2]:,}<extra></extra>"
    left, right = st.columns(2)
    top = cat.head(n).iloc[::-1]
    card_chart(left, hbar(top, "revenue_k", "product_category", [GREY] * (len(top) - 1) + [HIGHLIGHT],
                          f"{n} Kategori Revenue Terbesar (R$ ribu)", "%{x:,.0f}",
                          customdata=top[["revenue", "share", "items"]].to_numpy(), hover=hover))
    bottom = cat.tail(n).sort_values("revenue", ascending=False)
    card_chart(right, hbar(bottom, "revenue_k", "product_category", [GREY] * (len(bottom) - 1) + [HIGHLIGHT],
                           f"{n} Kategori Revenue Terkecil (R$ ribu)", "%{x:,.1f}",
                           customdata=bottom[["revenue", "share", "items"]].to_numpy(), hover=hover))
    st.info(f"{n} kategori teratas menyumbang **{cat.head(n)['share'].sum():.1f}%** dari revenue pada filter ini.")

# TAB 3
with tab3:
    st.subheader("Seberapa besar keterlambatan pengiriman dan dampaknya ke review?")
    st_df = (orders_f.groupby("customer_state")
                     .agg(orders=("order_id", "count"), late_pct=("is_late", lambda s: s.mean() * 100),
                          avg_review=("review_score", "mean")).reset_index().sort_values("late_pct"))
    overall = orders_f["is_late"].mean() * 100
    left = right = st  # dua grafik disusun atas-bawah

    max_n = len(st_df)
    with st.container(border=True):
        st.markdown('<div style="font-size:15px;color:#333;padding:8px 0 0">Pesanan Terlambat per State (%)</div>',
                    unsafe_allow_html=True)
        if max_n > 5:
            n_state = st.slider("Jumlah state yang ditampilkan", 5, max_n, min(10, max_n), key="n_state")
        else:
            n_state = max_n
        st_top = st_df.tail(n_state)  # st_df urut naik, jadi tail = state dengan keterlambatan tertinggi
        colors = [GREY] * max(len(st_top) - 5, 0) + [HIGHLIGHT] * min(5, len(st_top))
        fig = hbar(st_top, "late_pct", "customer_state", colors, None,
                   "%{x:.1f}%", customdata=st_top[["orders", "avg_review"]].to_numpy(),
                   hover="<b>%{y}</b><br>Terlambat: %{x:.1f}%<br>Pesanan: %{customdata[0]:,}<br>Rata-rata review: %{customdata[1]:.2f}<extra></extra>",
                   height=max(280, 34 * len(st_top) + 30))
        fig.update_layout(margin=dict(l=16, r=6, t=8, b=7))
        st.plotly_chart(fig, config=PLOT_CONFIG, theme=None)

    bins = [-np.inf, -8, -1, 0, 3, 7, np.inf]
    labels = ["Jauh lebih cepat<br>(>7 hari)", "Lebih cepat<br>(1-7 hari)", "Tepat di hari<br>estimasi",
              "Telat<br>1-3 hari", "Telat<br>4-7 hari", "Telat<br>>7 hari"]
    o = orders_f.copy()
    o["delay_group"] = pd.cut(o["delay_days"], bins=bins, labels=labels)
    dg = (o.groupby("delay_group", observed=True)
           .agg(orders=("order_id", "count"), avg_review=("review_score", "mean")).reset_index())
    dg["delay_group"] = dg["delay_group"].astype(str)
    top_i = dg["avg_review"].idxmax()
    colors = [GREY] * len(dg)
    colors[top_i] = HIGHLIGHT
    fig = go.Figure(go.Bar(
        x=dg["delay_group"], y=dg["avg_review"], marker_color=colors, text=dg["avg_review"],
        texttemplate="%{y:.2f}", textposition="outside", cliponaxis=False, customdata=dg[["orders"]].to_numpy(),
        hovertemplate="<b>%{x}</b><br>Rata-rata review: %{y:.2f}<br>Pesanan: %{customdata[0]:,}<extra></extra>"))
    fig.update_yaxes(range=[0, 5.6], dtick=1)
    fig = style_fig(fig, height=420, grid="y")
    fig.update_xaxes(tickangle=0)
    fig.update_layout(
        title_text="Rata-rata Review vs Selisih dari Tanggal Estimasi<br><sup>Skala review 1-5</sup>",
        margin=dict(l=16, r=6, t=48, b=41))
    card_chart(right, fig)

# TAB 4
with tab4:
    st.subheader("Bagaimana segmentasi pelanggan berdasarkan RFM?")
    snapshot = f["order_purchase_timestamp"].max().normalize() + pd.Timedelta(days=1)
    rfm = (f.groupby("customer_unique_id", as_index=False)
             .agg(last_order=("order_purchase_timestamp", "max"), frequency=("order_id", "nunique"), monetary=("price", "sum")))
    rfm["recency"] = (snapshot - rfm["last_order"].dt.normalize()).dt.days
    if len(rfm) >= 10:
        rfm["r_score"] = pd.qcut(rfm["recency"].rank(method="first", ascending=False), 5, labels=[1, 2, 3, 4, 5]).astype(int)
        rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
        rep, rec, big = rfm["frequency"] >= 2, rfm["r_score"] >= 4, rfm["m_score"] >= 4
        rfm["segment"] = np.select(
            [rep & rec, rep & ~rec, ~rep & rec & big, ~rep & rec & ~big, ~rep & ~rec & big],
            ["Champions", "Loyal Customers", "New Big Spenders", "New Customers", "Big Spenders at Risk"],
            default="Hibernating")
        seg = (rfm.groupby("segment").agg(customers=("customer_unique_id", "count"), revenue=("monetary", "sum"),
                                          avg_recency=("recency", "mean"), avg_monetary=("monetary", "mean")).reset_index())
        seg["Porsi pelanggan (%)"] = seg["customers"] / seg["customers"].sum() * 100
        seg["Porsi revenue (%)"] = seg["revenue"] / seg["revenue"].sum() * 100
        seg = seg.sort_values("Porsi revenue (%)")

        k1, k2, k3 = st.columns(3)
        k1.metric("Pelanggan dianalisis", f"{len(rfm):,}")
        k2.metric("Pelanggan membeli ulang (2+ pesanan)", f"{(rfm['frequency'] >= 2).mean() * 100:.1f}%")
        k3.metric("Rata-rata belanja per pelanggan", f"R$ {rfm['monetary'].mean():,.0f}")

        left, right = st.columns(2)
        for col, name in ((left, "Porsi pelanggan (%)"), (right, "Porsi revenue (%)")):
            colors = [HIGHLIGHT if i == seg[name].idxmax() else GREY for i in seg.index]
            fig = hbar(seg, name, "segment", colors, name, "%{x:.1f}%",
                       customdata=seg[["customers", "revenue", "avg_recency"]].to_numpy(),
                       hover="<b>%{y}</b><br>" + name + ": %{x:.1f}%<br>Pelanggan: %{customdata[0]:,}<br>Revenue: R$ %{customdata[1]:,.0f}<br>Rata-rata recency: %{customdata[2]:.0f} hari<extra></extra>",
                       height=340, x_pad=1.16)
            card_chart(col, fig)

        show_table(
            seg.sort_values("Porsi revenue (%)", ascending=False)[
                ["segment", "customers", "Porsi pelanggan (%)", "revenue", "Porsi revenue (%)", "avg_recency", "avg_monetary"]
            ].rename(columns={"segment": "Segmen", "customers": "Pelanggan", "revenue": "Revenue (R$)",
                              "avg_recency": "Rata-rata recency (hari)", "avg_monetary": "Rata-rata belanja (R$)"}),
            {"Pelanggan": "{:,.0f}", "Porsi pelanggan (%)": "{:.1f}", "Revenue (R$)": "{:,.0f}",
             "Porsi revenue (%)": "{:.1f}", "Rata-rata recency (hari)": "{:.0f}", "Rata-rata belanja (R$)": "{:,.0f}"})
        with st.expander("Aturan segmen"):
            st.markdown(
                "- **Champions**: Frequency 2+ dan R >= 4 (pembeli ulang dan masih baru)\n"
                "- **Loyal Customers**: Frequency 2+ dan R < 4\n"
                "- **New Big Spenders**: Frequency 1, R >= 4, M >= 4\n"
                "- **New Customers**: Frequency 1, R >= 4, M < 4\n"
                "- **Big Spenders at Risk**: Frequency 1, R < 4, M >= 4\n"
                "- **Hibernating**: Frequency 1, R < 4, M < 4")
    else:
        st.warning("Data terlalu sedikit untuk segmentasi RFM. Perluas filter.")

# TAB 5
with tab5:
    st.subheader("Bagaimana sebaran revenue dan keterlambatan antar state?")
    g = (f.groupby("customer_state").agg(revenue=("price", "sum"), lat=("customer_lat", "mean"), lng=("customer_lng", "mean"))
           .join(orders_f.groupby("customer_state").agg(orders=("order_id", "count"), late_pct=("is_late", lambda s: s.mean() * 100),
                                                        avg_review=("review_score", "mean")))
           .dropna(subset=["lat", "lng"]).reset_index())
    metric = st.radio("Warna lingkaran", ["Pesanan terlambat (%)", "Rata-rata review"], horizontal=True,
                      label_visibility="collapsed")
    color_col = "late_pct" if metric.startswith("Pesanan") else "avg_review"
    fig = px.scatter_map(g, lat="lat", lon="lng", size="revenue", color=color_col, hover_name="customer_state",
                         hover_data={"revenue": ":,.0f", "orders": ":,", "late_pct": ":.1f", "avg_review": ":.2f", "lat": False, "lng": False},
                         size_max=42, zoom=3, center={"lat": -15, "lon": -52}, map_style="carto-positron",
                         color_continuous_scale="YlOrRd" if color_col == "late_pct" else "YlGnBu",
                         labels={"late_pct": "Terlambat (%)", "avg_review": "Review", "revenue": "Revenue (R$)", "orders": "Pesanan"})
    fig.update_layout(height=560, margin=dict(l=16, r=6, t=14, b=14), coloraxis_colorbar=dict(title=None, thickness=12))
    card_chart(st, fig)
    st.caption("Ukuran lingkaran = revenue. Posisi = rata-rata koordinat pelanggan per state.")

    reg = (orders_f.groupby("region").agg(orders=("order_id", "count"), late_pct=("is_late", lambda s: s.mean() * 100),
                                          avg_delivery_days=("delivery_days", "mean"), avg_review=("review_score", "mean"))
                   .reset_index().sort_values("orders", ascending=False))
    st.markdown("**Ringkasan per wilayah (manual grouping)**")
    show_table(
        reg.rename(columns={"region": "Wilayah", "orders": "Pesanan", "late_pct": "Terlambat (%)",
                            "avg_delivery_days": "Rata-rata pengiriman (hari)", "avg_review": "Rata-rata review"}),
        {"Pesanan": "{:,.0f}", "Terlambat (%)": "{:.1f}", "Rata-rata pengiriman (hari)": "{:.1f}",
         "Rata-rata review": "{:.2f}"})