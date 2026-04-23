"""Page Rapport — export PDF de la dernière simulation pour annexer au rapport PFE."""

import io
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from components.branding import inject_global_css, render_footer, render_header

st.set_page_config(page_title="Rapport", page_icon="📄", layout="wide")
inject_global_css()

render_header(
    title="📄 Export du rapport de simulation",
    subtitle="Générez un PDF des résultats à annexer au rapport PFE",
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
ANTHRACITE = colors.HexColor("#2B2B2B")


def build_pdf(simulation: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title="Rapport de simulation — PFE Attijari Bank",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "H1", parent=styles["Title"], fontSize=18, textColor=ATTIJARI_RED,
        spaceAfter=8, alignment=0,
    )
    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"], fontSize=12, textColor=ANTHRACITE,
        spaceBefore=10, spaceAfter=6,
    )
    body = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontSize=10, textColor=ANTHRACITE,
        leading=14,
    )
    caption = ParagraphStyle(
        "Caption", parent=styles["BodyText"], fontSize=8,
        textColor=colors.HexColor("#6C757D"),
    )

    flow = []

    # --- Header ---
    flow.append(Paragraph("Rapport de simulation — Salle de marché", h1))
    flow.append(Paragraph(
        "Système d'aide à la décision IA · Cas Attijari Bank Tunisie · Modèle académique",
        caption,
    ))
    flow.append(Paragraph(
        f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        caption,
    ))
    flow.append(Spacer(1, 12))

    # --- Section 1 : Opération ---
    op = simulation["operation"]
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

    # --- Section 2 : Modules ---
    flow.append(Paragraph("2. Résultats par module", h2))
    fx = simulation["forex"]
    tr = simulation["treasury"]
    rk = simulation["risk"]
    cp = simulation["compliance"]

    modules_data = [
        ["Module", "Score brut", "État"],
        [
            "Forex", f"{fx['signal_score']:+d} / 4",
            f"{fx['signal']} (RSI={fx['rsi']:.1f}, MACD={fx['macd']:+.4f})",
        ],
        [
            "Trésorerie", f"Net cash {tr['net_cash']:+,.0f}",
            tr["treasury_recommendation"],
        ],
        [
            "Risque", f"{rk['risk_score']}/8",
            f"{rk['risk_level']} (infl={rk['inflation']}%, exp={rk['exposure_level']:.2f})",
        ],
        [
            "Conformité", str(len(cp["flags"])) + " flag(s)",
            cp["status"].replace("_", " "),
        ],
    ]
    flow.append(_styled_table(modules_data, col_widths=[3 * cm, 3.5 * cm, 10 * cm]))
    flow.append(Spacer(1, 10))

    # --- Section 3 : Formule pondérée ---
    dec = simulation["decision"]
    ns = dec["normalized_scores"]
    w = dec["weights"]

    flow.append(Paragraph("3. Calcul du score global pondéré", h2))
    formula_data = [
        ["Module", "Poids", "Score normalisé", "Contribution"],
        ["Forex", f"{w['forex']:.2f}", f"{ns['forex']:+.3f}", f"{w['forex'] * ns['forex']:+.4f}"],
        ["Trésorerie", f"{w['treasury']:.2f}", f"{ns['treasury']:+.3f}", f"{w['treasury'] * ns['treasury']:+.4f}"],
        ["Risque", f"{w['risk']:.2f}", f"{ns['risk']:+.3f}", f"{w['risk'] * ns['risk']:+.4f}"],
        ["Conformité", f"{w['compliance']:.2f}", f"{ns['compliance']:+.3f}", f"{w['compliance'] * ns['compliance']:+.4f}"],
        ["Score global", "", "", f"{dec['global_score']:+.4f}"],
    ]
    flow.append(_styled_table(formula_data, highlight_last_row=True))
    flow.append(Spacer(1, 10))

    # --- Section 4 : Décision finale ---
    flow.append(Paragraph("4. Décision finale", h2))
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
    flow.append(Paragraph(
        "Seuils appliqués : score &gt; +0.5 → BUY · score &lt; −0.5 → SELL · sinon HOLD. "
        "Bloqueurs durs : risque HIGH ou conformité NON_COMPLIANT → HOLD forcé.",
        caption,
    ))

    # --- Flags conformité ---
    if cp["flags"]:
        flow.append(Spacer(1, 10))
        flow.append(Paragraph("5. Flags de conformité relevés", h2))
        for flag in cp["flags"]:
            flow.append(Paragraph(f"• {flag}", body))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph(
        "Document généré automatiquement par le prototype académique. "
        "Les données marché proviennent de l'API Frankfurter (gratuite) ou d'une simulation.",
        caption,
    ))

    doc.build(flow)
    return buf.getvalue()


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
        "Le PDF contient : paramètres de l'opération, résultats des 4 modules, "
        "détail du calcul pondéré, décision finale, flags éventuels. À annexer au rapport PFE."
    )

render_footer()
