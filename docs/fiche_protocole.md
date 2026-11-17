# Fiche protocole PFA 06 (R2)

Version 1, proposee le 16/11/2026, a valider par Pr. MESTARI avant tout entrainement.

Cette fiche fige les choix d'evaluation avant de regarder le moindre score. Les valeurs machine sont dans `configs/splits.json` et `configs/variables.json`, et `tests/test_protocol.py` verifie qu'elles sont bien renseignees.

## 1. Corpus

PaySim, fichier `PS_20174392719_1491204439457_log.csv`, SHA256 `16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b`. On utilise le fichier entier, sans retirer de lignes.

## 2. Population evaluee

* **Population principale : TRANSFER et CASH_OUT** (2 770 409 transactions, 0,30 % de fraudes). Toutes les fraudes du corpus sont dans ces deux types. Si on scorait aussi PAYMENT, CASH_IN et DEBIT, une partie du score viendrait juste du fait de reconnaitre des types qui ne sont jamais frauduleux dans le simulateur.
* **Population secondaire : tous les types** (6 362 620 transactions, 0,129 %). On la rapporte a part pour mesurer l'effet de la restriction.
* Les metriques et les taux de fraude sont toujours calcules sur la population annoncee, jamais melanges.
* L'historique du graphe (E1, E2) utilise toutes les operations passees, quel que soit leur type.

## 3. Decoupage temporel

* Unite : le step (heure simulee). Un jour = `(step - 1) // 24 + 1`.
* Entrainement : steps 1 a 445. Validation : 446 a 594. Test : 595 a 743.
* Les memes bornes pour E0, E1, E2 et pour les deux scenarios. Graine 42.
* L'encodage, la normalisation, la ponderation des classes, l'echantillonnage et les hyperparametres sont appris sur l'entrainement et la validation seulement.
* Ces bornes ne bougent pas en fonction des resultats du test. Les autres decoupages (70/15/15 par heures, 60/20/20 par volume) sont calcules uniquement comme diagnostic, sans y evaluer de modele.

## 4. Jour 31

Le jour 31 (steps 721 a 743) contient 272 transactions, toutes frauduleuses.

* **Resultat principal : test complet, jour 31 inclus.** C'est la periode definie a l'avance, et on decide avant de voir les scores.
* **Resultat diagnostique : test sans le jour 31**, toujours rapporte a cote.
* On n'exclura pas ce jour apres coup parce qu'il avantage ou desavantage un modele.

## 5. Scenarios de variables

* Scenario A : `type`, `amount`, `oldbalanceOrg`.
* Scenario B : `type`, `amount`.
* Toujours exclus : `newbalanceOrig`, `newbalanceDest`, `isFlaggedFraud`, `isFraud`, `step`. `oldbalanceDest` sert seulement en ablation separee.
* Les trois modeles sont compares dans les deux scenarios. On ne garde pas seulement celui qui arrange GraphSAGE.

## 6. Budget d'alertes

* Unite : le jour simule.
* K = 100, 250 et 500 alertes par jour, fixes maintenant et communs a tous les modeles. On compte entre 216 et 320 fraudes par jour, donc K = 250 correspond a peu pres au nombre de fraudes d'une journee, K = 100 a une capacite d'examen serree et K = 500 a une capacite large.
* Les jours ou le nombre de transactions scorees est inferieur a K sont signales dans les tableaux (c'est le cas du jour 31 pour K = 500).

## 7. Metriques

* Metrique principale : Average Precision (et pas "l'aire sous la courbe PR" en general).
* A cote de chaque AP : le taux de fraude de la partition (AP d'un modele au hasard) et le ratio AP / taux.
* Aussi : courbe precision rappel, Precision@K et Recall@K par jour, matrice de confusion au seuil gele, courbes de fiabilite, et l'AP jour par jour sur le test.

## 8. Seuil et calibration

* Le seuil de decision est choisi sur la validation (a budget d'alertes donne), puis gele pour le test.
* La calibration est ajustee sur la validation, avec sa distribution naturelle, et jugee a part du classement.

## 9. Analyses diagnostiques annoncees

Test sans le jour 31, population tous types, decoupages alternatifs, scores par jour. Elles sont toutes annoncees ici et ne servent jamais a choisir le protocole principal.

## 10. Regle de modification

Toute modification de cette fiche donne une nouvelle version datee, avec sa justification, faite avant toute evaluation sur le test.

## Preuves

`configs/splits.json`, `configs/variables.json`, `tests/test_protocol.py`, `reports/tables/prevalence_par_partition.csv` (comptages par population).

Validation encadrant : ______________________ Date : __________
