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

## Version 2 du 23/11/2026 : precisions apres l'expertise du 17/11/2026

Cette version ne change aucun choix de E0 deja evalue. Elle precise la lecture des resultats et s'applique a E1 et E2. Le test a deja ete consulte pour E0 (voir `docs/registre_evaluation.md`), donc cette version n'est pas faite avant toute evaluation sur le test et on le dit.

* Reference principale : scenario B (type, montant), avec la regression logistique B. Le scenario A est un diagnostic de sensibilite aux entrees, pas une reference.
* Deux politiques d'alertes distinctes, jamais melangees dans un meme tableau :
  * seuil gele : seuil choisi sur la validation pour viser environ 250 alertes par jour, applique tel quel au test. Le nombre d'alertes reel sur le test est rapporte (`reports/e0/alertes_au_seuil_gele.csv`) ;
  * top K par jour : classement apres cloture du jour, repere hors ligne, pas une alerte immediate.
* Top K par jour : k_d = min(K, n_d), scores egaux departages par l'ordre de ligne d'origine, precision agregee = vrais positifs sur le nombre d'alertes reellement emises, jours partiels et jours sans negatif marques, effectifs et metriques quotidiens publies (`reports/e0/topk_quotidien.csv`).
* Scenario de decision avant execution : politique distincte, seuil gele applique dans l'ordre d'arrivee avec une capacite restante, a evaluer en S5. On ne suppose pas d'ordre fiable entre les transactions d'un meme step.
* Selection des hyperparametres : AP de validation non arrondie, en cas d'egalite exacte le premier de la grille (profondeur 4, 6, 8, puis taux d'apprentissage 0,05 puis 0,1). Pour E1 et E2 : parmi les reglages a moins de 0,0001 d'AP du meilleur, on garde le plus petit modele (profondeur minimale, puis nombre d'arbres minimal).
* Arret anticipe : critere `aucpr` calcule par XGBoost. La selection et toutes les AP publiees utilisent `average_precision_score` de scikit-learn. Ce sont deux calculs differents.
* Test : consultations enregistrees dans `docs/registre_evaluation.md`. Toute decision modifiee apres avoir vu le test rend la comparaison concernee exploratoire.
* Jours : le jour 25 est partiel (steps 595 a 600), le jour 31 est partiel et ne contient que des fraudes. Les resultats sont toujours donnes avec et sans le jour 31, et avec le retrait de chaque jour (`reports/e0/ap_sans_un_jour_test.csv`). Pas d'intervalle de confiance promis avec six jours utiles.

Validation encadrant : ______________________ Date : __________
