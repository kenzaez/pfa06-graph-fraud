# Note d'avancement S3 : reference E0 (XGBoost transactionnel)

PFA 06, Kenza EZZAHED et Oumnia EL FATIMI, encadrant Pr. Mohammed MESTARI. Genere le 17/11/2026 par `src/rapport_s3.py` a partir des sorties du notebook `03_e0_xgboost.ipynb`.

## 1. Objet

Cette semaine couvre les recommandations R4 (deux scenarios de variables tires d'un contrat unique) et R5 (baseline E0 competitive). Elle s'appuie sur le protocole gele en fin de S2 (`docs/fiche_protocole.md`).

Controle de l'audit (R1) : la reexecution independante de l'audit a ete faite sur les donnees reelles (notebook 02) et les 48 valeurs du rapport sont retrouvees (48/48 OK, voir `reports/tables/concordance.csv`).

## 2. Protocole applique

* Population principale : TRANSFER et CASH_OUT. Population secondaire : tous les types, avec les memes hyperparametres.
* Decoupage : steps 1 a 445 (entrainement), 446 a 594 (validation), 595 a 743 (test). Le test n'a ete utilise qu'une fois, apres le choix des hyperparametres et du seuil.
* Scenario A : `type`, `amount`, `oldbalanceOrg`, plus deux variables derivees declarees dans `configs/variables.json` et calculees uniquement a partir de ces colonnes (`oldbalanceOrg - amount` et `amount / (oldbalanceOrg + 1)`). Scenario B : `type` et `amount`. Aucun solde posterieur, ni `step`, ni `isFlaggedFraud`, ni identifiant de compte (verifie par `tests/test_features.py`).
* Desequilibre : quatre strategies comparees sur la validation, soit le ratio naturel avec `scale_pos_weight`, soit un sous echantillonnage des transactions normales de l'entrainement jusqu'a 1 %, 5 % ou 10 % de fraudes (graine 42). On n'a jamais combine les deux. La validation et le test gardent leur distribution naturelle.
* Grille : profondeur [4, 6, 8], taux d'apprentissage [0.05, 0.1], jusqu'a 500 arbres avec arret precoce (50 tours) sur l'AP de validation, subsample 0.8.
* Reference simple : regression logistique (log signe, standardisation, `class_weight="balanced"`) sur les memes variables.
* Seuil : choisi sur la validation pour produire en moyenne 250 alertes par jour, puis gele pour le test.
* Budget d'alertes : K = 100, 250, 500 alertes par jour simule. P@K et R@K sont agreges sur les jours de la partition.

## 3. Hyperparametres retenus (validation)

| Scenario | Desequilibre | Lignes d'entrainement | Profondeur | Taux d'apprentissage | scale_pos_weight | Arbres | AP validation |
|---|---|---|---|---|---|---|---|
| A | sous_ech_10pct | 50070 | 6 | 0,10 | 1,0 | 66 | 1,000 |
| B | sous_ech_1pct | 500700 | 8 | 0,10 | 1,0 | 13 | 0,293 |

Meilleure AP de validation par strategie de desequilibre :

| Scenario | Strategie | Meilleure AP validation |
|---|---|---|
| A | naturel_spw | 0,995 |
| A | sous_ech_10pct | 1,000 |
| A | sous_ech_1pct | 0,999 |
| A | sous_ech_5pct | 1,000 |
| B | naturel_spw | 0,292 |
| B | sous_ech_10pct | 0,291 |
| B | sous_ech_1pct | 0,293 |
| B | sous_ech_5pct | 0,290 |

## 4. Resultats principaux : TRANSFER et CASH_OUT

### Test (jour 31 inclus, resultat principal)

| Modele | Scenario | AP | Taux de fraude | AP / taux | P@100 | R@100 | P@250 | R@250 | P@500 | R@500 | F1 au seuil | Brier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XGBoost | A | 1,000 | 3,225 % | 31,0 | 0,934 | 0,395 | 0,887 | 0,938 | 0,505 | 0,999 | 0,955 | 0,0001 |
| RegLog | A | 0,257 | 3,225 % | 8,0 | 0,294 | 0,125 | 0,341 | 0,361 | 0,333 | 0,659 | 0,154 | 0,0901 |
| XGBoost | B | 0,344 | 3,225 % | 10,7 | 0,659 | 0,279 | 0,425 | 0,449 | 0,280 | 0,553 | 0,334 | 0,0256 |
| RegLog | B | 0,115 | 3,225 % | 3,6 | 0,371 | 0,157 | 0,275 | 0,291 | 0,182 | 0,360 | 0,151 | 0,2112 |

### Validation

| Modele | Scenario | AP | Taux de fraude | AP / taux | P@100 | R@100 | P@250 | R@250 | P@500 | R@500 | F1 au seuil | Brier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XGBoost | A | 1,000 | 1,642 % | 60,9 | 1,000 | 0,451 | 0,854 | 0,963 | 0,443 | 1,000 | 0,899 | 0,0000 |
| RegLog | A | 0,151 | 1,642 % | 9,2 | 0,081 | 0,037 | 0,127 | 0,144 | 0,151 | 0,340 | 0,104 | 0,0836 |
| XGBoost | B | 0,293 | 1,642 % | 17,8 | 0,540 | 0,244 | 0,261 | 0,294 | 0,162 | 0,365 | 0,270 | 0,0131 |
| RegLog | B | 0,060 | 1,642 % | 3,7 | 0,147 | 0,066 | 0,084 | 0,095 | 0,065 | 0,146 | 0,085 | 0,2129 |

### Matrices de confusion sur le test, au seuil fixe sur la validation

| Modele | Scenario | Seuil (fixe sur validation) | VP | FP | FN | VN | Precision | Rappel |
|---|---|---|---|---|---|---|---|---|
| RegLog | A | 0,9714 | 216 | 941 | 1438 | 48691 | 0,187 | 0,131 |
| XGBoost | A | 0,0056 | 1653 | 153 | 1 | 49479 | 0,915 | 0,999 |
| RegLog | B | 0,8211 | 182 | 568 | 1472 | 49064 | 0,243 | 0,110 |
| XGBoost | B | 0,0470 | 485 | 762 | 1169 | 48870 | 0,389 | 0,293 |

## 5. Resultats diagnostiques

### Test sans le jour 31

| Modele | Scenario | AP | Taux de fraude | AP / taux | P@100 | R@100 | P@250 | R@250 | P@500 | R@500 | F1 au seuil | Brier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XGBoost | A | 1,000 | 2,709 % | 36,9 | 0,923 | 0,401 | 0,868 | 0,942 | 0,460 | 0,999 | 0,947 | 0,0001 |
| RegLog | A | 0,226 | 2,709 % | 8,3 | 0,177 | 0,077 | 0,231 | 0,251 | 0,273 | 0,592 | 0,145 | 0,0905 |
| XGBoost | B | 0,328 | 2,709 % | 12,1 | 0,602 | 0,261 | 0,329 | 0,357 | 0,214 | 0,465 | 0,318 | 0,0215 |
| RegLog | B | 0,099 | 2,709 % | 3,7 | 0,267 | 0,116 | 0,155 | 0,168 | 0,108 | 0,234 | 0,146 | 0,2112 |

### Population secondaire (tous les types), test

| Modele | Scenario | AP | Taux de fraude | AP / taux | P@100 | R@100 | P@250 | R@250 | P@500 | R@500 | F1 au seuil | Brier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XGBoost | A | 0,999 | 1,338 % | 74,7 | 0,934 | 0,395 | 0,886 | 0,938 | 0,505 | 0,999 | 0,964 | 0,0001 |
| RegLog | A | 0,196 | 1,338 % | 14,7 | 0,196 | 0,083 | 0,186 | 0,196 | 0,254 | 0,503 | 0,036 | 0,0466 |
| XGBoost | B | 0,338 | 1,338 % | 25,3 | 0,649 | 0,274 | 0,428 | 0,453 | 0,281 | 0,555 | 0,331 | 0,0103 |
| RegLog | B | 0,114 | 1,338 % | 8,5 | 0,371 | 0,157 | 0,275 | 0,291 | 0,182 | 0,360 | 0,151 | 0,1593 |

## 6. Stabilite jour par jour sur le test

| Scenario | Modele | AP min | AP mediane | AP max |
|---|---|---|---|---|
| A | RegLog | 0,064 | 0,315 | 0,445 |
| A | XGBoost | 0,998 | 1,000 | 1,000 |
| B | RegLog | 0,023 | 0,139 | 0,266 |
| B | XGBoost | 0,215 | 0,355 | 0,473 |

| Jour | Transactions | Fraudes | Taux | AP XGBoost A | AP XGBoost B |
|---|---|---|---|---|---|
| 25 | 7736 | 54 | 0,70 % | 1,000 | 0,215 |
| 26 | 5458 | 272 | 4,98 % | 1,000 | 0,376 |
| 27 | 3722 | 280 | 7,52 % | 0,998 | 0,473 |
| 28 | 5724 | 248 | 4,33 % | 1,000 | 0,335 |
| 29 | 23313 | 260 | 1,12 % | 1,000 | 0,312 |
| 30 | 5061 | 268 | 5,30 % | 1,000 | 0,457 |

Les jours sans fraude ou sans transaction normale (comme le jour 31) n'ont pas d'AP definie.

## 7. Variables qui pesent dans le score

Moyenne des valeurs SHAP absolues de XGBoost sur un echantillon d'entrainement :

* Scenario A : ecart_montant_solde (4,640), ratio_montant_solde (1,004), amount (0,526), oldbalanceOrg (0,341), type_CASH_OUT (0,088)
* Scenario B : type_CASH_OUT (0,602), amount (0,494)

Ces valeurs decrivent le modele, elles ne disent pas pourquoi une transaction est frauduleuse.

## 8. Calibration

Le score de Brier est dans les tableaux, et les courbes de fiabilite sont dans `reports/e0/fiabilite_*.png`. Quand l'entrainement est sous echantillonne, les scores ne sont plus des probabilites realistes : ils surestiment le risque. Le classement (AP, P@K) n'en depend pas. Une calibration sur la validation sera etudiee a part (R11), en tenant compte du changement de taux de fraude entre validation et test.

## 9. Couts

| Modele | Scenario | Entrainement (s) | Latence pour 1000 tx (ms) | Taille (Ko) |
|---|---|---|---|---|
| RegLog | A | 10,1 | 1,03 | n/a |
| XGBoost | A | 2,0 | 2,87 | 220 |
| RegLog | B | 4,8 | 0,72 | n/a |
| XGBoost | B | 3,5 | 1,98 | 579 |

## 10. Lecture des resultats

1. Avec le solde de l'emetteur (scenario A), XGBoost obtient une AP de 1,000 sur le test, contre 0,344 sans solde (scenario B). L'ecart de 0,656 mesure le poids du raccourci montant egal au solde. C'est une propriete du simulateur, pas une preuve de detection realiste.
2. Scenario A : XGBoost (1,000) est au dessus de la regression logistique (0,257).
3. Scenario B : XGBoost (0,344) est au dessus de la regression logistique (0,115).
4. Dans le scenario B, l'AP de XGBoost vaut 10,7 fois le hasard. C'est la reference que E1 et E2 devront depasser grace a l'information relationnelle.
5. Sans le jour 31, l'AP de XGBoost en scenario A passe de 1,000 a 1,000 (taux de fraude 2,709 %).
6. Sans le jour 31, l'AP de XGBoost en scenario B passe de 0,344 a 0,328 (taux de fraude 2,709 %).

## 11. Limites

* PaySim est synthetique : les resultats ne disent rien de l'efficacite sur une vraie banque.
* Le scenario A repose en grande partie sur une regle du simulateur.
* L'entrainement est dans la periode chargee, la validation et le test dans la periode calme : le modele est evalue dans un autre regime que celui ou il a appris.
* Pas encore d'intervalles de confiance par blocs temporels (prevu en S8).

## 12. Suite (S4)

Construction causale du graphe historique G<t et des agregats de E1 (R6) : degres entrants et sortants, partenaires distincts, montants cumules, fenetres 24 h et 72 h, indicateur d'historique absent. Mesure des degres reellement disponibles au moment de la decision (R7).

## 13. Fichiers de preuve

* Code : `src/features.py`, `src/e0.py`, `src/rapport_s3.py`, `notebooks/03_e0_xgboost.ipynb`
* Contrat et configuration : `configs/variables.json`, `configs/e0.json`, `reports/e0/config_choisie.json`
* Modeles : `models/e0_xgb_*.json`
* Resultats : `reports/e0/resultats_e0.csv`, `reports/e0/selection_*.csv`, `reports/e0/ap_par_jour_test.csv`, `reports/e0/shap_*.csv`
* Figures : `reports/e0/pr_*.png`, `reports/e0/fiabilite_*.png`
* Tests : `tests/test_protocol.py`, `tests/test_features.py`, `tests/test_concordance.py`
