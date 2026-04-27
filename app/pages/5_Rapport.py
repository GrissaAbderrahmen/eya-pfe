"""Page Rapport — export PDF complet avec graphiques (candlestick, jauges, OHLC)."""

import io
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.explainer import explain_decision
from app.core.market_data import fetch_history_ohlc
from components.branding import (
    inject_global_css,
    render_attijari_logo,
    render_footer,
    render_header,
)
from components.charts import candlestick_chart
from components.gauges import confidence_gauge, global_score_gauge, normalized_scores_bar

st.set_page_config(page_title="Rapport", page_icon="📄", layout="wide")
inject_global_css()
render_attijari_logo()

render_header(
    title="📄 Export du rapport de simulation",
    subtitle="PDF complet avec graphiques candlestick, scores des modules, tableau OHLC et conclusion",
)

sim = st.session_state.get("last_simulation")
if not sim:
    st.warning(
        "Aucune simulation à exporter. Passez par la page **Simulateur** d'abord.",
        icon="👈",
    )
    render_footer()
    st.stop()

ATTIJARI_RED = colors.HexColor("#C8102E")
ATTIJARI_DARK = colors.HexColor("#8B0B20")
ANTHRACITE = colors.HexColor("#2B2B2B")


def _fig_to_image(fig, width_cm=16, height_cm=8) -> Image | None:
    """Convertit une figure Plotly en élément ReportLab Image via kaleido.

    Renvoie None en cas d'échec (kaleido non installé, conversion qui plante) —
    le PDF se génère alors sans le graphique plutôt que de planter complètement.
    """
    try:
        png_bytes = fig.to_image(format="png", width=900, height=int(900 * height_cm / width_cm),
                                 scale=2)
    except Exception:
        return None
    img = Image(io.BytesIO(png_bytes), width=width_cm * cm, height=height_cm * cm)
    return img


def _styled_table(data, col_widths=None, highlight_last_row=False):
    t = Table(data, colWidths=col_widths)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), ATTIJARI_RED),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E5E5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for row_idx in range(1, len(data)):
        if row_idx % 2 == 0:
            style.append(("BACKGROUND", (0, row_idx), (-1, row_idx),
                          colors.HexColor("#FAF6F3")))
    if highlight_last_row:
        style.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FDE7EB")))
        style.append(("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"))
    t.setStyle(TableStyle(style))
    return t


def build_pdf(simulation: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title="Rapport de simulation — PFE Attijari Bank",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Title"], fontSize=18, textColor=ATTIJARI_RED,
                        spaceAfter=8, alignment=0)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, textColor=ANTHRACITE,
                        spaceBefore=10, spaceAfter=6)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10, textColor=ANTHRACITE,
                          leading=14)
    caption = ParagraphStyle("Caption", parent=styles["BodyText"], fontSize=8,
                             textColor=colors.HexColor("#6C757D"))
    conclusion_style = ParagraphStyle("Conclusion", parent=body, fontSize=11,
                                      textColor=ATTIJARI_DARK, leading=16,
                                      backColor=colors.HexColor("#FDE7EB"),
                                      borderPadding=10, spaceBefore=6, spaceAfter=6)

    flow = []
    op = simulation["operation"]
    fx = simulation["forex"]
    tr = simulation["treasury"]
    rk = simulation["risk"]
    cp = simulation["compliance"]
    dec = simulation["decision"]

    # --- Header ---
    flow.append(Paragraph("ATTIJARI BANK — Salle de marché", h1))
    flow.append(Paragraph(
        "Système d'aide à la décision IA · Cas Attijari Bank Tunisie · Prototype fonctionnel",
        caption,
    ))
    flow.append(Paragraph(
        f"Date du rapport : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        caption,
    ))
    flow.append(Spacer(1, 12))

    # --- Section 1 : Opération ---
    flow.append(Paragraph("1. Paramètres de l'opération", h2))
    op_data = [
        ["Paramètre", "Valeur"],
        ["Montant (devise de base)", f"{op['amount']:,.0f}"],
        ["Paire de devises", op["pair"]],
        ["Sens", op["direction"]],
        ["Horizon", op["horizon"]],
    ]
    flow.append(_styled_table(op_data))
    flow.append(Spacer(1, 10))

    # --- Section 2 : Graphique candlestick ---
    flow.append(Paragraph("2. Évolution du marché — chandeliers japonais", h2))
    df_ohlc = fetch_history_ohlc(op["pair"], period="3mo")
    if not df_ohlc.empty:
        ma_series = df_ohlc["Close"].rolling(window=5, min_periods=1).mean()
        candle_fig = candlestick_chart(df_ohlc.tail(60), op["pair"],
                                       moving_average=ma_series.tail(60))
        candle_img = _fig_to_image(candle_fig, width_cm=16, height_cm=8)
        if candle_img:
            flow.append(candle_img)
        else:
            flow.append(Paragraph(
                "(Graphique candlestick indisponible — kaleido absent ou échec conversion.)",
                caption,
            ))
    else:
        flow.append(Paragraph("(Données OHLC indisponibles pour cette paire.)", caption))
    flow.append(Spacer(1, 8))

    # --- Section 3 : Modules + barres scores ---
    flow.append(Paragraph("3. Résultats par module", h2))
    modules_data = [
        ["Module", "Score brut", "État"],
        ["Forex", f"{fx['signal_score']:+d} / 4",
         f"{fx['signal']} (RSI={fx['rsi']:.1f}, MACD={fx['macd']:+.4f})"],
        ["Trésorerie", f"Net cash {tr['net_cash']:+,.0f}",
         tr["treasury_recommendation"]],
        ["Risque", f"{rk['risk_score']}/8",
         f"{rk['risk_level']} (infl={rk['inflation']}%, exp={rk['exposure_level']:.2f})"],
        ["Conformité", f"{len(cp['flags'])} flag(s)",
         cp["status"].replace("_", " ")],
    ]
    flow.append(_styled_table(modules_data, col_widths=[3 * cm, 3.5 * cm, 10 * cm]))
    flow.append(Spacer(1, 8))

    bar_img = _fig_to_image(
        normalized_scores_bar(dec["normalized_scores"], dec["weights"]),
        width_cm=16, height_cm=6,
    )
    if bar_img:
        flow.append(bar_img)
    flow.append(Spacer(1, 8))

    # --- Section 4 : Formule pondérée ---
    flow.append(PageBreak())
    flow.append(Paragraph("4. Calcul du score global pondéré", h2))
    ns = dec["normalized_scores"]
    w = dec["weights"]
    formula_data = [
        ["Module", "Poids", "Score normalisé", "Contribution"],
        ["Forex", f"{w['forex']:.2f}", f"{ns['forex']:+.3f}", f"{w['forex'] * ns['forex']:+.4f}"],
        ["Trésorerie", f"{w['treasury']:.2f}", f"{ns['treasury']:+.3f}",
         f"{w['treasury'] * ns['treasury']:+.4f}"],
        ["Risque", f"{w['risk']:.2f}", f"{ns['risk']:+.3f}", f"{w['risk'] * ns['risk']:+.4f}"],
        ["Conformité", f"{w['compliance']:.2f}", f"{ns['compliance']:+.3f}",
         f"{w['compliance'] * ns['compliance']:+.4f}"],
        ["Score global", "", "", f"{dec['global_score']:+.4f}"],
    ]
    flow.append(_styled_table(formula_data, highlight_last_row=True))
    flow.append(Spacer(1, 10))

    # --- Section 5 : Décision finale + jauges ---
    flow.append(Paragraph("5. Décision finale", h2))
    decision_line = (
        f"<b>Décision :</b> {dec['final_decision']} · "
        f"<b>Score global :</b> {dec['global_score']:+.3f} · "
        f"<b>Confiance :</b> {dec['confidence_score']:.0f} %"
    )
    flow.append(Paragraph(decision_line, body))
    if dec["decision_blocked"]:
        flow.append(Paragraph(
            "<b>⚠ Décision forcée à HOLD</b> — bloqueurs durs :<br/>"
            + "<br/>".join(f"• {r}" for r in dec["blocking_reasons"]),
            body,
        ))
    flow.append(Spacer(1, 6))

    gauge_score_img = _fig_to_image(global_score_gauge(dec["global_score"]),
                                    width_cm=8, height_cm=5)
    gauge_conf_img = _fig_to_image(confidence_gauge(dec["confidence_score"]),
                                   width_cm=8, height_cm=5)
    if gauge_score_img and gauge_conf_img:
        gauges_table = Table([[gauge_score_img, gauge_conf_img]],
                             colWidths=[8 * cm, 8 * cm])
        flow.append(gauges_table)
    flow.append(Spacer(1, 8))

    # --- Section 6 : Conformité (flags + warnings) ---
    flags = cp.get("flags", [])
    warnings_list = cp.get("warnings", [])
    if flags or warnings_list:
        flow.append(Paragraph("6. Contrôles de conformité — détail", h2))
        if flags:
            flow.append(Paragraph("<b>Violations réglementaires :</b>", body))
            for f in flags:
                flow.append(Paragraph(f"• {f}", body))
        if warnings_list:
            flow.append(Paragraph("<b>Zones d'alerte (proche du seuil) :</b>", body))
            for w_msg in warnings_list:
                flow.append(Paragraph(f"• {w_msg}", body))
        flow.append(Spacer(1, 8))

    # --- Section 7 : Tableau OHLC ---
    if not df_ohlc.empty:
        flow.append(Paragraph("7. Données OHLC — 20 derniers jours", h2))
        ohlc_tail = df_ohlc.tail(20).iloc[::-1].round(4)
        ohlc_data = [["Date", "Open", "High", "Low", "Close"]]
        for date, row in ohlc_tail.iterrows():
            ohlc_data.append([
                date.strftime("%Y-%m-%d"),
                f"{row['Open']:.4f}", f"{row['High']:.4f}",
                f"{row['Low']:.4f}", f"{row['Close']:.4f}",
            ])
        flow.append(_styled_table(ohlc_data,
                                  col_widths=[3 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm]))
        flow.append(Spacer(1, 10))

    # --- Section 8 : Conclusion (explainer) ---
    flow.append(Paragraph("8. Conclusion — interprétation pour le trader", h2))
    explanation = explain_decision(dec, fx, tr, rk, cp)
    # Markdown bold ** -> HTML <b> pour ReportLab
    explanation_html = explanation.replace("**", "")
    flow.append(Paragraph(explanation_html, conclusion_style))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph(
        "Document généré automatiquement par le prototype d'aide à la décision. "
        "Données de marché : Yahoo Finance · Conformité : règles BCT (LCR, position, exposition).",
        caption,
    ))

    doc.build(flow)
    return buf.getvalue()


# --- UI ---
op = sim["operation"]
dec = sim["decision"]

col1, col2 = st.columns([1, 2])
with col1:
    st.markdown("#### Aperçu de la simulation")
    st.markdown(
        f"""
- **Opération** : {op['direction']} de {op['amount']:,.0f} en {op['pair']}
- **Horizon** : {op['horizon']}
- **Décision** : **{dec['final_decision']}** ({dec['confidence_score']:.0f} % de confiance)
- **Score global** : {dec['global_score']:+.3f}
"""
    )

with col2:
    st.markdown("#### Télécharger le rapport")
    with st.spinner("Génération du PDF avec graphiques (kaleido)…"):
        pdf_bytes = build_pdf(sim)
    filename = f"Rapport_PFE_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    st.download_button(
        "📥 **Télécharger le PDF**",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
        type="primary",
        width='stretch',
    )
    st.caption(
        "Le PDF contient : opération, candlestick, scores des 4 modules en barres, "
        "calcul pondéré, jauges score+confiance, conformité, tableau OHLC, conclusion."
    )

st.divider()

# Mini aperçu
st.markdown("#### 🔍 Aperçu du contenu PDF")
preview_cols = st.columns(2)
with preview_cols[0]:
    st.plotly_chart(global_score_gauge(dec["global_score"]), width='stretch')
with preview_cols[1]:
    st.plotly_chart(confidence_gauge(dec["confidence_score"]), width='stretch')
st.plotly_chart(normalized_scores_bar(dec["normalized_scores"], dec["weights"]), width='stretch')

st.markdown("#### Conclusion (telle qu'elle apparaîtra dans le PDF)")
from app.core.explainer import explain_decision as _explain
st.info(_explain(dec, sim["forex"], sim["treasury"], sim["risk"], sim["compliance"]),
        icon="🎓")

render_footer()
