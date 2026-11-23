# -*- coding: utf-8 -*-
"""
Import automatique de tous les scripts du dossier Scripts.

Chaque fichier .py (sauf __init__.py) devient un sous-module du package,
accessible sous la forme : Scripts.<nom_du_fichier>

La fonction run(nom_du_script) exécute la fonction main() du script demandé.
"""

import importlib
import pkgutil

__all__ = ["run"]

_MODULES = {}

for _loader, _name, _ispkg in pkgutil.iter_modules(__path__):
    _module = importlib.import_module(f"{__name__}.{_name}")
    _MODULES[_name] = _module
    globals()[_name] = _module
    __all__.append(_name)


def run(name):
    """Exécute la fonction main() du script dont le nom est fourni."""
    if name not in _MODULES:
        available = ", ".join(sorted(_MODULES))
        raise ValueError(
            f"Script '{name}' introuvable. Scripts disponibles : {available}"
        )
    main = getattr(_MODULES[name], "main", None)
    if main is None:
        raise AttributeError(
            f"Le script '{name}' ne définit pas de fonction main()."
        )
    return main()


# Nettoyage des variables temporaires
del importlib, pkgutil, _loader, _name, _ispkg, _module
