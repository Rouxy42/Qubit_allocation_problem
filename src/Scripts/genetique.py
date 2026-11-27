#genetique-simple




##-------------------------------------------------------
##     A vous de jouer !  
##-------------------------------------------------------

import random  # Importe le module Python permettant de générer des nombres et tirages aléatoires
import time    # Importe le module Python permettant de mesurer le temps d'exécution en secondes

# 1. Paramètres de l'Algorithme Génétique
nom= "Algo Génétique"
nom_groupe = "GroupeC"  # Nom du groupe utilisé pour nommer automatiquement le fichier de sortie
pop_size = 25           # Taille de la population : nombre de solutions candidates conservées à chaque génération
nb_generations = 120    # Nombre total de générations (itérations d'évolution) que l'algorithme va exécuter
prob_mutation = 0.35    # Probabilité de mutation : 35 % de chance qu'un enfant subisse une modification aléatoire
elitisme = 2            # Élitisme : nombre des meilleurs individus copiés tels quels vers la génération suivante

# Dictionnaire de cache (mémoïsation) associant chaque permutation déjà testée à son score fitness()
memo_fitness = {}

def evaluer(mapping):
    # Convertit la liste mapping en tuple (structure immuable) car Python interdit une liste comme clé de dictionnaire
    cle = tuple(mapping)
    # Vérifie si cette permutation précise n'a pas encore été évaluée par Qiskit
    if cle not in memo_fitness:
        # Si elle est nouvelle, appelle la fonction boîte noire fitness(mapping) et sauvegarde son coût dans le cache
        memo_fitness[cle] = fitness(mapping)
    # Renvoie le coût (soit fraîchement calculé par Qiskit, soit lu instantanément depuis le cache)
    return memo_fitness[cle]

def creer_individu():
    # Pioche sans remise (donc sans aucun doublon) n entiers distincts dans {0, ..., m-1} et les renvoie en liste
    return random.sample(range(m), n)

def selection_tournoi(population, scores, k=3):
    # Tire au hasard k indices distincts parmi les individus de la population actuelle
    indices = random.sample(range(len(population)), k)
    # Compare les scores des k candidats tirés et retient l'indice de celui qui a le plus petit coût (minimisation)
    meilleur_idx = min(indices, key=lambda i: scores[i])
    # Renvoie une copie indépendante ([:]) de l'individu gagnant pour ne pas modifier l'original par erreur
    return population[meilleur_idx][:]

def croisement_ox(parent1, parent2):
    # Sécurité si un circuit n'avait qu'un seul qubit (impossible de couper en deux)
    if n < 2:
        return parent1[:]
    
    # Tire 2 indices de coupure distincts entre 0 et n, et les trie par ordre croissant pour avoir a < b
    a, b = sorted(random.sample(range(n + 1), 2))
    # Crée une liste enfant de taille n initialement remplie de cases vides (None)
    enfant = [None] * n
    
    # Recopie exactement le segment central du parent 1 (indices a à b-1) aux mêmes positions dans l'enfant
    enfant[a:b] = parent1[a:b]
    # Stocke dans un ensemble (set) les qubits physiques déjà placés dans l'enfant pour vérifier les doublons en O(1)
    deja_presents = set(parent1[a:b])
    
    # Initialise un curseur au début de l'enfant pour repérer la prochaine case vide à remplir
    idx_enfant = 0
    # Parcourt un par un tous les qubits physiques du parent 2 de gauche à droite
    for gene in parent2:
        # Si ce qubit physique n'est pas encore présent dans l'enfant
        if gene not in deja_presents:
            # Avance le curseur jusqu'à trouver la prochaine case None (en sautant le bloc copié du parent 1)
            while idx_enfant < n and enfant[idx_enfant] is not None:
                idx_enfant += 1
            # Vérifie que le curseur n'a pas dépassé la fin de la liste
            if idx_enfant < n:
                # Place le gène du parent 2 dans cette case libre
                enfant[idx_enfant] = gene
                # Ajoute ce qubit à l'ensemble des qubits déjà utilisés pour interdire tout doublon futur
                deja_presents.add(gene)
    
    # Gère le cas spécifique où n < m (il y a plus de qubits physiques sur la machine que de qubits virtuels)
    if None in enfant:
        # Liste tous les qubits physiques du processeur qui ne sont pas encore utilisés dans l'enfant
        libres = [q for q in range(m) if q not in deja_presents]
        # Mélange aléatoirement cette liste de qubits disponibles
        random.shuffle(libres)
        # Parcourt l'enfant pour combler les dernières cases vides restantes en piochant un qubit libre
        for i in range(n):
            if enfant[i] is None:
                enfant[i] = libres.pop()
                
    # Renvoie l'enfant complet et 100 % admissible (taille n, sans doublon)
    return enfant

def mutation(individu):
    # Fait une copie indépendante de l'individu pour ne pas altérer l'original
    mutant = individu[:]
    # Si tous les qubits physiques sont utilisés (n == m), ou avec 50 % de chance quand n < m :
    if n == m or random.random() < 0.5:
        # Mutation interne (intensification) : échange deux qubits physiques déjà présents dans le mapping
        if n >= 2:
            # Tire deux positions distinctes i et j dans le mapping
            i, j = random.sample(range(n), 2)
            # Échange leurs valeurs
            mutant[i], mutant[j] = mutant[j], mutant[i]
    else:
        # Mutation externe (diversification, uniquement quand n < m) : remplace un qubit par un qubit libre
        utilises = set(mutant)
        # Récupère tous les qubits physiques disponibles ailleurs sur la puce quantique
        libres = [q for q in range(m) if q not in utilises]
        if libres:
            # Choisit une position au hasard dans le mutant
            idx = random.randrange(n)
            # Remplace le qubit à cette position par un qubit libre choisi au hasard
            mutant[idx] = random.choice(libres)
    # Renvoie l'individu muté
    return mutant

def main(inst=None, func_fitness=None, nb_q=None, nb_phys=None):
    global fitness, n, m, instance_num
    if func_fitness is not None:
        instance_num, fitness, n, m = inst, func_fitness, nb_q, nb_phys
    else:
        from __main__ import fitness, n, m, instance_num
    memo_fitness.clear()
    # 2. Exécution de l'Algorithme Génétique
    debut = time.time()  # Enregistre l'horodatage de départ pour calculer la durée totale
    # Crée la population initiale (génération 0) composée de pop_size solutions aléatoires
    population = [creer_individu() for _ in range(pop_size)]
    # Calcule le coût fitness de chaque individu initial en passant par le cache
    scores = [evaluer(ind) for ind in population]

    # Trouve l'indice du meilleur individu de la génération initiale
    meilleur_idx = min(range(pop_size), key=lambda i: scores[i])
    # Sauvegarde une copie du meilleur mapping trouvé jusqu'ici et son coût
    best_mapping = population[meilleur_idx][:]
    best_cost = scores[meilleur_idx]
    print(f"Génération 0 | Meilleur coût : {best_cost}")

    # Démarre la boucle principale sur nb_generations générations
    for gen in range(1, nb_generations + 1):
        # Associe chaque individu à son score (zip), trie par coût croissant (sorted), et extrait les individus triés
        population_triee = [ind for _, ind in sorted(zip(scores, population), key=lambda x: x[0])]
        # Trie également la liste des scores par ordre croissant
        scores_tries = sorted(scores)
        
        # Vérifie si le meilleur individu de cette génération bat le record historique global
        if scores_tries[0] < best_cost:
            best_cost = scores_tries[0]
            best_mapping = population_triee[0][:]
            print(f"Génération {gen} | Nouveau meilleur coût : {best_cost} ({time.time() - debut:.1f}s)")
        
        # Applique l'élitisme en copiant directement les meilleurs individus en tête de la future génération
        nouvelle_population = [ind[:] for ind in population_triee[:elitisme]]
        
        # Génère de nouveaux enfants jusqu'à atteindre la taille pop_size
        while len(nouvelle_population) < pop_size:
            # Sélectionne deux parents par tournoi
            p1 = selection_tournoi(population, scores)
            p2 = selection_tournoi(population, scores)
            
            # Combine les deux parents via le croisement d'ordre OX
            enfant = croisement_ox(p1, p2)
            # Tire un nombre aléatoire entre 0 et 1 : s'il est inférieur à prob_mutation, applique une mutation
            if random.random() < prob_mutation:
                enfant = mutation(enfant)
                
            # Ajoute l'enfant à la nouvelle génération
            nouvelle_population.append(enfant)
            
        # Remplace l'ancienne population par la nouvelle génération
        population = nouvelle_population
        # Évalue le coût de tous les individus de cette nouvelle génération
        scores = [evaluer(ind) for ind in population]

    # Vérification finale sur la toute dernière génération produite
    for ind, sc in zip(population, scores):
        if sc < best_cost:
            best_cost = sc
            best_mapping = ind[:]

    # Calcule la durée totale d'exécution en secondes
    duree = time.time() - debut
    # Affiche le bilan : temps écoulé et nombre réel d'appels à Qiskit effectués (taille du dictionnaire cache)

    return nom, best_mapping, best_cost, duree, len(memo_fitness)