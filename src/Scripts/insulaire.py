import random
import time
from source import instance_selector

# 1. Paramètres du Modèle Insulaire à 2 Îles Mémétiques Auto-Adaptatives
nom = "Insulaire 2 Iles Memetique"
nom_groupe = "GroupeC"
nb_iles = 2
taille_ile = 12             # 2 x 12 = 24 individus au total (même budget que memetiquev2)
nb_generations = 60         # Nombre de générations d'évolution
freq_migration = 10         # Échange des champions toutes les 10 générations
nb_migrants = 1             # Nombre d'individus migrés par échange
elitisme = 2                # Nombre des meilleurs individus conservés par île

# Paramètres du Bandit Manchot (epsilon-greedy)
epsilon = 0.20

# Cache global partagé entre les 2 îles (zéro appel Qiskit redondant !)
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
    indices = random.sample(range(len(population)), min(k, len(population)))
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


def mutation(individu, scores_bras):
    mutant = individu[:]

    if n == m:
        bras = 0
    elif random.random() < epsilon:
        bras = random.choice([0, 1])
    else:
        bras = 0 if scores_bras[0] >= scores_bras[1] else 1

    if bras == 0:
        # Mutation interne (intensification)
        if n >= 2:
            i, j = random.sample(range(n), 2)
            mutant[i], mutant[j] = mutant[j], mutant[i]
    else:
        # Mutation externe (diversification)
        utilises = set(mutant)
        libres = [q for q in range(m) if q not in utilises]
        if libres:
            idx = random.randrange(n)
            mutant[idx] = random.choice(libres)

    return mutant, bras


def recherche_locale(individu, cout_actuel, max_essais, scores_bras):
    courant = individu[:]
    meilleur_cout = cout_actuel

    for _ in range(max_essais):
        voisin, bras = mutation(courant, scores_bras)
        cout_voisin = evaluer(voisin)

        if cout_voisin < meilleur_cout:
            courant = voisin
            meilleur_cout = cout_voisin
            recompense = 1.0
        else:
            recompense = 0.0

        if n < m:
            scores_bras[bras] += 0.1 * (recompense - scores_bras[bras])

    return courant, meilleur_cout


def main(inst=None, func_fitness=None, nb_q=None, nb_phys=None):
    global fitness, n, m, instance_num, circuit, backend
    if func_fitness is not None:
        instance_num, fitness, n, m = inst, func_fitness, nb_q, nb_phys
        backend, circuit, _, _ = instance_selector(inst)
    else:
        from __main__ import fitness, n, m, instance_num, circuit, backend

    memo_fitness.clear()
    debut = time.time()

    # Configuration asymétrique des 2 îles :
    # Île 0 : Intensification (mutation basse 0.25, recherche locale plus poussée)
    # Île 1 : Exploration (mutation haute 0.45, recherche locale légère)
    configs_iles = [
        {"prob_base": 0.25, "prob_actuelle": 0.25, "nb_eduques": 2, "max_voisins": 6, "stagnation": 0, "bras": [0.5, 0.5]},
        {"prob_base": 0.45, "prob_actuelle": 0.45, "nb_eduques": 1, "max_voisins": 4, "stagnation": 0, "bras": [0.5, 0.5]},
    ]

    iles_pop = []
    iles_scores = []

    # Initialisation de chaque île (Génération 0)
    for idx_ile in range(nb_iles):
        pop = [creer_individu() for _ in range(taille_ile)]
        # Île 0 reçoit l'individu topologique pur ; Île 1 reçoit l'individu topologique bruité
        pop[0] = creer_individu_topologique(bruit=(idx_ile == 1))

        sc = [evaluer(ind) for ind in pop]
        pop_triee = [ind for _, ind in sorted(zip(sc, pop), key=lambda x: x[0])]
        sc_tries = sorted(sc)

        cfg = configs_iles[idx_ile]
        for i in range(cfg["nb_eduques"]):
            pop_triee[i], sc_tries[i] = recherche_locale(
                pop_triee[i], sc_tries[i], cfg["max_voisins"], cfg["bras"]
            )

        iles_pop.append(pop_triee)
        iles_scores.append(sc_tries)

    # Meilleur individu global toutes îles confondues
    best_mapping = None
    best_cost = float("inf")
    for idx_ile in range(nb_iles):
        if iles_scores[idx_ile][0] < best_cost:
            best_cost = iles_scores[idx_ile][0]
            best_mapping = iles_pop[idx_ile][0][:]

    print(f"Génération 0 (2 îles) | Meilleur coût : {best_cost}")

    # Boucle principale d'évolution
    for gen in range(1, nb_generations + 1):
        for idx_ile in range(nb_iles):
            cfg = configs_iles[idx_ile]
            pop = iles_pop[idx_ile]
            sc = iles_scores[idx_ile]

            pop_triee = [ind for _, ind in sorted(zip(sc, pop), key=lambda x: x[0])]
            sc_tries = sorted(sc)

            # Mise à jour du record global et gestion de stagnation locale de l'île
            if sc_tries[0] < best_cost:
                best_cost = sc_tries[0]
                best_mapping = pop_triee[0][:]
                cfg["stagnation"] = 0
                cfg["prob_actuelle"] = cfg["prob_base"]
                print(f"Génération {gen} [Île {idx_ile}] | Nouveau meilleur coût : {best_cost} ({time.time() - debut:.1f}s)")
            else:
                cfg["stagnation"] += 1
                if cfg["stagnation"] == 8:
                    cfg["prob_actuelle"] = min(0.65, cfg["prob_base"] + 0.20)
                elif cfg["stagnation"] >= 13:
                    cfg["prob_actuelle"] = cfg["prob_base"]
                    cfg["stagnation"] = 0

            nouvelle_pop = [ind[:] for ind in pop_triee[:elitisme]]
            nouveaux_sc = sc_tries[:elitisme]

            enfants = []
            while len(enfants) < (taille_ile - elitisme):
                p1 = selection_tournoi(pop, sc)
                p2 = selection_tournoi(pop, sc)
                enfant = croisement_ox(p1, p2)
                if random.random() < cfg["prob_actuelle"]:
                    enfant, _ = mutation(enfant, cfg["bras"])
                enfants.append(enfant)

            sc_enfants = [evaluer(enf) for enf in enfants]
            enfants_tries = [enf for _, enf in sorted(zip(sc_enfants, enfants), key=lambda x: x[0])]
            sc_enfants_tries = sorted(sc_enfants)

            for i in range(len(enfants_tries)):
                if i < cfg["nb_eduques"]:
                    enf_ed, sc_ed = recherche_locale(
                        enfants_tries[i], sc_enfants_tries[i], cfg["max_voisins"], cfg["bras"]
                    )
                    nouvelle_pop.append(enf_ed)
                    nouveaux_sc.append(sc_ed)
                else:
                    nouvelle_pop.append(enfants_tries[i])
                    nouveaux_sc.append(sc_enfants_tries[i])

            iles_pop[idx_ile] = nouvelle_pop
            iles_scores[idx_ile] = nouveaux_sc

        # --- MIGRATION EN ANNEAU BIDIRECTIONNEL TOUTES LES freq_migration GÉNÉRATIONS ---
        if gen % freq_migration == 0:
            # On trie chaque île avant d'échanger le meilleur de l'une contre le pire de l'autre
            for idx_ile in range(nb_iles):
                zipped = sorted(zip(iles_scores[idx_ile], iles_pop[idx_ile]), key=lambda x: x[0])
                iles_scores[idx_ile] = [s for s, _ in zipped]
                iles_pop[idx_ile] = [ind for _, ind in zipped]

            migrant_0 = iles_pop[0][0][:]
            score_0 = iles_scores[0][0]
            migrant_1 = iles_pop[1][0][:]
            score_1 = iles_scores[1][0]

            # Remplace le pire individu (dernier indice) de chaque île par le champion de l'autre île
            iles_pop[0][-1] = migrant_1
            iles_scores[0][-1] = score_1
            iles_pop[1][-1] = migrant_0
            iles_scores[1][-1] = score_0

    # Polissage final sur le champion global
    best_mapping, best_cost = recherche_locale(best_mapping, best_cost, max_essais=20, scores_bras=configs_iles[0]["bras"])

    duree = time.time() - debut
    return nom, best_mapping, best_cost, duree, len(memo_fitness)