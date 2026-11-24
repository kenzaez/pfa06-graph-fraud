# S4 : E1, XGBoost avec statistiques du graphe causal

Etat au 24/11/2026. Le code, les tests de causalite et le notebook sont prets. Les resultats sur PaySim viendront du notebook 05.

## 1. Regle causale

Pour une transaction au step t, toutes les variables relationnelles utilisent seulement les transactions des steps strictement avant t, tous types confondus (PAYMENT, CASH_IN et DEBIT compris, comme prevu dans `configs/splits.json`). Une transaction ne voit jamais celles de son propre step, ni sa propre arete, ni aucune etiquette.

Consequence : ajouter une transaction future ne change aucune variable passee, et melanger l'ordre des lignes ne change rien.

## 2. Variables (19, fenetre de 24 steps)

Pour l'emetteur (orig) et le beneficiaire (dest) :

| Variable | Sens |
|----------|------|
| sortant_n, sortant_somme | nombre et somme des envois passes du compte |
| entrant_n, entrant_somme | nombre et somme des receptions passees |
| sortant_n24, entrant_n24 | meme chose sur les 24 steps avant t |
| contreparties_dist | nombre de contreparties distinctes passees (destinataires pour l'emetteur, emetteurs pour le beneficiaire) |
| ecart_dernier | steps ecoules depuis la derniere activite du compte (manquant si aucune) |
| a_historique | 1 si le compte a deja une activite passee |

Plus `g_paire_n` : nombre de fois ou cette paire emetteur beneficiaire a deja ete vue. Code : `src/graphe_causal.py`.

## 3. Tests

`tests/test_causalite.py` :
1. un evenement futur ne change aucune variable passee (coupures aux steps 100, 445, 594) ;
2. aux frontieres de partitions, la premiere transaction de validation ou de test n'utilise que des evenements anterieurs ;
3. permuter les lignes ne change ni les variables ;
4. changer ou retirer les etiquettes ne change rien ;
5. un compte nouveau a des variables vides et l'arete cible n'est pas comptee ;
6. une petite trajectoire est verifiee a la main (comptes, sommes, fenetre de 24 steps, ecart, paires).

Les tests passent sur des donnees synthetiques. Le notebook 05 refait aussi le test de coupure sur les vraies donnees.

## 4. Protocole d'evaluation

* Reference : E0 B (type et montant), memes lignes. Scenario E1 = B plus les 19 variables.
* Memes partitions, memes populations, meme grille et meme regle de selection que E0 (fiche protocole version 2).
* Resultats : AP, P@K et R@K, matrice au seuil gele, AP par jour, avec et sans jour 31, selon l'existence d'un historique de l'emetteur et du beneficiaire.
* Comparaison appariee E0 B contre E1 (`src/comparaison_e0_e1.py`) : AP globale, par jour, selon l'historique.
* Un gain nul ou limite aux comptes avec historique est un resultat valable.

## 4 bis. Limite connue a l'avance

Dans PaySim, 99,84 % des emetteurs sont nouveaux et aucune paire emetteur beneficiaire ne se repete. Les variables de l'emetteur seront donc vides pour presque toutes les transactions. Les variables du beneficiaire peuvent porter plus d'information. A mesurer dans le notebook 05 (part de transactions avec historique).

## 5. Fichiers

`src/graphe_causal.py`, `src/e1.py`, `src/comparaison_e0_e1.py`, `tests/test_causalite.py`, `configs/variables.json` (scenario E1), `notebooks/05_e1_graphe_causal.ipynb`.
