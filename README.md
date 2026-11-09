# Projet Graphes et Optimisation Combinatoire — Qubit Allocation Problem

> **Auteur :** Jérôme Rouzé  
> **Faculté polytechnique de Mons — Université de Mons**  
> **Année :** GOC 2026

---

## 1. Présentation du problème

### 1.1 Formulation abstraite : problème de permutation partielle

Soient `n` et `m` deux entiers naturels non nuls tels que `n ≤ m`. On cherche le
**meilleur arrangement** de `n` éléments parmi `m`.

- **But du projet :** mettre en place un algorithme d'optimisation pour minimiser
  une fonction objectif « *black box* ».
- **La fonction objectif :** prend en entrée une **liste ordonnée** de `n` entiers
  deux à deux distincts dans `{0, ..., m-1}` et renvoie un coût.

#### Exemple

Avec `m = 5` et `n = 3` :

| Liste          | Admissible ? |
| -------------- | ------------ |
| `[0, 3, 1]`    | ✅ Oui       |
| `[1, 0, 3]`    | ✅ Oui       |
| `[0, 3, 3]`    | ❌ Non (doublons) |
| `[0, 3]`       | ❌ Non (taille incorrecte) |
| `[0, 3, 1, 4]` | ❌ Non (taille incorrecte) |

> **Remarque :** les instances du problème et la fonction objectif sont fournies.

### 1.2 Application : association de graphes

Le but est d'associer les sommets d'un **graphe orange** (les qubits virtuels) à
ceux d'un **graphe bleu** (les qubits physiques) en préservant au mieux les arêtes
oranges.

- Association `A→1 ; B→0 ; C→2` : aucun changement (**association parfaite**)
- Association `A→0 ; B→1 ; C→2` : plusieurs changements (**association imparfaite**)

Lorsqu'aucune association parfaite n'existe, on cherche l'association qui minimise
les changements. On attribue un coût à chaque changement et on minimise le coût
cumulé.

---

## 2. Contexte quantique

### 2.1 Qu'est-ce qu'un qubit ?

- **La superposition :**
  - Informatique classique : un bit vaut `0` ou `1` ; deux bits : `00`, `01`, `10`, `11`.
  - Informatique quantique : un qubit vaut `α|0⟩ + β|1⟩`, où `α, β ∈ ℂ` tels que
    `|α|² + |β|² = 1`.
  - Deux qubits : `α|00⟩ + β|01⟩ + γ|10⟩ + δ|11⟩`.

- **L'intrication (entanglement) :** un état qui n'est pas le produit tensoriel de
  deux états. Exemple, l'état de Bell :
  `(1/√2)|00⟩ + (1/√2)|11⟩`.

### 2.2 Modèle à portes (gates-based model)

Un programme (circuit) quantique est une suite de portes quantiques.

- **Porte H (Hadamard) :** crée la superposition `(1/√2)|0⟩ + (1/√2)|1⟩`.
- **Porte CNOT (Controlled NOT) :** applique NOT à la cible si le contrôle est en
  `|1⟩`, et ne fait rien sinon. Elle crée de l'intrication.

### 2.3 Lien avec l'association de graphes

D'un circuit quantique, on tire un **graphe orange** (connectivité des qubits
virtuels) à associer au **graphe bleu** (connexions entre les qubits physiques d'un
ordinateur quantique).

Le coût des changements correspond aux portes quantiques à **ajouter** au circuit
pour l'exécuter malgré une association imparfaite. On parle de *« routing »* du
circuit.

#### Exemple

- **Association `[0, 1, 2]` imparfaite :** longueur `= 6` (longueur d'un swap `= 3`).
- **Association `[1, 0, 2]` parfaite :** longueur `= 3`, solution **optimale**.

### 2.4 Différence avec l'association de graphes

Prenons un circuit où la connexion `0–1` apparaît deux fois et la connexion `0–2`
une seule fois. Le problème n'est **pas** l'association d'un graphe pondéré : les
deux connexions `0–1` ne sont pas nécessairement présentes *en même temps* dans le
circuit. Il est donc possible de casser la seconde connexion `0–1` pour la
reconstruire ensuite.

> **« Association de graphes » et « Qubit Allocation Problem » sont donc similaires
> mais différents.**

---

## 3. Utilisation du projet

### 3.1 Fichiers fournis

| Fichier | Rôle |
| ------- | ---- |
| [`src/StudentCode.py`](src/StudentCode.py) | Code étudiant : c'est ici qu'on implémente la métaheuristique. |
| [`src/source.py`](src/source.py) | Fournit la fonction objectif et les utilitaires de chargement. **Ne pas modifier.** |
| [`src/Instances/`](src/Instances) | Dossier contenant les instances `Instance_1.qasm` à `Instance_9.qasm`. |

### 3.2 Installation

Installer la librairie **Qiskit** avec la commande suivante :

```bash
pip install qiskit==1.2.4
```

> ⚠️ **La version `1.2.4` est importante, ne pas en changer !**

### 3.3 Choix de l'instance

Le choix de l'instance se fait en donnant son numéro à la fonction
`instance_selector`, via la variable `instance_num` dans
[`src/StudentCode.py`](src/StudentCode.py:23).

```python
instance_num = 1     #### Entre 1 et 9 inclue
backend, circuit, n, m = instance_selector(instance_num)
```

- La fonction objectif calcule les changements nécessaires et renvoie le **coût**.
- Elle prend en entrée une liste ordonnée de `n` entiers parmi `{0, ..., m-1}`.
- Les variables `n` et `m` sont chargées automatiquement au choix de l'instance.
- **Ne rien modifier au-dessus de l'espace « A vous de jouer ! ».**

### 3.4 Fonction objectif

La fonction [`fitness()`](src/StudentCode.py:13) enveloppe `fitness_inner` fournie
par [`src/source.py`](src/source.py:125) :

```python
def fitness(mapping):
    return fitness_inner(mapping, circuit, backend)
```

Elle accepte une liste de `n` entiers deux à deux distincts parmi `m` et renvoie la
profondeur du circuit routé (`QC.depth()`), à minimiser.

---

## 4. Rendu attendu

À la fin de l'exécution de la métaheuristique, il faut **écrire l'association puis
son coût** dans un fichier nommé :

```
[GROUPE]_Challenge_[instance_number].txt
```

#### Exemple

Le groupe 18 trouve que la solution `[1, 0, 2]` a pour coût `53` pour l'instance
Challenge 0. Il rend alors un fichier `Groupe18_Challenge_0.txt` contenant
**exactement** :

```
1 0 2 53
```

---

## 5. Les instances

Les instances se trouvent dans le dossier [`src/Instances/`](src/Instances), à
placer dans le même répertoire que [`src/StudentCode.py`](src/StudentCode.py) et
[`src/source.py`](src/source.py).

[`src/StudentCode.py`](src/StudentCode.py:45) contient un test pour s'assurer que
tout est correctement installé.

### Meilleures solutions connues

| Instance | n  | m  | Coût de la meilleure solution connue |
| -------- | -- | -- | ------------------------------------ |
| 1        | 12 | 16 | 50                                   |
| 2        | 16 | 16 | 59*                                  |
| 3        | 10 | 16 | 108                                  |
| 4        | 19 | 20 | 35                                   |
| 5        | 12 | 20 | 323                                  |
| 6        | 14 | 20 | 25                                   |
| 7        | 20 | 27 | 22*                                  |
| 8        | 20 | 27 | 17                                   |
| 9        | 25 | 27 | 51                                   |

> `*` : solution exacte.

---

## 6. Notes techniques

- La ligne 122 de [`src/source.py`](src/source.py:116) contient un chemin vers les
  fichiers `.qasm` :
  ```python
  qasmfile = f".\Instances\{l.rstrip()}.qasm"
  ```
  Ce chemin peut poser problème à l'exécution, en particulier sous Linux. Le
  remplacer par `qasmfile = f"./Instances/{l.rstrip()}.qasm"` devrait résoudre le
  problème.

- [`src/source.py`](src/source.py) ne doit **pas** être modifié : toute modification
  pourrait entraîner des bugs ou des changements indésirables des instances.
