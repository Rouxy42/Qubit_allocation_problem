# -*- coding: utf-8 -*-
"""
GRASP réactif pour le Qubit Allocation Problem.

================================================================================
 PRINCIPE GENERAL
================================================================================
GRASP = Greedy Randomized Adaptive Search Procedure.

Une itération GRASP se décompose en deux phases :

  1. CONSTRUCTION gloutonne randomisée :
     on construit une solution (un "mapping") élément par élément. À chaque
     étape, on choisit un candidat dans une "Restricted Candidate List" (RCL)
     dont la taille est pilotée par le paramètre alpha (0 = glouton pur,
     1 = aléatoire pur). La construction n'appelle JAMAIS fitness() : elle
     utilise un score de substitution calculé à partir des deux graphes.

  2. RECHERCHE LOCALE :
     on améliore la solution construite en explorant son voisinage (swap de
     deux qubits physiques, ou remplacement par un qubit physique libre quand
     n < m). C'est ICI que fitness() (la boîte noire Qiskit) est appelée.

================================================================================
 VERSION "REACTIVE"
================================================================================
Un GRASP "classique" utilise un alpha fixe. Ici, on utilise un POOL d'alpha et
on adapte, au fil des itérations, la probabilité de choisir chaque alpha en
fonction de la QUALITE des solutions qu'il a produites (meilleures solutions
=> probabilité plus élevée). C'est le GRASP réactif (Prais & Ribeiro, 2000) :
il "apprend" tout seul quel alpha convient à l'instance en cours d'exécution.

================================================================================
 COMMENT CE MODULE S'INTEGRE AU PROJET
================================================================================
Ce fichier suit le même contrat que Scripts/genetique.py et
Scripts/memetique.py :

  - il définit une fonction main() qui retourne le 5-uplet :
        (nom, best_mapping, best_cost, duree, nb_evaluations)
  - il est exécuté depuis StudentCode.py via la fonction Scripts.run(...) :
        nom, best_mapping, best_cost, duree, nb_evals = run("grasp")

Les variables fitness, n, m, instance_num, backend et circuit sont importées
depuis le module principal (StudentCode.py), exactement comme le font les
autres scripts.
"""

import random  # Génération de nombres et de tirages aléatoires
import time    # Mesure du temps d'exécution


##====================================================================
##  PARAMETRES DE L'ALGORITHME
##====================================================================

nom = "GRASP réactif"  # Nom affiché dans les résultats de StudentCode.py

NB_ITERATIONS = 80      # Nombre d'itérations GRASP (construction + recherche locale)

# --- Paramètres de la recherche locale ---
NB_VOISINS_ETAPE = 5    # Nombre de voisins testés à chaque "balayage" de la descente
MAX_IMPASSES = 2        # Nombre de balayages consécutifs sans amélioration avant d'arrêter
NB_VOISINS_POLISSAGE = 30  # Budget de voisins pour le polissage final du meilleur mapping

# --- Paramètres du mécanisme réactif ---
# Pool d'alpha testés : 0.0 = glouton pur, 1.0 = aléatoire pur.
ALPHAS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
DELTA_REACTIF = 2.0  # Exposant qui accentue les différences de qualité entre alpha
P_MIN = 0.02         # Probabilité plancher : on garde toujours un peu d'exploration


##====================================================================
##  CACHE (MEMOISATION) DES EVALUATIONS
##====================================================================
# Chaque appel à fitness() déclenche une transpilation Qiskit, qui est COÛTEUSE.
# On mémorise donc chaque mapping déjà évalué pour ne jamais rappeler Qiskit
# deux fois pour la même solution.

memo_fitness = {}


def evaluer(mapping):
    """
    Renvoie le coût (profondeur du circuit routé) d'un mapping, en passant
    par le cache pour éviter de réévaluer deux fois la même solution.
    """
    cle = tuple(mapping)  # Une liste n'est pas hashable, on la convertit en tuple
    if cle not in memo_fitness:
        memo_fitness[cle] = fitness(mapping)
    return memo_fitness[cle]


##====================================================================
##  PRE-CALCULS (faits UNE SEULE FOIS par instance, très peu coûteux)
##====================================================================

def precalcul_distances():
    """
    Calcule les distances (plus courts chemins) entre tous les couples de
    qubits PHYSIQUES dans le graphe bleu (la connectivité du backend).

    Retourne (adj, dist) où :
      - adj[q]    : ensemble des voisins physiques du qubit q
      - dist[p][q]: distance entre les qubits physiques p et q

    m <= 27, donc un simple BFS depuis chaque sommet est largement suffisant.
    """
    # Construction de la liste d'adjacence du graphe bleu à partir du backend.
    adj = [set() for _ in range(m)]
    for (u, v) in backend.coupling_map.get_edges():
        if 0 <= u < m and 0 <= v < m:
            adj[u].add(v)
            adj[v].add(u)  # Le graphe est traité comme non orienté

    # BFS depuis chaque qubit physique pour obtenir toutes les distances.
    dist = [[0] * m for _ in range(m)]
    for source in range(m):
        vus = [-1] * m
        vus[source] = 0
        file = [source]
        while file:
            x = file.pop(0)
            for y in adj[x]:
                if vus[y] == -1:
                    vus[y] = vus[x] + 1
                    file.append(y)
        # Sécurité : un nœud inatteignable (graphe non connexe) reçoit une
        # grande distance arbitraire pour ne pas fausser le score glouton.
        for q in range(m):
            if vus[q] == -1:
                vus[q] = m
        dist[source] = vus

    return adj, dist


def precalcul_poids_circuit():
    """
    Construit le GRAPHE ORANGE : pour chaque couple de qubits VIRTUELS (i, j),
    on compte le nombre de portes à 2 qubits qui les relient dans le circuit.

    w[i][j] = nombre d'interactions (ex. CNOT) entre les qubits virtuels i et j.

    C'est ce graphe qui va guider la construction : deux qubits virtuels qui
    interagissent beaucoup doivent être placés sur des qubits physiques proches.
    """
    w = [[0] * n for _ in range(n)]

    # Table de correspondance : objet Qubit -> indice 0..n-1 dans le circuit.
    index_qubit = {}
    for q in circuit.qubits:
        index_qubit[q] = circuit.find_bit(q).index

    for instr in circuit.data:
        op = instr.operation
        qubits = instr.qubits

        # On ne garde que les portes à 2 qubits (ce sont elles qui exigent que
        # les deux qubits soient voisins sur la puce). Les barrières ne
        # comptent pas : elles n'imposent aucune contrainte d'adjacence.
        if op.num_qubits == 2 and len(qubits) == 2 and op.name != "barrier":
            i = index_qubit.get(qubits[0])
            j = index_qubit.get(qubits[1])
            if i is not None and j is not None and i != j:
                w[i][j] += 1
                w[j][i] += 1

    return w


##====================================================================
##  CONSTRUCTION GLOUTONNE RANDOMISEE
##====================================================================

def qubit_physique_central(adj, dist):
    """
    Choisit le qubit physique sur lequel on place le PREMIER qubit virtuel
    (celui qui interagit le plus). On privilégie un qubit physique bien
    connecté : degré maximal, puis plus petite excentricité (distance max
    vers les autres), ce qui revient à choisir un "centre" du graphe bleu.
    """
    degres = [len(adj[q]) for q in range(m)]
    degre_max = max(degres)
    candidats = [q for q in range(m) if degres[q] == degre_max]

    # Départage par excentricité (plus petite distance max vers les autres).
    excentricites = {}
    for q in candidats:
        excentricites[q] = max(dist[q])  # dist[q] contient les distances vers tous
    excentricite_min = min(excentricites.values())
    finalistes = [q for q in candidats if excentricites[q] == excentricite_min]

    return random.choice(finalistes)


def construction_gloutonne(alpha, ordre, adj, dist, w):
    """
    Construit un mapping admissible (liste de n qubits physiques distincts)
    de façon gloutonne randomisée.

    Paramètres :
      - alpha : paramètre GRASP qui contrôle la taille de la RCL.
      - ordre : liste des qubits virtuels ordonnée par "importance" décroissante.
      - adj   : liste d'adjacence du graphe bleu (choix du qubit central).
      - dist  : matrice des distances entre qubits physiques.
      - w     : matrice des poids d'interaction entre qubits virtuels.

    Déroulement :
      1. On place le qubit virtuel le plus important sur un qubit physique central.
      2. Pour chaque qubit virtuel suivant v, on estime pour chaque qubit
         physique libre p le surcoût :
             g(v, p) = somme_{u déjà placé} w[v][u] * dist[p][mapping[u]]
         c'est-à-dire : "à quelle distance de ses voisins déjà placés se
         retrouverait v s'il était mis sur p ?".
      3. On ne garde que les p dont g est proche du meilleur (RCL), et on tire
         au hasard dans cette liste. alpha = 0 -> uniquement le meilleur,
         alpha = 1 -> tous les candidats.
    """
    # Cas dégénéré (un seul qubit virtuel) : rien à construire.
    if n == 1:
        return [random.randrange(m)]

    mapping = [None] * n              # mapping[i] = qubit physique du virtuel i
    libres = set(range(m))            # Qubits physiques encore disponibles

    # 1) Graine : on place le qubit virtuel le plus important au centre.
    premier = ordre[0]
    graine = qubit_physique_central(adj, dist)
    mapping[premier] = graine
    libres.discard(graine)

    # 2) Placement glouton randomisé des qubits virtuels restants.
    for v in ordre[1:]:
        scores = []  # Liste de couples (g, p) pour chaque qubit physique libre p

        for p in libres:
            g = 0
            # Somme des "distances pondérées" vers les voisins déjà placés.
            for u in range(n):
                if mapping[u] is not None and w[v][u] > 0:
                    g += w[v][u] * dist[p][mapping[u]]
            scores.append((g, p))

        # Bornes du score parmi les candidats libres.
        g_min = min(g for g, _ in scores)
        g_max = max(g for g, _ in scores)

        # RCL : candidats dont le score est dans les "alpha meilleurs".
        seuil = g_min + alpha * (g_max - g_min)
        rcl = [p for g, p in scores if g <= seuil]

        # Tirage au hasard dans la RCL.
        choisi = random.choice(rcl)
        mapping[v] = choisi
        libres.discard(choisi)

    return mapping


##====================================================================
##  RECHERCHE LOCALE
##====================================================================

def voisin_aleatoire(mapping):
    """
    Renvoie un VOISIN aléatoire d'un mapping, c'est-à-dire une solution très
    proche obtenue par une petite modification :

      - soit un SWAP interne : échange des qubits physiques entre deux positions
        (c'est le seul mouvement possible quand n == m) ;
      - soit un REMPLACEMENT externe : quand n < m, on remplace un qubit du
        mapping par un qubit physique libre (permet de changer le sous-ensemble
        des qubits physiques utilisés).
    """
    voisin = mapping[:]  # Copie indépendante pour ne pas modifier l'original

    # Mouvement externe : uniquement possible si des qubits physiques sont libres.
    if n < m and random.random() < 0.5:
        utilises = set(voisin)
        libres = [q for q in range(m) if q not in utilises]
        idx = random.randrange(n)
        voisin[idx] = random.choice(libres)
    else:
        # Mouvement interne : swap de deux positions.
        if n >= 2:
            i, j = random.sample(range(n), 2)
            voisin[i], voisin[j] = voisin[j], voisin[i]

    return voisin


def recherche_locale(mapping, nb_voisins=NB_VOISINS_ETAPE, max_impasses=MAX_IMPASSES):
    """
    Descente stochastique (first-improvement sur un petit échantillon) :

    À chaque balayage, on teste nb_voisins voisins aléatoires et on retient le
    meilleur d'entre eux s'il améliore la solution courante. On s'arrête après
    max_impasses balayages consécutifs sans amélioration.

    Chaque voisin testé passe par evaluer() (donc par le cache), ce qui évite
    de rappeler Qiskit pour une solution déjà vue.
    """
    courant = mapping[:]
    cout_courant = evaluer(courant)

    impasses = 0
    while impasses < max_impasses:
        meilleur_voisin = None
        meilleur_cout = cout_courant

        for _ in range(nb_voisins):
            voisin = voisin_aleatoire(courant)
            cout_voisin = evaluer(voisin)
            if cout_voisin < meilleur_cout:
                meilleur_cout = cout_voisin
                meilleur_voisin = voisin

        if meilleur_voisin is not None:
            courant = meilleur_voisin
            cout_courant = meilleur_cout
            impasses = 0
        else:
            impasses += 1

    return courant, cout_courant


##====================================================================
##  MECANISME REACTIF (mise à jour des probabilités des alpha)
##====================================================================

def mettre_a_jour_probabilites(sommes, comptes, delta=DELTA_REACTIF, p_min=P_MIN):
    """
    Met à jour la probabilité de sélection de chaque alpha en fonction de la
    QUALITE MOYENNE des solutions qu'il a produites.

      - sommes[i]  : somme des qualités (1 / coût) obtenues avec ALPHAS[i]
      - comptes[i] : nombre de fois où ALPHAS[i] a été utilisé

    Un alpha qui produit régulièrement de MEILLEURES solutions (coût plus petit)
    aura une qualité moyenne plus grande, donc une probabilité plus élevée.
    Le paramètre delta accentue ces différences, et p_min garantit qu'aucun
    alpha ne tombe à une probabilité nulle (pour conserver de l'exploration).
    """
    k = len(ALPHAS)

    # Tant qu'aucun alpha n'a été testé, on reste sur une distribution uniforme.
    if sum(comptes) == 0:
        return [1.0 / k] * k

    # Qualité moyenne de chaque alpha (0 pour ceux jamais encore utilisés).
    moyennes = []
    for i in range(k):
        if comptes[i] > 0:
            moyennes.append(sommes[i] / comptes[i])
        else:
            moyennes.append(0.0)

    # Élévation à la puissance delta pour accentuer les écarts de qualité.
    poids = [m ** delta for m in moyennes]

    total = sum(poids)
    if total == 0:
        return [1.0 / k] * k

    # Probabilités normalisées, avec un plancher p_min.
    probas = [max(p / total, p_min) for p in poids]
    somme = sum(probas)
    return [p / somme for p in probas]


##====================================================================
##  BOUCLE PRINCIPALE
##====================================================================

def main():
    # Les variables suivantes sont définies dans StudentCode.py (module __main__).
    # On les importe ici pour que le script soit autonome une fois appelé via run().
    global fitness, n, m, instance_num, backend, circuit
    from __main__ import fitness, n, m, instance_num, backend, circuit

    # On vide le cache au début de chaque exécution (nouvelle instance).
    memo_fitness.clear()

    debut = time.time()

    # --- Pré-calculs (une seule fois, très peu coûteux) ---
    adj, dist = precalcul_distances()   # Distances du graphe BLEU (physique)
    w = precalcul_poids_circuit()       # Poids du graphe ORANGE (virtuel)

    # Ordre de placement des qubits virtuels : du plus "connecté" au moins.
    importance = [sum(w[v]) for v in range(n)]
    ordre = sorted(range(n), key=lambda v: (-importance[v], v))

    # --- État du mécanisme réactif ---
    k = len(ALPHAS)
    probas = [1.0 / k] * k  # Probabilités initiales uniformes
    sommes = [0.0] * k      # Somme des qualités (1/coût) par alpha
    comptes = [0] * k       # Nombre d'utilisations de chaque alpha

    best_mapping = None
    best_cost = float("inf")

    print(f"=== {nom} | Instance {instance_num} (n={n}, m={m}) ===")

    # --- Boucle GRASP réactive ---
    for it in range(1, NB_ITERATIONS + 1):
        # 1) Tirage d'un alpha selon la distribution réactive courante.
        idx = random.choices(range(k), weights=probas, k=1)[0]
        alpha = ALPHAS[idx]

        # 2) Phase de construction (gloutonne randomisée).
        solution = construction_gloutonne(alpha, ordre, adj, dist, w)

        # 3) Phase de recherche locale.
        solution, cout = recherche_locale(solution)

        # 4) Mise à jour de la meilleure solution globale.
        if cout < best_cost:
            best_cost = cout
            best_mapping = solution[:]
            print(f"Itération {it:3d} | alpha={alpha:.2f} | "
                  f"Nouveau meilleur coût : {best_cost} ({time.time() - debut:.1f}s)")

        # 5) Apprentissage réactif : on enregistre la qualité de cet alpha.
        sommes[idx] += 1.0 / max(cout, 1)
        comptes[idx] += 1
        # On ne commence à adapter les probabilités qu'une fois que chaque
        # alpha a été testé au moins une fois (évite une convergence trop rapide).
        if min(comptes) > 0:
            probas = mettre_a_jour_probabilites(sommes, comptes)

    # --- Sécurité : si aucun mapping n'a été produit (ex. NB_ITERATIONS = 0) ---
    if best_mapping is None:
        best_mapping = construction_gloutonne(0.0, ordre, adj, dist, w)
        best_cost = evaluer(best_mapping)

    # --- Polissage final : recherche locale plus poussée sur le meilleur ---
    best_mapping, best_cost = recherche_locale(
        best_mapping, nb_voisins=NB_VOISINS_POLISSAGE, max_impasses=MAX_IMPASSES
    )

    duree = time.time() - debut

    # Bilan des probabilités apprises (utile pour comprendre le comportement réactif).
    print(f"\nProbabilités finales des alpha (apprentissage réactif) :")
    for a, p in zip(ALPHAS, probas):
        barre = "#" * int(round(p * 40))
        print(f"  alpha={a:.2f}  proba={p:.3f}  {barre}")

    # Retour au même format que genetique.py et memetique.py.
    return nom, best_mapping, best_cost, duree, len(memo_fitness)
