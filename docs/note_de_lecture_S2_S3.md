# Note de lecture : note principale (31 pages) et annexe S2 et S3

La note de 53 pages garde le texte de 31 pages tel quel et ajoute l'annexe S2 et S3. Quand les deux disent des choses differentes, c'est l'annexe, corrigee par cette note, qui fait foi.

| Passage de la note principale | Etat actuel | Ou le trouver |
|-------------------------------|-------------|----------------|
| Resume, abstract, chapitre 1 : "aucun modele n'est encore entraine", E0 "prevu" | Remplace : E0 est entraine, scenario B de reference | Annexe, partie B |
| "Le test n'a jamais ete consulte" ou equivalent | Faux pour E0 depuis S3 : le test a ete consulte, voir le registre | `docs/registre_evaluation.md` |
| Partitions, jour 31, budget K = 100, 250, 500 par jour | Inchanges, precises : k_d = min(K, n_d), jours 25 et 31 partiels, deux politiques distinctes | Fiche protocole version 2 |
| Audit, 48 indicateurs concordants | Preuve produite par l'equipe, rejouable avec le manifeste. La verification independante par un tiers reste a faire | `reports/manifest_e0.json`, `reports/tables/concordance.csv` |
| Scenario A (avec solde) | Diagnostic de sensibilite aux entrees uniquement | Annexe, partie B ; ablation controlee dans le notebook 04 |

## Corrections de l'annexe

1. Fausses alertes de XGBoost B au seuil gele : 762 fausses alertes sur 1 247, soit 61,1 %, et non "la moitie environ". Rappel 485 sur 1 654, soit 29,3 %. Precision 38,9 %.
2. Calibration : le Brier (0,0256 pour XGBoost B contre 0,2112 pour la regression logistique B) mesure l'erreur quadratique, il ne donne pas le sens du biais. La phrase "ils surestiment le risque" n'est pas demontree. Le sens du biais se lit dans `reports/e0/calibration_resume.csv` (score moyen contre taux observe).
3. Tailles de modele : les tableaux 16 et 29 donnaient a la regression logistique la taille du fichier XGBoost (erreur de code, corrigee dans `src/e0.py`). Les vraies tailles viennent d'un fichier joblib mesure apres le notebook 04.
4. Seuil gele et top K par jour : deux politiques differentes. Au seuil gele de 0,0470, XGBoost B emet 1 247 alertes sur le test (precision 38,9 %, rappel 29,3 %). Pour le top 250 quotidien, precision 42,5 % et rappel 44,9 %. Un seuil regle pour environ 250 alertes par jour sur la validation ne garantit pas ce volume sur le test.
5. AP et hasard : sous un score constant, l'AP de scikit-learn est egale a la prevalence. Pour un classement aleatoire, l'AP vaut en moyenne a peu pres la prevalence, pas exactement.
6. Jours du test : le test couvre les jours 25 a 31. Le jour 25 est partiel (steps 595 a 600) et le jour 31 est partiel et ne contient que 272 fraudes, sans negatif.
7. Choix des hyperparametres, scenario A : 12 reglages ont la meme AP de validation a quatre decimales (1,0000). Deux sont exactement a 1,0 (profondeur 6 et profondeur 8, taux 0,1, 66 arbres). Le reglage retenu est le premier de la grille a egalite exacte (profondeur 6). Les valeurs non arrondies sont dans `reports/e0/selection_A_population_principale.csv`.
8. Arret anticipe : critere `aucpr` de XGBoost. Les AP publiees et la selection utilisent `average_precision_score` de scikit-learn.
