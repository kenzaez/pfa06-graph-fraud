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
4. Lancer les tests du protocole : `pytest tests/`

## Avancement

| Semaine | Contenu | Statut |
|---------|---------|--------|
| S1 | Cadrage, état de l'art, vérification initiale de PaySim | Terminé |
| S2 | Audit complet, contrat de variables, partitions temporelles | En cours de validation |
| S3 | Référence E0 | À venir |