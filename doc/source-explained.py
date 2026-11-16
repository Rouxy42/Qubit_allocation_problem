# -*- coding: utf-8 -*-
# ^ Indique à Python que le fichier contient des caractères français (accents).

"""
Created on Mon Nov  2 10:16:20 2026
@author: Jérôme Rouzé
...
"""
# ^ Commentaire de l'enseignant : ce fichier sert de "boîte noire" (slide 2).
# Tu n'as pas le droit de le modifier, ton code ira dans StudentCode.py.


# ==============================================================================
# IMPORTATION DES OUTILS QISKIT (la bibliothèque quantique d'IBM, slide 11)
# ==============================================================================

from qiskit import QuantumCircuit
# ^ QuantumCircuit permet de lire et manipuler un circuit quantique (le fameux
#   programme avec les portes H et CNOT qu'on voit sur les slides 6 à 10,
#   et qui correspond au GRAPHE ORANGE).

from qiskit.transpiler import Layout
# ^ Layout ("disposition" en anglais) est l'outil qui stocke l'association
#   entre le graphe orange et le graphe bleu (ex: A->1, B->0, C->2 sur la slide 3).

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
# ^ Le "PassManager" est le compilateur de Qiskit : c'est lui qui regarde ton
#   association, voit quelles connexions manquent sur le graphe bleu, et ajoute
#   automatiquement les portes SWAP nécessaires (le "routing" de la slide 7).


##-------------------------------------------------------
##     Création du backend (machine quantique)
##-------------------------------------------------------
# Dans Qiskit, un "backend" = un ordinateur quantique physique (le GRAPHE BLEU).
# Pour m = 20 et m = 27, Qiskit possède déjà des modèles tout faits.
# Mais pour m = 16 (instances 1, 2 et 3), le professeur a voulu créer sa propre
# machine quantique sur mesure : il crée donc la classe "CustomBackend" ci-dessous.

from qiskit.providers import BackendV2
# ^ BackendV2 est le "moule" (classe de base) de Qiskit pour fabriquer une machine quantique.
from qiskit.providers.options import Options
# ^ Permet de régler des options par défaut pour cette machine.
from qiskit.providers.exceptions import QiskitError
# ^ Permet d'afficher un message d'erreur propre à Qiskit.

class CustomBackend(BackendV2):
    # On crée notre propre modèle de machine quantique en héritant de BackendV2.
    
    def __init__(self, target, coupling):
        # Fonction appelée quand on construit la machine. Elle reçoit :
        # - target : la liste des portes quantiques que la machine sait faire.
        # - coupling : la carte des connexions physiques (les arêtes du GRAPHE BLEU).
        
        super().__init__(name="custom_basis_backend")
        # ^ Donne le nom "custom_basis_backend" à notre machine.
        
        self._target = target
        self._coupling = coupling
        # ^ Sauvegarde les portes autorisées (_target) et le graphe bleu (_coupling)
        #   à l'intérieur de notre objet machine.

    @property
    def target(self):
        return self._target
    # ^ Permet à Qiskit de demander à la machine : "Quelles portes sais-tu exécuter ?"

    @property
    def coupling_map(self):
        return self._coupling
    # ^ Permet à Qiskit de demander à la machine : "Quel est ton graphe bleu (connectivité) ?"

    @classmethod
    def _default_options(cls):
        return Options(shots=1024)
    # ^ Réglage technique obligatoire dans Qiskit (nombre d'essais = 1024).
    #   Ça ne sert pas dans ce projet car on ne lance pas vraiment le calcul quantique.
    
    @property
    def max_circuits(self):
        return 1
    # ^ Indique que la machine traite 1 seul circuit à la fois.
    
    def run(self, run_input, **options):
        raise QiskitError(
            "This backend is for transpilation only and does not support execution."
        )
    # ^ Si quelqu'un essaie de lancer un vrai calcul quantique (.run()), la machine
    #   bloque et affiche une erreur : ici, elle sert uniquement à calculer les portes
    #   SWAP à ajouter ("transpilation" / routing), pas à exécuter le circuit !


# ==============================================================================
# CHOIX DE LA MACHINE PHYSIQUE (GRAPHE BLEU) SELON LE NOMBRE m DE QUBITS
# ==============================================================================
# Regarde le tableau de la slide 15 : m vaut soit 16, soit 20, soit 27.

def backend_selector(num_physical_qubit):
    # num_physical_qubit correspond à "m" (le nombre de sommets du graphe bleu).

    if num_physical_qubit == 20:
        ### Cas où m = 20 (Instances 4, 5 et 6)
        from qiskit.providers.fake_provider import Fake20QV1
        from qiskit.providers import BackendV2Converter
        
        backend = Fake20QV1()
        # ^ Charge une copie virtuelle d'un vrai ordinateur IBM à 20 qubits.
        backend = BackendV2Converter(backend)
        # ^ Convertit cet ancien modèle (V1) vers le format récent de Qiskit (V2).
       
    elif num_physical_qubit == 27:
        ### Cas où m = 27 (Instances 7, 8 et 9)
        from qiskit.providers.fake_provider import Fake27QPulseV1
        from qiskit.providers import BackendV2Converter
        
        backend = Fake27QPulseV1()
        # ^ Charge une copie virtuelle d'un vrai ordinateur IBM à 27 qubits.
        backend = BackendV2Converter(backend)
        # ^ Convertit le modèle vers le format V2.
        
    else:
        ### Cas par défaut : m = 16 (Instances 1, 2 et 3)
        # Ici, le professeur construit lui-même le graphe bleu à 16 sommets (numérotés de 0 à 15).
        from qiskit.transpiler import CouplingMap
        
        coupling = CouplingMap([
            (0,1), (1,2), (2,3), (3,4), (4,5), (5,6), (6,7), (7,8), (8,9), (9,10), (10,11), (11,12), (12,13),
            (13,14), (14,15), (0,15), (1,14), (2,13), (3,12), (4,11), (5,10), (6,9)
        ])
        # ^ VOICI LE GRAPHE BLEU pour m = 16 !
        #   Chaque couple (a, b) est une arête bleue : le qubit physique 'a' est relié au qubit 'b'.
        #   Par exemple (0,1) signifie que les qubits physiques 0 et 1 sont directement connectés.
        
        from qiskit.transpiler import Target
        from qiskit.circuit.library import IGate, XGate, CXGate, RZGate, SXGate, Reset
        from qiskit.circuit import Measure
        # ^ Importe les briques de base (les portes logiques quantiques, slide 6).
        
        target = Target(num_qubits=16)
        # ^ Crée la fiche technique d'une machine qui possède m = 16 qubits physiques.
        
        # 1-qubit gates (Portes agissant sur 1 seul qubit à la fois, comme la porte H de la slide 6)
        target.add_instruction(IGate(),   {(q,): None for q in range(target.num_qubits)})
        target.add_instruction(XGate(),   {(q,): None for q in range(target.num_qubits)})
        target.add_instruction(SXGate(),  {(q,): None for q in range(target.num_qubits)})
        target.add_instruction(RZGate(0), {(q,): None for q in range(target.num_qubits)})
        target.add_instruction(Reset(),   {(q,): None for q in range(target.num_qubits)})
        target.add_instruction(Measure(), {(q,): None for q in range(target.num_qubits)})
        # ^ Ces 6 lignes disent simplement : "Les portes simples (sur 1 seul qubit) peuvent
        #   être utilisées librement sur n'importe lequel des 16 qubits physiques (de 0 à 15)."
        #   Elles ne posent jamais de problème de connexion !
        
        # 2-qubit gates follow coupling graph (Portes agissant sur 2 qubits : la porte CNOT !)
        cx_edges = set(coupling.get_edges())
        # ^ Récupère toutes les arêtes (a, b) du graphe bleu définies plus haut.
        cx_edges |= {(b, a) for (a, b) in coupling.get_edges()}
        # ^ Ajoute aussi le sens inverse (b, a) pour que chaque connexion marche dans les deux sens.
        target.add_instruction(CXGate(), {edge: None for edge in cx_edges})
        # ^ LIGNE TRÈS IMPORTANTE : CXGate() est la porte CNOT (slide 6).
        #   Cette ligne impose la règle du jeu : "On a le droit de faire une porte CNOT
        #   entre deux qubits physiques UNIQUEMENT s'ils sont reliés par une arête du graphe bleu (cx_edges)."
        #   Sinon, Qiskit devra ajouter des portes SWAP !

        backend = CustomBackend(target, coupling)
        # ^ Fabrique finalement la machine à 16 qubits avec ces règles.

    return backend
    # ^ Renvoie la machine quantique choisie (16, 20 ou 27 qubits).


##-------------------------------------------------------
##     Selection de l'instance du probleme
##-------------------------------------------------------
# Cette fonction est celle que tu vois sur la slide 12 dans StudentCode.py :
# backend, circuit, n, m = instance_selector(instance_num)

def instance_selector(instance_num):
    # Selon le numéro d'instance (1 à 9 dans le tableau de la slide 15,
    # plus 11, 12, 13 pour le challenge), on choisit la bonne taille de graphe bleu (m) :
    if instance_num == 1 or instance_num == 2 or instance_num == 3 or instance_num == 11:
        backend = backend_selector(16)  # Graphe bleu à m = 16 qubits physiques
    elif instance_num == 4 or instance_num == 5 or  instance_num == 6 or instance_num == 12:
        backend = backend_selector(20)  # Graphe bleu à m = 20 qubits physiques
    elif instance_num == 7 or instance_num == 8 or  instance_num == 9 or instance_num == 13:
        backend = backend_selector(27)  # Graphe bleu à m = 27 qubits physiques
    else:
        # Sécurité si l'étudiant tape un mauvais numéro (ex: 99) :
        print("Choix d'une instance inexistance, instance 1 revoyé  par défaut")
        backend = backend_selector(16)
        instance_num = 1
        
    qasmfile = f".\Instances\Instance_{instance_num}.qasm"  ###### Il est possible de cette ligne soit problèmatique.
    # ^ Prépare le nom du fichier à ouvrir dans le dossier "Instances" (slide 14),
    #   par exemple ".\Instances\Instance_1.qasm".
    #   (Note du prof : sur Mac/Linux, le "\" de Windows peut nécessiter d'être remplacé par "/").

    circuit = QuantumCircuit().from_qasm_file(qasmfile)
    # ^ Lit le fichier .qasm et construit le circuit quantique original (d'où vient le GRAPHE ORANGE).

    circuit.remove_final_measurements()
    # ^ Enlève les boîtes de mesure à la fin du circuit (les petits cadrans avec une flèche
    #   qu'on voit à droite sur la slide 6, et qui ont été retirés sur les slides 7, 8 et 9)
    #   car elles ne comptent pas dans le problème d'optimisation.
    
    n = circuit.num_qubits
    # ^ Compte combien le circuit utilise de qubits virtuels (n = taille du graphe orange).
    m = backend.num_qubits
    # ^ Compte combien la machine possède de qubits physiques (m = taille du graphe bleu).
    
    return backend,circuit,n,m
    # ^ Renvoie les 4 éléments prêts à l'emploi pour StudentCode.py (slide 12).


# ==============================================================================
# DESSINS DES GRAPHES (FAIT PAR IA) (PAS INCLUS DANS LE SOURCE.PY ORIGINEL)
# ==============================================================================

from source import backend_selector
import graphviz

# Les trois tailles de graphes bleus de ton projet
tailles_m = [16, 20, 27]

for m in tailles_m:
    print(f"\n" + "="*50)
    print(f" MACHINE QUANTIQUE : m = {m} QUBITS physiques")
    print("="*50)
    
    # Charger la machine quantique correspondante
    backend = backend_selector(m)
    
    # --- MÉTHODE 1 : Liste des arêtes en texte ---
    # On filtre (u < v) pour n'afficher qu'une seule fois chaque arête (ex: [0, 1] mais pas [1, 0])
    aretes_uniques = []
    for u, v in backend.coupling_map.get_edges():
        if u < v:
            aretes_uniques.append([u, v])
            
    print(f"Liste des {len(aretes_uniques)} connexions physiques :")
    print(aretes_uniques)
    
    # --- MÉTHODE 2 : Dessiner le graphe visuel ---
    g = graphviz.Graph(engine='neato', format='png')
    g.attr(overlap='false', splines='true')
    
    # Création des sommets (de 0 à m-1)
    for i in range(backend.num_qubits):
        g.node(str(i), 
               style='filled', 
               fillcolor='lightblue', 
               shape='circle', 
               fontname='Helvetica',
               penwidth='2')
        
    # Création des arêtes
    for u, v in aretes_uniques:
        g.edge(str(u), str(v), color='gray50', penwidth='2')
            
    # Sauvegarde et affichage
    nom_fichier = f"Graphe_Machine_{m}_Qubits"
    g.view(filename=nom_fichier)
    
    print(f"--> Image '{nom_fichier}.png' générée et ouverte avec succès !")

# On récupère le nombre de qubits pour générer les noeuds (de 0 à 19)
for i in range(backend.num_qubits):
    g.node(str(i), 
           style='filled', 
           fillcolor='lightblue', 
           shape='circle', 
           fontname='Helvetica',
           penwidth='2')

# On ajoute les connexions physiques (les arêtes du graphe bleu)
# On filtre (u < v) car le backend liste les connexions dans les deux sens (ex: 0->1 et 1->0)
for u, v in backend.coupling_map.get_edges():
    if u < v:
        g.edge(str(u), str(v), color='gray50', penwidth='2')

# Cette ligne génère le fichier et l'ouvre automatiquement dans ta visionneuse d'images !
g.view(filename="Graphe_Fake20QV1")

# ==============================================================================
# LA FONCTION OBJECTIF "BLACK BOX" (Slides 2, 8, 9 et 11)
# ==============================================================================
# C'est cette fonction qui calcule le COÛT d'une solution proposée par ton algorithme.
# - mapping : ta liste ordonnée de n entiers distincts entre 0 et m-1 (ex: [1, 0, 2] sur la slide 9).
# - circuit : le circuit quantique de l'instance (graphe orange).
# - backend : la machine quantique de l'instance (graphe bleu).

def fitness_inner(mapping,circuit,backend):
    qr=circuit.qregs[0]
    # ^ Récupère la liste des qubits virtuels du circuit : [q0, q1, q2, ..., q_{n-1}].

    init_mapping = {qr[i]:mapping[i] for i in range(len(mapping))}
    # ^ Crée un dictionnaire qui associe chaque qubit virtuel i au qubit physique mapping[i].
    #   Exemple de la slide 9 avec mapping = [1, 0, 2] :
    #   - qr[0] (q0) est associé au qubit physique 1
    #   - qr[1] (q1) est associé au qubit physique 0
    #   - qr[2] (q2) est associé au qubit physique 2

    init_mapping = Layout(init_mapping)
    # ^ Transforme ce dictionnaire en un objet "Layout" officiel pour Qiskit.

    pm = generate_preset_pass_manager(3,backend,initial_layout=init_mapping)
    # ^ Prépare le compilateur ("PassManager") de Qiskit en lui donnant :
    #   - le niveau d'optimisation 3 (le plus élevé pour simplifier les portes),
    #   - la machine cible (backend),
    #   - et SURTOUT ton association de départ (initial_layout=init_mapping).

    pm.layout.remove(1)
    pm.layout.remove(1)
    # ^ POURQUOI CES DEUX LIGNES ? C'est l'astuce du professeur :
    #   Normalement, quand on met le niveau 3, Qiskit est "trop malin" : il ignore ou modifie
    #   ton association de départ pour chercher lui-même une meilleure association !
    #   En faisant deux fois ".remove(1)", le professeur supprime les étapes où Qiskit
    #   choisit l'association. Ainsi, Qiskit est FORCÉ de garder exactement TON association (mapping),
    #   et se contente d'ajouter les portes SWAP nécessaires (le routing) !

    QC=pm.run(circuit)
    # ^ Lance la transformation : Qiskit prend le circuit original, applique ton association,
    #   et insère des portes SWAP (croix X sur la slide 8) chaque fois que deux qubits
    #   doivent interagir alors qu'ils ne sont pas voisins sur le graphe bleu.
    #   Le nouveau circuit obtenu (avec les SWAP ajoutés) s'appelle QC.

    return QC.depth()
    # ^ Calcule et renvoie la "profondeur" (depth = longueur, slides 8 et 9) du nouveau circuit QC.
    #   Plus ton association (mapping) est bonne, moins Qiskit a eu besoin d'ajouter de SWAP,
    #   et plus ce nombre renvoyé sera PETIT !
    #   Ton but dans StudentCode.py est de trouver la liste "mapping" qui donne le plus petit nombre possible.

