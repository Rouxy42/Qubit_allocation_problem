# -*- coding: utf-8 -*-
"""
Colonie de fourmis (ACO) pour le problème d'allocation de qubits.

Version intuitive, sans recherche locale et sans apprentissage
d'hyperparamètres : les valeurs ci-dessous sont des valeurs de départ
raisonnables et pourront être tunées plus tard.

Le principe :
  - Chaque fourmi construit un mapping admissible en choisissant, pour
    chaque qubit virtuel i (position i), un qubit physique j encore libre.
  - Le choix est guidé par :
      * tau[i][j] : la phéromone (mémoire collective),
      * eta[i][j] : une heuristique basée sur les interactions du circuit
        et la distance entre qubits physiques sur le backend.
  - Les phéromones s'évaporent puis sont renforcées par les meilleures
    solutions (coût faible => dépôt fort, car on minimise la profondeur).
"""

import random
import time

# ----------------------------------------------------------------------
# 1. Paramètres de l'ACO (valeurs intuitives de départ, à tuner plus tard)
# ----------------------------------------------------------------------
nom = "Algo ACO"
nom_groupe = "GroupeC"      # Utilisé pour nommer le fichier de sortie
nb_fourmis = 15             # Nombre de fourmis à chaque itération
nb_iterations = 60          # Nombre d'itérations de la colonie
alpha = 1.0                 # Poids de la phéromone
beta = 2.0                  # Poids de l'heuristique
rho = 0.10                  # Taux d'évaporation (0 < rho < 1)
tau0 = 1.0                  # Phéromone initiale sur chaque arc (i, j)
q_depot = 10.0              # Intensité du dépôt de phéromone
elitiste = True             # Déposer un bonus pour la meilleure solution globale
facteur_elite = 2.0         # Multiplicateur du dépôt pour la solution élite


# Dictionnaire de cache (mémoïsation) : évite de rappeler Qiskit pour une
# permutation déjà évaluée par une autre fourmi ou une autre itération.
memo_fitness = {}


def evaluer(mapping):
    """Évalue un mapping en passant par le cache Qiskit."""
    cle = tuple(mapping)
    if cle not in memo_fitness:
        memo_fitness[cle] = fitness(mapping)
    return memo_fitness[cle]


def _aretes_couplage(backend, m):
    """Extrait les arêtes du graphe de couplage du backend.

    On essaie d'abord `backend.target.build_coupling_map()` (fonctionne pour
    les backends convertis en BackendV2), puis `backend.coupling_map`.
    En dernier recours on retombe sur une grille linéaire 0-1-...-m-1.
    """
    try:
        cm = backend.target.build_coupling_map()
        aretes = list(cm.get_edges())
        if aretes:
            return aretes
    except Exception:
        pass

    try:
        cm = backend.coupling_map
        aretes = list(cm.get_edges())
        if aretes:
            return aretes
    except Exception:
        pass

    return [(i, i + 1) for i in range(m - 1)]


def _distances(m, aretes):
    """Renvoie la matrice des plus courtes distances entre qubits physiques.

    Le backend ne dépasse pas quelques dizaines de qubits, un simple BFS par
    sommet est largement suffisant et se calcule une seule fois.
    """
    adj = [[] for _ in range(m)]
    for a, b in aretes:
        if 0 <= a < m and 0 <= b < m:
            adj[a].append(b)
            adj[b].append(a)

    dist = [[10**9] * m for _ in range(m)]
    for depart in range(m):
        dist[depart][depart] = 0
        file = [depart]
        tete = 0
        while tete < len(file):
            u = file[tete]
            tete += 1
            for v in adj[u]:
                if dist[depart][v] == 10**9:
                    dist[depart][v] = dist[depart][u] + 1
                    file.append(v)
    return dist


def _interactions(circuit, n):
    """Compte les interactions à 2 qubits entre chaque paire de qubits virtuels.

    Plus deux qubits virtuels partagent de portes à 2 qubits (CNOT, etc.),
    plus ils devraient être placés proches sur la puce physique.
    """
    interactions = [[0] * n for _ in range(n)]
    for instruction in circuit.data:
        qubits = getattr(instruction, "qubits", ())
        if len(qubits) != 2:
            continue
        try:
            a = circuit.find_bit(qubits[0]).index
            b = circuit.find_bit(qubits[1]).index
        except Exception:
            continue
        if 0 <= a < n and 0 <= b < n:
            interactions[a][b] += 1
            interactions[b][a] += 1
    return interactions


def _choisir(poids, candidats):
    """Tirage à la roulette biaisée selon les poids fournis."""
    total = sum(poids)
    if total <= 0:
        return random.choice(candidats)

    r = random.random() * total
    cumul = 0.0
    for idx, j in enumerate(candidats):
        cumul += poids[idx]
        if r <= cumul:
            return j
    return candidats[-1]


def _construire_mapping(tau, interactions, dist):
    """Construit un mapping admissible (permutation partielle) pour une fourmi.

    Pour le qubit virtuel i, la probabilité de choisir le qubit physique j
    est proportionnelle à :
        tau[i][j]^alpha * eta[i][j]^beta

    eta[i][j] = 1 / (1 + somme_des_pénalités)
    où chaque qubit virtuel k déjà placé sur le qubit physique p ajoute :
        interactions[i][k] / (1 + distance(j, p))

    Ainsi, un qubit virtuel fortement lié à un qubit déjà placé est attiré
    vers les qubits physiques proches de celui-ci.
    """
    mapping = []
    candidats = list(range(m))

    # acc[i][j] = pénalité accumulée pour placer i sur j, au vu des choix
    # déjà faits. eta[i][j] en découle directement.
    acc = [[0.0] * m for _ in range(n)]

    for i in range(n):
        # Calcule les poids de sélection pour le qubit virtuel courant i.
        poids = []
        for j in candidats:
            eta = 1.0 / (1.0 + acc[i][j])
            poids.append((tau[i][j] ** alpha) * (eta ** beta))

        # Choisit un qubit physique parmi ceux encore libres.
        choisi = _choisir(poids, candidats)
        mapping.append(choisi)
        candidats.remove(choisi)

        # Met à jour l'heuristique pour les qubits virtuels restants.
        for i2 in range(i + 1, n):
            poids_lien = interactions[i2][i]
            if poids_lien == 0:
                continue
            for j in candidats:
                # Distance physique entre le candidat j et le qubit choisi.
                d = dist[j][choisi]
                acc[i2][j] += poids_lien / (1.0 + d)

    return mapping


def main(inst=None, func_fitness=None, nb_q=None, nb_phys=None):
    global fitness, n, m, instance_num
    if func_fitness is not None:
        instance_num, fitness, n, m = inst, func_fitness, nb_q, nb_phys
    else:
        from __main__ import fitness, n, m, instance_num

    try:
        from __main__ import circuit, backend
    except ImportError:
        circuit = None
        backend = None

    memo_fitness.clear()

    # 2. Initialisation des données du problème
    debut = time.time()

    if circuit is not None and backend is not None:
        aretes = _aretes_couplage(backend, m)
        dist = _distances(m, aretes)
        interactions = _interactions(circuit, n)
    else:
        # Repli purement aléatoire/heuristique neutre si le contexte manque.
        dist = [[0 if a == b else 1 for b in range(m)] for a in range(m)]
        interactions = [[0] * n for _ in range(n)]

    # Matrice de phéromones tau[i][j] : attraction (qubit virtuel i, physique j).
    tau = [[tau0] * m for _ in range(n)]

    # Meilleure solution globale trouvée jusqu'ici.
    best_mapping = None
    best_cost = float("inf")

    # 3. Boucle principale de la colonie
    for iteration in range(1, nb_iterations + 1):
        solutions = []
        couts = []

        # Chaque fourmi construit puis évalue sa solution.
        for _ in range(nb_fourmis):
            mapping = _construire_mapping(tau, interactions, dist)
            cout = evaluer(mapping)
            solutions.append(mapping)
            couts.append(cout)

            if cout < best_cost:
                best_cost = cout
                best_mapping = mapping[:]

        # Évaporation des phéromones sur tous les arcs.
        for i in range(n):
            for j in range(m):
                tau[i][j] *= (1.0 - rho)

        # Dépôt de phéromone par les fourmis, proportionnel à 1/coût.
        for mapping, cout in zip(solutions, couts):
            if cout == 0:
                continue
            delta = q_depot / cout
            for i, j in enumerate(mapping):
                tau[i][j] += delta

        # Bonus élitiste : renforce la meilleure solution globale.
        if elitiste and best_mapping is not None and best_cost > 0:
            delta_elite = facteur_elite * q_depot / best_cost
            for i, j in enumerate(best_mapping):
                tau[i][j] += delta_elite

        print(
            f"Itération {iteration}/{nb_iterations} | "
            f"Meilleur coût : {best_cost} ({time.time() - debut:.1f}s)"
        )

    # 4. Bilan final
    duree = time.time() - debut
    nb_evals = len(memo_fitness)

    print(f"Évaluations Qiskit réelles : {nb_evals}")
    print(f"Meilleure association : {best_mapping}")
    print(f"Coût final : {best_cost}")

    return nom, best_mapping, best_cost, duree, nb_evals
