# Benchmark & Suivi des Versions (Groupe C)

Outil autonome pour comparer les algorithmes de `src/Scripts/` sans modifier `StudentCode.py`.

## Utilisation rapide

Depuis la racine du projet (ou depuis `src/benchmark/`) :

```bash
# 1. Lancer le benchmark (détecte automatiquement les algos de Scripts/)
python3 src/benchmark/benchmark.py --note "description de votre test"

# 2. Ouvrir le dashboard HTML dans le navigateur (Mac)
open src/benchmark/benchmark_report.html
```

## Options utiles

- `--instances 1 2 3 4` : choisir les instances à tester (défaut : `1 2 3 4`).
- `--algos genetique memetique` : tester uniquement certains algos.
- `--runs 3` : nombre de répétitions par couple `(algo, instance)`.
- `--save-txt` : met à jour les fichiers officiels dans `src/solutions/GroupeC_Challenge_X.txt` si un record est battu.
- `--report-only` : régénère uniquement `benchmark_report.html` depuis tous les CSV du dossier `runs/` sans relancer les calculs.

## Fonctionnement en équipe (zéro conflit Git)

- Chaque lancement crée son propre fichier dans `src/benchmark/runs/` (ex. `2026-11-27_14h52m00_Baptiste.csv`).
- Quand vous mergez une branche dans `main`, les fichiers `runs/*.csv` s'additionnent sans conflit.
- Le dashboard `benchmark_report.html` lit automatiquement tout le dossier `runs/` + `src/solutions/` et affiche par défaut la **vue consolidée** (dernier résultat connu de chaque algo).

## Ajouter un nouvel algorithme

Déposez simplement votre fichier dans `src/Scripts/mon_algo.py` avec une fonction :
```python
def main(inst=None, func_fitness=None, nb_q=None, nb_phys=None):
    ...
    return nom_affiche, best_mapping, best_cost, duree, nb_evals
```
Il sera détecté automatiquement au prochain lancement.
