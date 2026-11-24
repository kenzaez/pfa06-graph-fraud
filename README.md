# Détection de fraudes financières par réseaux de neurones sur graphes

Projet de fin d'année PFA 06, EMSI, cinquième année du cycle ingénieur.
Encadrant : Pr. Mohammed MESTARI.
Réalisé par : Kenza EZZAHED et Oumnia EL FATIMI.

## Objectif

Comparer trois approches de détection de fraudes sur le corpus synthétique PaySim :

| Code | Modèle | Rôle |
|------|--------|------|
| E0 | XGBoost transactionnel | Référence sans graphe |
| E1 | XGBoost enrichi de statistiques relationnelles | Apport de l'information relationnelle |
| E2 | GraphSAGE avec tête de classification des arêtes | Apport de l'agrégation apprise |

Chaque transaction est évaluée uniquement à partir du graphe strictement antérieur à son heure de décision. Deux scénarios de variables sont comparés : A avec le solde de l'émetteur avant la transaction, B sans aucun solde (voir `configs/variables.json`).

## Structure du dépôt

```
pfa06-graph-fraud/
├── configs/         partitions temporelles et contrat de variables
├── data/            données brutes (non versionnées, voir data/README.md)
├── docs/            fiche protocole (R2, version 2), prévalence (R3), note S3, registre d'évaluation, réponse à l'expertise
├── models/          modèles E0 sauvegardés
├── notebooks/       notebooks d'analyse et d'expérimentation
├── reports/         figures et tableaux générés
├── src/             code réutilisable
├── tests/           tests du protocole
└── requirements.txt versions des bibliothèques
```

## Reproduire

1. Télécharger PaySim en suivant `data/README.md` et vérifier l'empreinte SHA256.
2. Installer les dépendances : `pip install -r requirements.txt`
3. Exécuter `notebooks/01_audit_paysim.ipynb` (testé sur Google Colab).
4. Exécuter `notebooks/02_controle_s2.ipynb` : réexécution de l'audit, tableau de concordance rapport / code, prévalence par jour et par partition.
5. Exécuter `notebooks/03_e0_xgboost.ipynb` : référence E0 et génération de `docs/note_s3_E0.md`.
6. Exécuter `notebooks/04_e0_rejeu_diagnostics.ipynb` : rejeu de E0, scores sauvegardés, top K quotidien corrigé, calibration, ablation du solde, manifeste.
7. Exécuter `notebooks/05_e1_graphe_causal.ipynb` : tests de causalité, variables du graphe sur le passé, E1 et comparaison à E0 B.
8. Lancer les tests du protocole : `pytest tests/`

En ligne de commande :

```
python -m src.audit data/PS_20174392719_1491204439457_log.csv
python -m src.concordance
python -m src.prevalence data/PS_20174392719_1491204439457_log.csv
python -c "from src.audit import load; from src import e0; e0.main(load('data/PS_20174392719_1491204439457_log.csv'))"
python -m src.rapport_s3
pytest tests/
```

## Avancement

| Semaine | Contenu | Statut |
|---------|---------|--------|
| S1 | Cadrage, état de l'art, vérification initiale de PaySim | Terminé |
| S2 | Audit complet, contrat de variables, partitions temporelles, fiche protocole, concordance (48/48 OK), prevalence par jour | Termine, fiche protocole en attente de validation du Pr. MESTARI |
| S3 | Référence E0 (XGBoost A et B, régression logistique), note générée automatiquement | Terminé, résultats dans `reports/e0/` et `docs/note_s3_E0.md` |
| S4 | Variables relationnelles causales sur G<t (E1) | Code, tests de causalité et notebook prêts, résultats à produire (notebook 05) |
| S5 | GraphSAGE avec classification des arêtes (E2) | À venir |
| S6 | Comparaison E0, E1, E2, ablations, analyse des erreurs | À venir |