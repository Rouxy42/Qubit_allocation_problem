# Architecture du Benchmark & Suivi Collaboratif — Qubit Allocation Problem

Outil autonome pour comparer les algorithmes de `src/Scripts/` sans jamais modifier `StudentCode.py` ni les scripts d'algorithmes eux-mêmes.

---

## Démarrage rapide

Depuis la **racine du projet** :

```bash
# Lancer tous les algos détectés
python3 src/benchmark/benchmark.py --note "description de votre test"

# Ouvrir le dashboard (macOS)
open src/benchmark/benchmark_report.html
```

> [!IMPORTANT]
> Le fichier `benchmark_report.html` n'est **pas** versionné (`.gitignore`).
> Après un `git pull`, régénérez-le avec `python3 src/benchmark/benchmark.py --report-only`.

---

## Options CLI

| Option | Description | Défaut |
| :--- | :--- | :--- |
| `--note "..."` | Label libre pour identifier le run dans le dashboard | `""` |
| `--algos aco` | Restreindre aux algos listés | tous les algos détectés |
| `--instances 1 2 3 4` | Choisir les instances à tester | `[1, 2, 3, 4]` |
| `--runs 3` | Répétitions par couple `(algo, instance)` | `3` |
| `--save-txt` | Met à jour `solutions/GroupeC_Challenge_X.txt` si record battu | désactivé |
| `--report-only` | Régénère uniquement le HTML sans relancer les algos | — |

---

## Arborescence

```text
src/
├── Instances/                     # Circuits QASM (Instance_1.qasm .. Instance_9.qasm)
├── source.py                      # instance_selector() et fitness_inner() — NE PAS MODIFIER
├── StudentCode.py                 # Point d'entrée individuel — NE PAS MODIFIER
│
├── Scripts/                       # Algorithmes d'optimisation
│   ├── __init__.py                # Découvre et importe automatiquement chaque module .py
│   ├── example.py                 # Template ignoré par le benchmark
│   ├── genetique.py
│   ├── memetique.py
│   ├── aco.py
│   └── ...                        # Tout futur script ajouté ici est détecté automatiquement
│
├── solutions/                     # Records officiels pour le rendu du challenge
│   └── GroupeC_Challenge_<X>.txt  # Mapping optimal + coût (mis à jour uniquement avec --save-txt)
│
└── benchmark/                     # Système de benchmark — seul dossier à modifier si besoin
    ├── README.md                  # Ce fichier
    ├── benchmark.py               # Orchestrateur : exécution, collecte, sauvegarde
    ├── report_generator.py        # Agrégateur des CSV + générateur du dashboard HTML
    ├── benchmark_report.html      # Dashboard interactif (non versionné, généré localement)
    └── runs/                      # Historique distribué (1 CSV = 1 lancement, tous versionnés)
        ├── 2026-11-27_11h56m28_initial.csv
        └── <date_heure>_<auteur>.csv
```

---

## Fonctionnement interne

### 1. Détection automatique des algorithmes

`benchmark.py` parcourt `Scripts._MODULES` (alimenté par `Scripts/__init__.py`) et retient tout module exposant une fonction `main()` callable, sauf ceux dans `ALGORITHMES_IGNORES` (`{"example"}`).

**Deux conventions d'appel sont supportées** (détectées via `inspect.signature`) :

```python
# Convention 1 — paramétrée (genetique.py, memetique.py, insulaire.py...)
def main(inst=None, func_fitness=None, nb_q=None, nb_phys=None):
    ...
    return nom_affiche, best_mapping, best_cost, duree, nb_evals

# Convention 2 — style StudentCode sans arguments (aco.py...)
def main():
    from __main__ import fitness, n, m, instance_num  # injecté par benchmark.py
    ...
    return nom_affiche, best_mapping, best_cost, duree, nb_evals
```

> [!NOTE]
> `benchmark.py` injecte automatiquement `instance_num`, `backend`, `circuit`, `n`, `m` et `fitness` dans `sys.modules["__main__"]` avant chaque appel, pour que les deux styles fonctionnent sans modification.

### 2. Métriques collectées par couple `(algo, instance)`

| Champ | Description |
| :--- | :--- |
| `cout_min` | Meilleur coût parmi les `NB_RUNS` répétitions |
| `cout_moy` | Moyenne des coûts |
| `cout_max` | Pire coût |
| `cout_std` | Écart-type (stabilité de l'algo) |
| `temps_moy / min / max` | Temps d'exécution |
| `evals_moy` | Appels réels à Qiskit |
| `meilleur_mapping` | Permutation physique → virtuelle optimale |

### 3. Sauvegarde incrémentale

Dès qu'un couple `(algo, instance)` se termine :
1. La ligne est ajoutée au CSV du run dans `runs/`.
2. `benchmark_report.html` est régénéré (écriture atomique via fichier `.tmp`).

En cas d'interruption (`Ctrl+C`), les résultats déjà calculés sont conservés.

---

## Stockage distribué dans `runs/` — pourquoi ?

Un seul CSV partagé créerait des **conflits Git** à chaque merge entre deux branches ayant lancé des benchmarks en parallèle.

Avec un dossier `runs/` :
- Chaque exécution crée `<run_id>_<auteur>.csv` (ex. `2026-11-28_14h09m13_Babilou.csv`).
- Les CSV des coéquipiers **s'additionnent sans conflit** lors d'un merge.
- **Aucun run n'est jamais écrasé**.
- `report_generator.py` lit et trie chronologiquement **tous** les `*.csv` de `runs/`.

### Schéma des colonnes CSV

```
run_id, timestamp_iso, timestamp_label, auteur,
git_branch, git_commit, git_dirty, note, nb_runs,
instance, n, m, algo, nom_affiche,
cout_min, cout_moy, cout_max, cout_std,
temps_moy, temps_min, temps_max, evals_moy,
meilleur_mapping
```

> [!NOTE]
> `report_generator.py` utilise `.get(..., valeur_par_défaut)` pour chaque colonne : les anciens CSV (sans certaines colonnes) restent lisibles sans migration.

---

## Dashboard HTML (`benchmark_report.html`)

Généré localement, **non versionné**. Ouvrir directement dans le navigateur (`file://` suffit, pas de serveur nécessaire) car les données sont injectées en JSON dans le HTML au moment de la génération.

### Fonctionnalités

- **Vue consolidée par défaut** : pour chaque couple `(algo, instance)`, affiche le **dernier résultat connu** à travers tous les CSV de `runs/`. Un coéquipier qui ne lance que `aco` le voit immédiatement comparé à `genetique`, `memetique`, etc.
- **Comparaison Version vs Version** : choisir n'importe quel run en *Version analysée* et n'importe quel autre en *Baseline* — les graphiques affichent les deux séries et le tableau calcule les deltas.
- **Filtres dynamiques** : par algorithme et par instance.
- **Onglet Comparatif** : KPIs, graphiques Qualité/Temps/Évaluations Qiskit, scatter *Coût vs Temps*, tableau triable (clic sur une cellule mapping = copie dans le presse-papiers).
- **Onglet Évolution** : courbes chronologiques pour suivre la progression d'un algo commit après commit.
- **Onglet Records** : état des fichiers `solutions/*.txt` + journal de tous les runs.
- **Import CSV** : bouton pour charger manuellement un CSV externe dans l'interface.

---

## Workflow Git en équipe — zéro conflit

```
1. git pull origin main
   └── Récupère les Scripts/ des autres + leurs runs/*.csv

2. python3 src/benchmark/benchmark.py --algos mon_algo --note "test X"
   └── Crée runs/<date>_<auteur>.csv (unique, jamais en conflit)
   └── Régénère benchmark_report.html avec comparaison face à tous les autres

3. git add src/benchmark/runs/
   git commit -m "bench(mon_algo): résultats run X"
   git push origin ma_branche
   └── Merge dans main (PR ou direct)

4. Les autres font git pull → récupèrent le CSV → relancent --report-only
```

> [!CAUTION]
> `benchmark_report.html` peut avoir un conflit lors d'un merge (deux personnes l'ont régénéré en parallèle). La résolution prend 2 secondes :
> ```bash
> python3 src/benchmark/benchmark.py --report-only
> git add src/benchmark/benchmark_report.html
> git commit --no-edit
> ```

---

## Ajouter un nouvel algorithme

Déposez votre fichier dans `src/Scripts/mon_algo.py` avec une fonction `main` retournant :

```python
return nom_affiche, best_mapping, best_cost, duree, nb_evals
#        str           list[int]    float/int  float   int
```

Il sera **détecté automatiquement** au prochain lancement, qu'il utilise la convention avec ou sans arguments.

---

## Aide-mémoire rapide

```bash
# Tous les algos, toutes les instances, 3 runs
python3 src/benchmark/benchmark.py --note "run complet"

# Un algo précis, instances ciblées, 5 runs
python3 src/benchmark/benchmark.py --algos aco --instances 1 2 3 4 --runs 5 --note "tuning aco"

# Mettre à jour les fichiers de soumission si record battu
python3 src/benchmark/benchmark.py --save-txt --note "records finaux"

# Régénérer le HTML après un git pull (sans relancer les calculs)
python3 src/benchmark/benchmark.py --report-only

# Ouvrir le dashboard (macOS)
open src/benchmark/benchmark_report.html
```
