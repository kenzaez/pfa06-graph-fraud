# Reponse a l'expertise du 17 novembre 2026

Legende : fait = dans le depot ; a executer = le code est pret, il faut lancer `notebooks/04_e0_rejeu_diagnostics.ipynb` ; a faire = prevu plus tard.

| Remarque du rapport | Reponse | Etat |
|---------------------|---------|------|
| Fausses alertes sous estimees (762 sur 1 247 = 61,1 %) | Corrige dans la note de lecture, le generateur de la note S3 (`src/rapport_s3.py`) et l'erratum | fait |
| Regle de depart des egalites, valeurs non arrondies, convention d'arret anticipe | Regle ecrite (fiche v2), valeurs non arrondies dans les CSV de selection, convention `aucpr` contre AP de scikit-learn precisee | fait |
| Tailles de la regression logistique | Bug du code (taille XGBoost recopiee), corrige, taille mesuree sur un fichier joblib | a executer |
| Note principale et annexe pas dans le meme etat | Note de lecture qui dit ce qui remplace quoi | fait |
| Concordance produite par l'equipe, pas verification independante | Distingue dans la note de lecture. Manifeste avec versions, empreinte des donnees et empreintes des sorties | a executer |
| Raccourci propre a PaySim (scenario A) | A qualifie de diagnostic, B reference. Ablation controlee : type et montant, puis solde, puis derives, meme echantillon, meme graine, meme modele, sans recherche d'hyperparametres | a executer |
| Reemploi adaptatif du test | Registre de consultation, E1 et E2 geles sur la validation, comparaison declaree exploratoire si un choix change | fait |
| Fuite dans l'historique du graphe | Regles et cinq tests de causalite ecrits, a coder avant E1 | a faire (debut S4) |
| Budget retrospectif contre alerte immediate | Deux politiques separees (fiche v2). Politique en flux a evaluer en S5 | fait pour le texte, a faire pour la politique en flux |
| Derive de prevalence, jour 31, jours partiels | Jours 25 et 31 marques partiels, jour 31 sans negatif, top K avec k_d = min(K, n_d), AP sans chaque jour | a executer |
| Historique trop pauvre | Mesure du voisinage disponible et reference pour les comptes sans historique prevues dans le registre | a faire (S4) |
| Brier et calibration | Phrase non demontree retiree. Score moyen contre taux observe par modele et partition | a executer |
| Predictions E0 indexees pour rejouer | `predictions_*.csv.gz` avec idx, step, jour, partition, y, scores des deux modeles. Rejeu independant et comparaison des AP | a executer |
| Le depot n'a pas pu etre consulte | Verifier que le depot est public ou inviter le Pr. MESTARI | a faire |
