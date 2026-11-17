# Donnees

Le CSV PaySim n'est pas versionne (environ 470 Mo).

Source : Kaggle, jeu "Synthetic Financial Datasets For Fraud Detection" (`ealaxi/paysim1`).

```
kaggle datasets download -d ealaxi/paysim1 -p data
unzip -o data/paysim1.zip -d data
```

Fichier attendu : `data/PS_20174392719_1491204439457_log.csv`

Empreinte SHA256 attendue :

```
16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b
```

`src/audit.py` recalcule l'empreinte et `src/concordance.py` la compare automatiquement a cette valeur.
