# Registre d'evaluation et de consultation du test

Ce registre sert a savoir ce qui a ete regarde sur le test, quand, et ce qui est gele avant E1 et E2. Il est mis a jour a chaque consultation.

## 1. Consultations du test deja faites

| N | Moment | Quoi | Resultats vus | Decision prise depuis |
|---|--------|------|---------------|------------------------|
| 1 | S3, novembre 2026, avant l'avis du 17/11 | E0 : XGBoost et regression logistique, scenarios A et B, populations principale et secondaire, tous les indicateurs de `reports/e0/resultats_e0.csv`, matrices au seuil gele, AP par jour, sans jour 31 | AP test XGBoost A 0,9996 et B 0,3437, regression logistique A 0,2572 et B 0,1149 | Scenario B retenu comme reference principale pour E1 et E2 |
| 2 | S3 bis, notebook 04 | Rejeu de E0 avec sauvegarde des scores, top K quotidien corrige, AP sans un jour, calibration, ablation du solde | A remplir apres execution du notebook | Aucune pour l'instant |

Le test n'est donc plus un test dont aucun resultat n'est connu pour E0.

## 2. Ce qui est gele pour E1 et E2

* Scenario d'entrees : B uniquement (type, montant et agregats de graphe calcules sur le passe). Aucun solde, aucune variable derivee du solde.
* Partitions : celles de `configs/splits.json`, steps 1 a 445, 446 a 594, 595 a 743.
* Population principale : TRANSFER + CASH_OUT. Population secondaire : tous les types, memes reglages.
* Grille d'hyperparametres : celle de `configs/e0.json` (profondeur 4, 6, 8, taux d'apprentissage 0,05 et 0,1, quatre strategies de desequilibre, arret anticipe 50 sur la validation).
* Regle de selection : voir fiche protocole version 2.
* Choix a faire sur la validation seulement. Le test est evalue une fois par configuration finale, apres gel de la configuration.
* Si un choix est modifie apres avoir regarde les scores de test d'E0, E1 ou E2, la comparaison concernee est declaree exploratoire dans la note.

## 3. Regles de construction des variables relationnelles (E1)

* Les agregats d'une transaction au step t n'utilisent que les evenements des steps strictement avant t. Les transactions du meme step ne se voient pas entre elles et sont scorees avant d'etre ajoutees a l'etat.
* L'arete cible n'entre jamais dans son propre voisinage.
* Les etiquettes des voisins ne sont pas utilisees, car leur disponibilite au moment de la decision n'est pas etablie.
* L'historique peut etre mis a jour dans l'ordre chronologique a travers validation et test avec les evenements passes seulement, sans reajuster le modele.
* Comptes sans historique : variables relationnelles absentes (valeur manquante) plus un indicateur d'historique, et resultats decomposes selon l'existence d'un historique d'emetteur et de beneficiaire, avec les effectifs.
* Tests de causalite a ecrire avant le premier entrainement de E1 (`tests/test_causalite.py`) :
  1. ajouter un evenement futur ne change pas les variables d'un evenement passe ;
  2. permuter les lignes d'un meme step ne change ni les variables ni les scores, a modele fixe ;
  3. un compte nouveau a des variables relationnelles vides ;
  4. aux frontieres des partitions, la premiere transaction de validation ou de test n'utilise que des evenements anterieurs ;
  5. les agregats sur de petites trajectoires sont verifies a la main.

## 4. Plan de comparaison

* E0 B contre E1 B sur les memes transactions, puis E1 contre E2 a information et support aussi proches que possible, avec la portee du voisinage, le budget d'entrainement et la regle de repli sans voisins declares a l'avance.
* Ecarts apparies par jour, avec et sans le jour 31, avec le retrait de chaque jour.
* Cout complet : construction des variables, entrainement, inference de bout en bout.
* Resultat nul ou gain limite a certains comptes : tous deux acceptables et rapportes tels quels.
