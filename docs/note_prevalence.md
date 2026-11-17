# Note sur le changement de prevalence (R3)

Tableaux generes par `src/prevalence.py` (notebook `02_controle_s2.ipynb`) :

* `reports/tables/prevalence_par_jour.csv` : transactions, fraudes et taux par jour, pour tous les types et pour TRANSFER + CASH_OUT, avec regime de volume, jours atypiques et depassement de budget.
* `reports/tables/prevalence_par_partition.csv` : la meme chose par partition, avec l'AP d'un modele au hasard.
* `reports/tables/test_sans_jour31.csv` et `reports/tables/sensibilite_decoupage.csv` : diagnostics.
* `reports/figures/prevalence_par_jour.png`.

Les chiffres ci dessous viennent de l'execution du notebook `02_controle_s2.ipynb` du 17/11/2026. Les 48 indicateurs du rapport concordent avec la sortie du code (`reports/tables/concordance.csv`).

## 1. Ce qu'on observe

PaySim alterne deux regimes de volume. Les jours 1, 2 et 6 a 17 comptent entre 400 000 et 575 000 transactions. Les jours 3 a 5 et 18 a 31 en comptent moins de 60 000. Le nombre de fraudes, lui, reste stable, entre 216 et 320 par jour. Le taux de fraude depend donc surtout du volume de transactions normales, et pas d'une variation du nombre de fraudes.

| Partition | Steps | Tous types : transactions | Tous types : taux | TRANSFER + CASH_OUT : transactions | TRANSFER + CASH_OUT : taux |
|---|---|---|---|---|---|
| Entrainement | 1 a 445 | 6 010 937 | 0,083 % | 2 624 611 | 0,191 % |
| Validation | 446 a 594 | 228 103 | 0,680 % | 94 512 | 1,642 % |
| Test | 595 a 743 | 123 580 | 1,338 % | 51 286 | 3,225 % |
| Test sans jour 31 | 595 a 720 | 123 308 | 1,121 % | 51 014 | 2,709 % |

Le decoupage par heures tombe pile sur le changement de regime : l'entrainement est presque entierement dans la periode chargee, la validation et le test sont entierement dans la periode calme. Sur la population principale (TRANSFER + CASH_OUT), le taux de fraude est 17 fois plus eleve en test qu'en entrainement (3,225 % contre 0,191 %), le meme rapport que sur tous les types. Le jour 31 explique une partie de l'ecart : sans lui, le test descend a 2,709 %.

## 2. Pourquoi ce n'est pas une fuite, mais ca reste un probleme

Le decoupage est strictement chronologique, donc aucun modele ne voit le futur. Par contre :

* L'Average Precision d'un modele au hasard est egale au taux de fraude. Une AP de 0,40 ne veut pas dire la meme chose en entrainement (taux 0,083 %) et en test (taux 1,338 %). On affiche donc toujours le taux et le ratio AP / taux a cote de chaque AP.
* Le modele apprend dans un regime et il est evalue dans un autre. C'est un vrai decalage de distribution, qu'on mentionnera dans les limites.
* Un seuil ou une calibration regles sur la validation peuvent mal se transferer au test, puisque les taux ne sont pas les memes (1,64 % contre 3,23 % sur TRANSFER + CASH_OUT). Les deux sont quand meme dans le regime calme, ce qui rend la validation plus representative du test que l'entrainement.
* Les comparaisons entre modeles se font sur les memes transactions de test. Le taux de fraude est donc le meme pour E0, E1 et E2, et les differences d'AP restent comparables entre elles.

## 3. Jours atypiques

Le jour 31 contient 272 transactions, toutes frauduleuses. Un modele qui place ces transactions en haut du classement gagne beaucoup de rappel sans effort. Le traitement est decide dans la fiche protocole : resultat principal avec le jour 31, resultat diagnostique sans. Un seul autre jour est marque `atypique` dans le tableau journalier : le jour 3, dans l'entrainement, avec 1 070 transactions dont 310 fraudes (72,3 % des TRANSFER + CASH_OUT). Il est dans la partition d'apprentissage, il n'affecte donc pas l'evaluation, mais on le signale.

## 4. Budget d'alertes

Le budget est fixe par jour simule (K = 100, 250, 500). Les jours ou le nombre de transactions TRANSFER + CASH_OUT est inferieur a K sont marques dans les colonnes `budget_K_depasse`. Sur le test, seul le jour 31 est concerne, et seulement pour K = 500 (272 transactions). Pour K = 250, le jour 31 a juste assez de transactions, mais comme elles sont toutes frauduleuses, n'importe quel modele y obtient une precision de 1 : c'est pour ca qu'on rapporte aussi le test sans ce jour. Dans l'entrainement, le jour 3 depasse aussi le budget K = 500 (429 transactions).

## 5. Sensibilite du decoupage (diagnostic)

| Decoupage | Steps | Taux entrainement | Taux validation | Taux test | Taux test TRANSFER + CASH_OUT |
|---|---|---|---|---|---|
| Heures 60/20/20 (reference) | 1 a 445, 446 a 594, 595 a 743 | 0,083 % | 0,680 % | 1,338 % | 3,225 % |
| Heures 70/15/15 | 1 a 520, 521 a 631, 632 a 743 | 0,095 % | 0,617 % | 1,399 % | 3,297 % |
| Volume 60/20/20 | 1 a 281, 282 a 355, 356 a 743 | 0,084 % | 0,060 % | 0,340 % | 0,799 % |

Le decoupage par volume rapproche les taux mais ne supprime pas l'ecart, retire 1 814 fraudes de l'entrainement (3 193 au lieu de 5 007) et met la validation (periode chargee) et le test (periode calme) dans deux regimes differents. Le 70/15/15 par heures ne change presque rien : l'ecart vient des deux regimes de PaySim, pas des proportions choisies. On garde donc le decoupage par heures comme reference. Ces lignes sont un diagnostic, aucun modele n'est evalue dessus.

## 6. Ce qu'on applique pour la suite

1. Taux de fraude de la partition et ratio AP / taux affiches a cote de chaque AP.
2. AP et Precision@K calcules jour par jour sur le test, pour verifier qu'un resultat ne vient pas de quelques jours atypiques.
3. Resultat principal avec le jour 31, resultat diagnostique sans.
4. Les memes transactions de test pour les trois modeles.
