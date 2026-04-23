# Cahier de charges — PFE Finance (modèle d'aide à la décision)

## Contexte

Mon amie prépare un **PFE en finance** (pas en informatique/IA). Elle a conçu un **modèle d'aide à la décision** destiné aux entreprises. Son professeur lui demande de **prouver la validité du modèle sur un cas concret** (une entreprise exemple) : calculs, pourcentages, visualisations, et démonstration que le modèle aide réellement à la prise de décision.

Elle n'est pas développeuse — elle a besoin qu'on transforme son modèle théorique en **outil exploitable** (schémas, calculs automatisés, tableau de bord, ou application simple) pour illustrer son PFE.

**Avant de commencer**, on a besoin qu'elle remplisse ce questionnaire. Ses réponses détermineront :
- le périmètre exact du travail,
- les outils à utiliser (Excel, Python, web app, PowerPoint animé, etc.),
- les livrables finaux,
- le calendrier.

---

## Comment utiliser ce document

Elle répond **directement sous chaque question** (en français ou en anglais, peu importe). Les questions marquées 🔴 sont bloquantes — sans la réponse on ne peut rien démarrer. Les 🟡 sont importantes mais peuvent être précisées plus tard. Les 🟢 sont optionnelles / « nice to have ».

---

## 1. Le PFE en général

- 🔴 **Quel est le titre exact du PFE ?**
  > _Réponse : AI-Based Decision Support System in a Trading Room: Application to Forex, Treasury and Risk Management – Case of Attijari Bank Tunisia

- 🔴 **Quelle est la problématique / question de recherche ?** (1-2 phrases)
  > _Réponse : Comment un modèle d’aide à la décision basé sur l’intelligence artificielle peut-il améliorer la prise de décision dans une salle de marché bancaire en intégrant simultanément l’analyse du Forex, la gestion de trésorerie et le contrôle du risque ?

- 🔴 **Quel est le domaine précis de finance ?**
  (ex : finance d'entreprise, analyse financière, évaluation d'investissement, gestion de portefeuille, gestion des risques, finance islamique, audit, contrôle de gestion, finance de marché, etc.)
  > _Réponse : Finance de marché – Gestion de trésorerie – Gestion du risque – Marché des changes

- 🔴 **Niveau / diplôme** (Licence, Master 1, Master 2, ingénieur, autre) et **établissement** :
  > _Réponse : Licence en gestion (3ème année) – Tunisie

- 🔴 **Date de soutenance prévue** :
  > _Réponse : 11 mai le dépôt et début juin la soutenance  

- 🟡 **Langue finale du PFE et de la soutenance** (français, anglais, arabe) :
  > _Réponse :Français 

---

## 2. Le modèle d'aide à la décision

- 🔴 **Décris le modèle en 3-5 phrases**, comme si tu l'expliquais à quelqu'un qui n'y connaît rien en finance. Quelle décision aide-t-il à prendre ?
  (ex : « décider d'investir ou non dans un projet », « évaluer la santé financière d'une entreprise », « choisir entre plusieurs fournisseurs », « prédire un risque de faillite », etc.)
  > _Réponse :_ Le modèle que j’ai conçu est un système d’aide à la décision destiné à la salle de marché d’une banque. Il permet d’analyser simultanément plusieurs dimensions financières, notamment le marché des changes, la position de trésorerie, le niveau de risque et les contraintes réglementaires, afin de proposer une recommandation au trader.
Ce modèle intègre également un module d’interaction qui permet au trader de simuler une opération (achat ou vente de devises) en introduisant des paramètres tels que le montant, la devise et l’horizon temporel. Le système analyse ensuite l’impact de cette opération et fournit une recommandation structurée accompagnée d’un niveau de confiance.
L’objectif n’est pas de remplacer le trader, mais de renforcer la qualité, la rapidité et la cohérence de la prise de décision.
- 🔴 **Le modèle est-il :**
  - [ ] Entièrement de ta conception (original)
  - [ ] Une adaptation d'un modèle existant (lequel ? Altman Z-score, DCF, CAPM, WACC, Beneish M-score, autre ?)
  - [ ] Une combinaison de plusieurs modèles existants
  > _Réponse : Une combinaison de plusieurs approches existantes (analyse technique, gestion de trésorerie, scoring de risque) enrichie par un système d’interaction utilisateur permettant la simulation de décisions.
- 🔴 **Quels sont les INPUTS du modèle ?**
  (les données qu'on entre : chiffre d'affaires, ratio d'endettement, ROI, ROE, flux de trésorerie, nombre d'employés, secteur d'activité, etc. — liste-les toutes)
  > _Réponse : Le modèle utilise plusieurs types de données d’entrée :
les taux de change (EUR/USD, USD/TND, etc.), l’historique des prix, les flux de trésorerie (cash inflow et outflow), le niveau de liquidité, les taux d’intérêt, l’inflation, la volatilité du marché, le niveau d’exposition au risque, ainsi que des contraintes réglementaires (ratios de liquidité, limites de position).
En complément, le module d’interaction permet au trader d’introduire des paramètres spécifiques liés à une opération, notamment le montant de la transaction, la devise concernée, le type d’opération (achat ou vente) et l’horizon temporel.


- 🔴 **Quels sont les OUTPUTS du modèle ?**
  (ce que le modèle produit : un score ? un pourcentage ? une recommandation « oui / non » ? un classement ? plusieurs indicateurs ?)
  > _Réponse : Le modèle génère plusieurs types de résultats :
un signal de trading (BUY, SELL ou HOLD), une évaluation de la position de trésorerie (SURPLUS, DEFICIT ou BALANCED), un niveau de risque (LOW, MEDIUM ou HIGH), ainsi qu’une décision finale accompagnée d’un score de confiance.
Dans le cadre du module d’interaction, le système fournit également une analyse de l’impact de l’opération simulée sur la liquidité, le risque et la conformité réglementaire, avec une recommandation argumentée destinée au trader.

- 🔴 **Quelles sont les formules / équations du modèle ?**
  Peux-tu les écrire toutes (même à la main / photo) ? Y a-t-il des coefficients de pondération ? Des seuils de décision (ex : si score > 0.7 → investir) ?
  > _Réponse : Le modèle repose sur une combinaison de calculs issus de l’analyse financière et de règles de décision :
La moyenne mobile est utilisée pour identifier la tendance générale du marché en calculant la moyenne des prix sur une période donnée.
L’indicateur RSI permet d’évaluer les conditions de surachat ou de survente à partir des variations de prix.
La volatilité est mesurée à travers l’écart-type des rendements afin d’estimer le niveau d’incertitude du marché.
Un score global est ensuite calculé à partir d’une combinaison pondérée des différents modules :
Score global = (Signal Forex × 0.4) + (Score Trésorerie × 0.25) + (Score Risque × 0.25) + (Score Conformité × 0.1)
La décision finale est déterminée selon des seuils :
• Si le score est supérieur à 0.5 → recommandation d’achat 
• Si le score est inférieur à -0.5 → recommandation de vente 
• Sinon → recommandation d’attente 
Des règles de contrôle sont également intégrées :
• En cas de risque élevé → suspension ou prudence dans la décision 
• En cas de non-conformité réglementaire → blocage de l’opération 
Dans le module d’interaction, ces calculs sont appliqués en temps réel afin d’évaluer la pertinence d’une opération proposée par le trader.


- 🟡 **Le modèle utilise-t-il :**
  - [ ] Des pourcentages simples (ratios)
  - [ ] Des pondérations (coefficients)
  - [ ] Des scores agrégés
  - [ ] Des probabilités / statistiques
  - [ ] Des simulations (Monte Carlo, scénarios)
  - [ ] Autre : _________
  > _Réponse : ✔ Ratios
✔ Pondérations
✔ Score agrégé
✔ Simulation de scénarios (via interaction trader)

---

## 3. L'entreprise exemple (cas pratique)

- 🔴 **As-tu déjà choisi une entreprise pour l'exemple ?**
  - [ ] Oui, laquelle ? _________
  - [ ] Non, j'hésite entre : _________
  - [ ] Non, j'ai besoin d'aide pour en choisir une
  > _Réponse : Attijari Bank Tunisie 

- 🔴 **Est-ce une entreprise :**
  - [ ] Réelle (cotée en bourse, données publiques disponibles)
  - [ ] Réelle (non cotée, données obtenues via stage / contacts)
  - [ ] Fictive (cas d'école, données que tu inventes pour illustrer)
  > _Réponse : Entreprise réelle (données partiellement observées durant le stage + simulation académique)

- 🔴 **Sur quelle période veux-tu appliquer le modèle ?** (ex : 3 dernières années, 5 ans, une seule année, projection future)
  > _Réponse : Simulation sur données récentes (année actuelle) + scénarios simulés

- 🟡 **As-tu déjà les états financiers ?** (bilan, compte de résultat, tableau des flux)
  - [ ] Oui, au format PDF
  - [ ] Oui, au format Excel
  - [ ] Non, je dois encore les collecter
  > _Réponse : Partiellement disponibles, complétées par simulation réaliste


- 🟡 **Veux-tu comparer plusieurs entreprises** (benchmark sectoriel) ou une seule ?
  > _Réponse : Une seule banque (focus approfondi)

---

## 4. Ce que le professeur attend

- 🔴 **Qu'a demandé précisément le professeur pour « prouver » le modèle ?**
  (copie-colle ses consignes exactes si possible, ou résume)
  > _Réponse : Le professeur demande de démontrer la validité du modèle à travers un cas concret, en appliquant les formules sur des données réelles ou simulées, en présentant des résultats chiffrés, des graphiques, et en montrant que le modèle améliore la prise de décision.

- 🔴 **Quels livrables le professeur attend-il ?**
  - [ ] Rapport écrit (PFE complet) — tu t'en charges seule
  - [ ] Tableaux de calcul avec les résultats
  - [ ] Graphiques / visualisations
  - [ ] Schémas du modèle (flowchart, logigramme)
  - [ ] Démonstration logicielle (appli / Excel interactif / dashboard)
  - [ ] Soutenance avec slides
  - [ ] Autre : _________
  > _Réponse : ✔ Tableaux de calcul
✔ Graphiques
✔ Schéma du modèle
✔ Démonstration (Excel ou prototype)
✔ Slides de soutenance

- 🟡 **Le professeur a-t-il mentionné un outil spécifique ?** (Excel obligatoire ? Python ? SPSS ? R ? Power BI ?)
  > _Réponse : Excel recommandé

- 🟡 **Y a-t-il une partie « validation / test » attendue ?**
  (ex : comparer la prédiction du modèle à la réalité, test de sensibilité, analyse des limites)
  > _Réponse : Oui, comparaison entre décision humaine et décision du modèle + analyse des limites

---

## 5. Ce sur quoi j'ai besoin d'aide

Coche tout ce qui s'applique (on prioritera ensuite) :

- [ ] Schématiser le modèle (flowchart clair, logigramme, schéma de principe)
- [ ] Automatiser les calculs (Excel avec formules / Python)
- [ ] Créer un tableau de bord visuel (graphiques, pourcentages, jauges)
- [ ] Créer une petite application web où on entre les données et ça sort le résultat
- [ ] Générer des visualisations pour le rapport (camemberts, courbes, heatmaps)
- [ ] Faire une analyse de sensibilité (« si on change X de +10 %, le résultat varie de Y »)
- [ ] Préparer les slides de soutenance (schémas animés, démos)
- [ ] Valider que le modèle « fonctionne » statistiquement (backtesting, comparaison avec la réalité)
- [ ] Rédiger la partie méthodologie / technique du rapport
- [ ] Autre : _________
> _Réponse : ✔ Automatiser les calculs (Excel)
✔ Créer tableau de bord
✔ Schématiser le modèle
✔ Visualisations
✔ Slides
✔ Analyse de sensibilité

---

## 6. Préférences techniques et contraintes

- 🟡 **Quel est ton niveau technique ?**
  - [ ] Excel de base
  - [ ] Excel avancé (formules, TCD, macros)
  - [ ] J'ai déjà utilisé Python / R un peu
  - [ ] Aucun outil technique, juste Word
  > _Réponse : Excel intermédiaire

- 🟡 **Quel ordinateur utilises-tu ?** (Windows / Mac, version d'Excel)
  > _Réponse : ASUS Vivobook 

- 🟡 **Veux-tu pouvoir modifier / faire tourner le modèle toi-même** après mon aide, ou juste présenter le résultat ?
  > _Réponse : Mon objectif principal est de présenter les résultats du modèle de manière claire et professionnelle lors de la soutenance. Toutefois, je souhaite également comprendre le fonctionnement global de l’outil afin de pouvoir expliquer la logique des calculs et des décisions proposées. Il n’est pas nécessaire que je développe moi-même le modèle, mais il est important que je puisse l’utiliser et interpréter ses résultats de manière autonome.


- 🟢 **As-tu un budget / des outils payants à disposition ?** (Office 365, Power BI, etc.)
  > _Réponse : Je ne dispose pas de budget ni d’outils payants. Je privilégie donc des solutions accessibles telles que Excel ou des outils gratuits, compatibles avec les exigences académiques de mon projet.

---

## 7. Calendrier

- 🔴 **Date limite pour la version finale du modèle / exemple** :
  > _Réponse :26 avril 

- 🟡 **Y a-t-il des jalons intermédiaires** ? (présentation à mi-parcours, rendu partiel, réunion avec le prof)
  > _Réponse : réunion avec l’encadrante 

- 🟡 **Combien d'heures par semaine peux-tu y consacrer de ton côté** ? (pour itérer avec moi)
  > _Réponse : entre 2 et 3 heures 

---

## 8. Questions libres

- 🟢 **Quelque chose qui t'inquiète / te bloque en ce moment ?**
  > _Réponse : Actuellement, ma principale difficulté concerne la transformation de mon modèle théorique en un outil réellement praticable. En effet, j’ai conçu un modèle d’aide à la décision structuré, mais je cherche encore la meilleure manière de le tester concrètement à travers un cas réel ou simulé, notamment en ce qui concerne l’intégration des données et l’automatisation des calculs.
Je m’interroge également sur la manière de représenter visuellement les résultats afin de démontrer clairement l’utilité du modèle devant le jury, en particulier sous forme de tableau de bord ou d’interface interactive.
Enfin, je souhaite m’assurer que mon modèle reste à la fois simple, cohérent avec la réalité d’une salle de marché et suffisamment rigoureux pour être considéré comme pertinent d’un point de vue académique.

- 🟢 **Autres éléments utiles à partager** (photos du tableau avec les formules, premier brouillon du rapport, slides du cours, références citées par le prof, etc.)
  > _Réponse : J’ai effectué un stage au sein de la salle de marché de Attijari Bank, ce qui m’a permis d’observer concrètement le fonctionnement des opérations de change, de la gestion de trésorerie et du contrôle du risque. J’ai notamment compris le rôle des différents acteurs (traders, gestionnaires de trésorerie), les types d’opérations réalisées (spot, forward, couverture), ainsi que les contraintes liées à la réglementation et à la gestion de la liquidité.
Par ailleurs, j’ai déjà développé une première version d’un modèle académique en Python, structuré en plusieurs modules (analyse Forex, trésorerie, risque, conformité et moteur de décision). Je travaille actuellement sur son amélioration afin d’y intégrer un module d’interaction permettant au trader de simuler des opérations.
Je dispose également d’un début de rédaction de mon rapport (chapitres théoriques) ainsi que d’exemples de résultats issus de simulations, que je pourrai utiliser pour construire la partie pratique et les visualisations.

---

## Prochaines étapes (côté ami développeur)

Une fois ces réponses reçues, je vais :

1. **Relire et identifier les zones floues** → revenir avec 3-5 questions ciblées maximum.
2. **Proposer une architecture de solution** (Excel seul ? Excel + schémas ? Python notebook + dashboard ?) adaptée au niveau technique et au temps disponible.
3. **Définir les livrables concrets** avec un mini-planning.
4. **Démarrer** par le plus urgent (souvent : schématiser le modèle + automatiser les calculs sur l'entreprise exemple).

---

## Checklist minimale pour démarrer

Pour pouvoir **commencer quoi que ce soit**, il me faut **au minimum** :

- [ ] Le modèle décrit (section 2) avec au moins une formule
- [ ] Le nom de l'entreprise exemple (ou décision de prendre un cas fictif)
- [ ] Les consignes exactes du professeur (section 4)
- [ ] La deadline

Le reste peut se préciser en cours de route.

