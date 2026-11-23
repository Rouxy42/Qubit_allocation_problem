# -*- coding: utf-8 -*-
"""
Created on Tue Nov 14 11:08:40 2023

@author: Jérôme
"""

from source import instance_selector, fitness_inner

##-------------------------------------------------------
##     Definition de la fonction objetif à minimiser
##-------------------------------------------------------
def fitness(mapping):
    return fitness_inner(mapping, circuit, backend)

##-------------------------------------------------------
##     Pour choisir une instance: 
##     Modifier instance_num ET RIEN D'AUTRE   
##     La fonction instance_selector revoie n et m
##     ainsi que "backend" et "circuit" qui sont 
##     utiliser dans la fonction objectif (voir fitness) 
##-------------------------------------------------------
instance_num=1     #### Entre 1 et 9 inclue

backend,circuit,n,m = instance_selector(instance_num)

##-------------------------------------------------------
##     A vous de jouer !  
##-------------------------------------------------------

###### Votre code ici

###### A faire : un algorithme d'optimisation qui minimise la fonction fitness,
###### Cette fonction qui accepte en entrée :
###### une liste de n parmi m (n<=m) entiers deux à deux distincts
###### N'oubliez pas d'écrire la solution dans Groupe[numero_du_groupe]_Instance_[instance_num].txt

###### /!\ Attention /!\
###### Il est possible que la ligne 122 de code source.py : qasmfile=f".\Instances\{l.rstrip()}.qasm"
###### crée un problème à l'execution si le chemin n'est pas le bon,
###### en particulier sous Linux. Essayer de la remplacer par
###### qasmfile=f"./Instances/{l.rstrip()}.qasm". Cela devrait résoudre le problème.

from Scripts import *

# Notez ici le nom du fichier que vous voulez executer !
run("example")


    
