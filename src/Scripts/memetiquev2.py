import random
import time
from source import instance_selector

# 1. Paramètres de l'Algorithme Mémétique Auto-Adaptatif (v2 optimisée)
nom = "Memetique Auto-Adaptatif"
nom_groupe = "GroupeC"
pop_size = 25           # Taille de la population
nb_generations = 55     # Réduit à 55 grâce au démarrage topologique rapide
prob_mutation = 0.35    # Taux de mutation de base (phase d'intensification)
elitisme = 2            # Nombre des meilleurs individus conservés intacts

# Paramètres mémétiques recalibrés pour un budget Qiskit optimal
nb_eduques = 2          # On éduque les 2 meilleurs enfants par génération
max_voisins = 6         # 6 voisins explorés lors d'une recherche locale

# Paramètres du Bandit Manchot (epsilon-greedy)
scores_bras = [0.5, 0.5]  # [Score mutation interne, Score mutation externe]
epsilon = 0.20            # 20 % d'exploration, 80 % d'exploitation

# Dictionnaire de cache (mémoïsation) associant chaque permutation déjà testée à son coût
memo_fitness = {}


def evaluer(mapping):
    cle = tuple(mapping)
    if cle not in memo_fitness:
        memo_fitness[cle] = fitness(mapping)
    return memo_fitness[cle]


def creer_individu():
    return random.sample(range(m), n)


def creer_individu_topologique(bruit=False):
    """Place les qubits virtuels les plus actifs sur les qubits physiques les plus centraux (hubs)."""
    degres_virtuels = [0] * n
    for inst in circuit.data:
        if len(inst.qubits) == 2:
            for q in inst.qubits:
                idx = circuit.find_bit(q).index
                degres_virtuels[idx] += 1

    degres_physiques = [0] * m
    for u, v in backend.coupling_map.get_edges():
        degres_physiques[u] += 1
        degres_physiques[v] += 1

    if bruit:
        degres_virtuels = [d + random.uniform(-1.5, 1.5) for d in degres_virtuels]

    ordre_virtuel = sorted(range(n), key=lambda i: degres_virtuels[i], reverse=True)
    ordre_physique = sorted(range(m), key=lambda i: degres_physiques[i], reverse=True)

    mapping = [0] * n
    for k in range(n):
        mapping[ordre_virtuel[k]] = ordre_physique[k]
    return mapping


def selection_tournoi(population, scores, k=3):
    indices = random.sample(range(len(population)), k)
    meilleur_idx = min(indices, key=lambda i: scores[i])
    return population[meilleur_idx][:]


def croisement_ox(parent1, parent2):
    if n < 2:
        return parent1[:]

    a, b = sorted(random.sample(range(n + 1), 2))
    enfant = [None] * n
    enfant[a:b] = parent1[a:b]
    deja_presents = set(parent1[a:b])

    idx_enfant = 0
    for gene in parent2:
        if gene not in deja_presents:
            while idx_enfant < n and enfant[idx_enfant] is not None:
                idx_enfant += 1
            if idx_enfant < n:
                enfant[idx_enfant] = gene
                deja_presents.add(gene)

    if None in enfant:
        libres = [q for q in range(m) if q not in deja_presents]
        random.shuffle(libres)
        for i in range(n):
            if enfant[i] is None:
                enfant[i] = libres.pop()

    return enfant


def mutation(individu):
    mutant = individu[:]

    # Sélection du bras par règle epsilon-greedy (0 = interne, 1 = externe)
    if n == m:
        bras = 0
    elif random.random() < epsilon:
        bras = random.choice([0, 1])
    else:
        bras = 0 if scores_bras[0] >= scores_bras[1] else 1

    if bras == 0:
        # Mutation interne (intensification) : échange deux qubits physiques actifs
        if n >= 2:
            i, j = random.sample(range(n), 2)
            mutant[i], mutant[j] = mutant[j], mutant[i]
    else:
        # Mutation externe (diversification) : remplace un qubit par un qubit libre
        utilises = set(mutant)
        libres = [q for q in range(m) if q not in utilises]
        if libres:
            idx = random.randrange(n)
            mutant[idx] = random.choice(libres)

    return mutant, bras


def recherche_locale(individu, cout_actuel, max_essais=max_voisins):
    courant = individu[:]
    meilleur_cout = cout_actuel

    for _ in range(max_essais):
        voisin, bras = mutation(courant)
        cout_voisin = evaluer(voisin)

        if cout_voisin < meilleur_cout:
            courant = voisin
            meilleur_cout = cout_voisin
            recompense = 1.0
        else:
            recompense = 0.0

        # Mise à jour en ligne du score du bras utilisé
        if n < m:
            scores_bras[bras] += 0.1 * (recompense - scores_bras[bras])

    return courant, meilleur_cout


def main(inst=None, func_fitness=None, nb_q=None, nb_phys=None):
    global fitness, n, m, instance_num, circuit, backend, prob_mutation
    if func_fitness is not None:
        instance_num, fitness, n, m = inst, func_fitness, nb_q, nb_phys
        backend, circuit, _, _ = instance_selector(inst)
    else:
        from __main__ import fitness, n, m, instance_num, circuit, backend

    memo_fitness.clear()
    scores_bras[:] = [0.5, 0.5]
    prob_mutation = 0.35

    debut = time.time()

    # Génération 0 : 2 individus topologiques + (pop_size - 2) aléatoires
    population = [creer_individu() for _ in range(pop_size)]
    population[0] = creer_individu_topologique(bruit=False)
    population[1] = creer_individu_topologique(bruit=True)

    scores = [evaluer(ind) for ind in population]
    population_triee = [ind for _, ind in sorted(zip(scores, population), key=lambda x: x[0])]
    scores_tries = sorted(scores)

    for i in range(nb_eduques):
        ind_ameliore, score_ameliore = recherche_locale(population_triee[i], scores_tries[i], max_voisins)
        population_triee[i] = ind_ameliore
        scores_tries[i] = score_ameliore

    population = population_triee
    scores = scores_tries

    best_mapping = population[0][:]
    best_cost = scores[0]
    print(f"Génération 0 | Meilleur coût : {best_cost}")

    prob_mutation_base = 0.35
    stagnation = 0
    seuil_stagnation = 8

    for gen in range(1, nb_generations + 1):
        population_triee = [ind for _, ind in sorted(zip(scores, population), key=lambda x: x[0])]
        scores_tries = sorted(scores)

        if scores_tries[0] < best_cost:
            stagnation = 0
            prob_mutation = prob_mutation_base
            best_cost = scores_tries[0]
            best_mapping = population_triee[0][:]
            print(f"Génération {gen} | Nouveau meilleur coût : {best_cost} ({time.time() - debut:.1f}s)")
        else:
            stagnation += 1
            if stagnation == seuil_stagnation:
                prob_mutation = 0.50
            elif stagnation >= seuil_stagnation + 5:
                # Fin de l'impulsion de réchauffage : on revient à la normale pour économiser Qiskit
                prob_mutation = prob_mutation_base
                stagnation = 0

        nouvelle_population = [ind[:] for ind in population_triee[:elitisme]]
        nouveaux_scores = scores_tries[:elitisme]

        enfants = []
        while len(enfants) < pop_size - elitisme:
            p1 = selection_tournoi(population, scores)
            p2 = selection_tournoi(population, scores)
            enfant = croisement_ox(p1, p2)
            if random.random() < prob_mutation:
                enfant, _ = mutation(enfant)
            enfants.append(enfant)

        scores_enfants = [evaluer(enf) for enf in enfants]
        enfants_tries = [enf for _, enf in sorted(zip(scores_enfants, enfants), key=lambda x: x[0])]
        scores_enfants_tries = sorted(scores_enfants)

        for i in range(len(enfants_tries)):
            if i < nb_eduques:
                enf_educated, score_educated = recherche_locale(
                    enfants_tries[i], scores_enfants_tries[i], max_voisins
                )
                nouvelle_population.append(enf_educated)
                nouveaux_scores.append(score_educated)
            else:
                nouvelle_population.append(enfants_tries[i])
                nouveaux_scores.append(scores_enfants_tries[i])

        population = nouvelle_population
        scores = nouveaux_scores

    # Vérification finale sur la dernière génération
    for ind, sc in zip(population, scores):
        if sc < best_cost:
            best_cost = sc
            best_mapping = ind[:]

    # Polissage final sur le champion global
    best_mapping, best_cost = recherche_locale(best_mapping, best_cost, max_essais=20)

    duree = time.time() - debut
    print(f"Scores bandit finaux (Interne / Externe) : {scores_bras[0]:.2f} / {scores_bras[1]:.2f}")

    return nom, best_mapping, best_cost, duree, len(memo_fitness)