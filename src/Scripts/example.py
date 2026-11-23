# Déclarez ici les fonctions que vous utilisez pour créer l'algorithme
def somme(param1, param2):
    return param1+param2

def difference(param1, param2):
    return param1-param2

# Déclarez ici la logique qui appelle vos fonctions et vos paramètres
def main():
    a = 3
    b = 4
    print(f"La somme de {a} et {b} vaut {somme(a, b)}")
    print(f"La différence de {a} et {b} vaut {difference(a, b)}")

if __name__ == "__main__":
    main()
