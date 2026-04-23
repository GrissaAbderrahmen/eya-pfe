# PFE — Système d'aide à la décision en salle de marché

Web-app de démonstration pour le PFE d'Eya (Licence en Gestion, Tunisie).
Cas d'étude : **Attijari Bank Tunisie** — système IA d'aide à la décision
pour une salle de marché, combinant Forex, trésorerie, risque et conformité.

## Démarrage rapide (local)

```bash
# Prérequis : Python 3.10+
pip install -r requirements.txt

# Lancer l'app
streamlit run app/main.py
```

Puis ouvrir <http://localhost:8501>.

## Tests

```bash
pytest tests/ -v
# ou sans pytest :
python app/core/engine.py
```

## Structure

```
app/
├── core/engine.py          ← 6 modules métier (Forex, Trésorerie, Risque, Conformité, Decision)
├── main.py                 ← page d'accueil Streamlit
├── pages/                  ← Marché, Simulateur, Décision IA, Sensibilité, Rapport
└── components/             ← branding, jauges et charts Plotly réutilisables
tests/                      ← tests pytest
.streamlit/config.toml      ← thème Attijari (bordeaux #C8102E)
```

## Déploiement (Streamlit Cloud, gratuit)

1. Push ce dossier sur un repo GitHub.
2. Sur <https://share.streamlit.io> : *New app* → pointer sur `app/main.py`.
3. L'URL publique est prête pour la soutenance.

## Formule de décision

```
Score global = 0.4 · Forex + 0.25 · Trésorerie + 0.25 · Risque + 0.10 · Conformité
```

Seuils : `> +0.5 → BUY`  |  `< −0.5 → SELL`  |  sinon `HOLD`.
Bloqueurs durs : risque HIGH ou conformité NON_COMPLIANT ⇒ HOLD forcé.
