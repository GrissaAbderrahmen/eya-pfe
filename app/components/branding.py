"""Palette et composants de branding Attijari."""

import streamlit as st

COLORS = {
    "attijari_red": "#C8102E",
    "attijari_dark": "#8B0B20",
    "white": "#FFFFFF",
    "anthracite": "#2B2B2B",
    "success": "#2A9D8F",
    "warning": "#F4A261",
    "danger": "#E63946",
    "neutral": "#6C757D",
    "light_gray": "#F6F2EF",
    "cream": "#FDFBF7",
}

DECISION_COLORS = {
    "BUY": COLORS["success"],
    "SELL": COLORS["danger"],
    "HOLD": COLORS["neutral"],
}

RISK_COLORS = {
    "LOW": COLORS["success"],
    "MEDIUM": COLORS["warning"],
    "HIGH": COLORS["danger"],
}

COMPLIANCE_COLORS = {
    "COMPLIANT": COLORS["success"],
    "WARNING": COLORS["warning"],
    "NON_COMPLIANT": COLORS["danger"],
}


def inject_global_css():
    """CSS global : typographie, cartes, badges. À appeler une fois par page."""
    st.markdown(
        """
        <style>
        /* ---- Typo et layout général ---- */
        html, body, [class*="css"]  {
            font-family: "Inter", "Helvetica Neue", Arial, sans-serif;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        /* ---- Bandeau de titre ---- */
        .ati-header {
            background: linear-gradient(135deg, #C8102E 0%, #8B0B20 100%);
            color: white;
            padding: 1.5rem 2rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        .ati-header h1 {
            margin: 0 0 0.25rem 0;
            font-size: 1.75rem;
            font-weight: 700;
            color: white;
        }
        .ati-header p {
            margin: 0;
            opacity: 0.92;
            font-size: 0.95rem;
        }

        /* ---- Cartes de module ---- */
        .module-card {
            background: white;
            border: 1px solid #EFE9E5;
            border-radius: 10px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        .module-card .label {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #6C757D;
            margin-bottom: 0.35rem;
        }
        .module-card .value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #2B2B2B;
        }
        .module-card .hint {
            font-size: 0.85rem;
            color: #6C757D;
            margin-top: 0.35rem;
        }

        /* ---- Badge décision ---- */
        .decision-badge {
            display: inline-block;
            padding: 0.6rem 1.5rem;
            border-radius: 999px;
            font-size: 1.35rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            color: white;
        }
        .decision-badge.BUY { background: #2A9D8F; }
        .decision-badge.SELL { background: #E63946; }
        .decision-badge.HOLD { background: #6C757D; }

        /* ---- Bandeau de blocage ---- */
        .blocked-banner {
            background: #FFE5E9;
            border-left: 4px solid #E63946;
            color: #8B0B20;
            padding: 0.9rem 1.2rem;
            border-radius: 8px;
            margin: 1rem 0;
            font-weight: 500;
        }

        /* ---- Footer discret ---- */
        .ati-footer {
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid #EFE9E5;
            color: #9A9A9A;
            font-size: 0.82rem;
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(title: str, subtitle: str = "") -> None:
    """Bandeau de titre Attijari en haut de page."""
    st.markdown(
        f"""
        <div class="ati-header">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        """
        <div class="ati-footer">
            PFE — Système d'aide à la décision en salle de marché · Cas Attijari Bank Tunisie ·
            Modèle académique, données partiellement simulées.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_decision_badge(decision: str) -> None:
    st.markdown(
        f'<div style="text-align:center; margin: 1rem 0;">'
        f'<span class="decision-badge {decision}">{decision}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_blocked_banner(reasons: list) -> None:
    if not reasons:
        return
    bullets = "".join(f"<li>{r}</li>" for r in reasons)
    st.markdown(
        f'<div class="blocked-banner"><strong>⛔ Opération bloquée :</strong>'
        f"<ul style='margin: 0.4rem 0 0 1rem;'>{bullets}</ul></div>",
        unsafe_allow_html=True,
    )


def render_module_card(label: str, value: str, hint: str = "") -> None:
    hint_html = f'<div class="hint">{hint}</div>' if hint else ""
    st.markdown(
        f'<div class="module-card">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        f"{hint_html}"
        f"</div>",
        unsafe_allow_html=True,
    )
