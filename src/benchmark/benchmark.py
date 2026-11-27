# -*- coding: utf-8 -*-
import argparse
import csv
import inspect
import os
import statistics
import subprocess
import sys
from datetime import datetime

BENCHMARK_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(BENCHMARK_DIR)
SOLUTIONS_DIR = os.path.join(SRC_DIR, "solutions")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from report_generator import CSV_FIELDS, generate_html_report

# =======================================================
# 1. CONFIGURATION DU BENCHMARK (À MODIFIER SELON VOS BESOINS)
# =======================================================
NOM_GROUPE = "GroupeC"
INSTANCES_A_TESTER = [1, 2, 3, 4]             # Mets list(range(1, 10)) pour les 9 instances complètes
ALGORITHMES = None                            # None = détection auto dans Scripts/ (ou liste ex: ["genetique", "memetique"])
NB_RUNS = 3                                   # Nombre de répétitions par couple (algo, instance)
SAUVEGARDER_MEILLEURS_TXT = False             # True (ou --save-txt) pour générer les fichiers GroupeC_Challenge_X.txt
RUNS_DIR = os.path.join(BENCHMARK_DIR, "runs")
RAPPORT_HTML = os.path.join(BENCHMARK_DIR, "benchmark_report.html")


# =======================================================
# 2. DÉCOUVERTE DES ALGORITHMES & MÉTADONNÉES GIT
# =======================================================
def decouvrir_algorithmes(scripts_pkg, selection=None):
    """Retourne les algorithmes de Scripts/ compatibles avec main(inst, fitness, n, m)."""
    if selection:
        return list(selection)

    compatibles = []
    for nom, mod in sorted(scripts_pkg._MODULES.items()):
        main_fn = getattr(mod, "main", None)
        if not callable(main_fn):
            continue
        try:
            sig = inspect.signature(main_fn)
            params = list(sig.parameters.values())
            accepts_varargs = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)
            positional_count = sum(
                1 for p in params
                if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            )
            if accepts_varargs or positional_count >= 4:
                compatibles.append(nom)
        except (TypeError, ValueError):
            continue
    return compatibles


def _git_cmd(*args):
    try:
        res = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=3,
        )
        return res.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def collecter_metadonnees_version(note=""):
    """Collecte l'horodatage, l'auteur et les informations Git du lancement courant."""
    now = datetime.now()
    auteur = _git_cmd("config", "user.name") or os.environ.get("USER") or "unknown"
    branch = _git_cmd("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    commit = _git_cmd("rev-parse", "--short", "HEAD") or "unknown"
    porcelain = _git_cmd("status", "--porcelain")
    dirty = "dirty" if porcelain else "clean"

    return {
        "run_id": now.strftime("%Y-%m-%d_%Hh%Mm%S"),
        "timestamp_iso": now.isoformat(timespec="seconds"),
        "timestamp_label": now.strftime("%d/%m/%Y à %Hh%M"),
        "auteur": auteur,
        "git_branch": branch,
        "git_commit": commit,
        "git_dirty": dirty,
        "note": note.strip(),
    }


# =======================================================
# 3. GESTION DES RECORDS ET EXÉCUTION
# =======================================================
def lire_record_existant(inst):
    """Lit le meilleur coût déjà enregistré dans solutions/GroupeC_Challenge_inst.txt."""
    nom_fichier = os.path.join(SOLUTIONS_DIR, f"{NOM_GROUPE}_Challenge_{inst}.txt")
    if os.path.exists(nom_fichier):
        with open(nom_fichier, "r", encoding="utf-8") as f:
            ligne = f.read().strip().split()
            if ligne:
                return float(ligne[-1])
    return float("inf")


def sauvegarder_si_record(inst, mapping, cout):
    """Écrase le fichier de soumission uniquement si le nouveau coût est strictement meilleur."""
    ancien_record = lire_record_existant(inst)
    if cout < ancien_record:
        os.makedirs(SOLUTIONS_DIR, exist_ok=True)
        nom_fichier = os.path.join(SOLUTIONS_DIR, f"{NOM_GROUPE}_Challenge_{inst}.txt")
        contenu = " ".join(map(str, mapping)) + f" {cout}\n"
        with open(nom_fichier, "w", encoding="utf-8") as f:
            f.write(contenu)
        print(f"   [RECORD] Nouveau record sauvegardé dans solutions/{os.path.basename(nom_fichier)} : {cout} (ancien : {ancien_record})")


def lancer_benchmark(instances, algos, nb_runs, meta, save_txt=SAUVEGARDER_MEILLEURS_TXT):
    from source import instance_selector, fitness_inner
    import Scripts

    algos_a_lancer = decouvrir_algorithmes(Scripts, algos)
    if not algos_a_lancer:
        raise RuntimeError("Aucun algorithme compatible trouvé dans Scripts/.")

    os.makedirs(RUNS_DIR, exist_ok=True)
    safe_auteur = "".join(c if c.isalnum() or c in "-_" else "_" for c in meta["auteur"]).strip("_") or "user"
    run_csv_path = os.path.join(RUNS_DIR, f"{meta['run_id']}_{safe_auteur}.csv")

    resultats = []

    print("==========================================================")
    print(f"DÉMARRAGE DU BENCHMARK — Version {meta['timestamp_label']} ({meta['git_branch']} @ {meta['git_commit']})")
    print(f"{len(algos_a_lancer)} algos ({', '.join(algos_a_lancer)}) x {len(instances)} instances x {nb_runs} runs")
    if meta["note"]:
        print(f"Note : {meta['note']}")
    print("==========================================================")

    for inst in instances:
        backend, circuit, n, m = instance_selector(inst)
        print(f"\n>>> INSTANCE {inst} (n={n} qubits virtuels, m={m} qubits physiques) <<<")

        def fitness_inst(mapping):
            return fitness_inner(mapping, circuit, backend)

        for algo_name in algos_a_lancer:
            module_algo = getattr(Scripts, algo_name)
            couts_runs = []
            temps_runs = []
            evals_runs = []
            meilleur_mapping_algo = None
            meilleur_cout_algo = float("inf")
            nom_affiche_final = algo_name

            for r in range(1, nb_runs + 1):
                print(f"  -> [{algo_name}] Run {r}/{nb_runs}...", end=" ", flush=True)
                nom_affiche, mapping, cout, duree, nb_evals = module_algo.main(
                    inst, fitness_inst, n, m
                )
                nom_affiche_final = nom_affiche or algo_name
                couts_runs.append(cout)
                temps_runs.append(duree)
                evals_runs.append(nb_evals)

                if cout < meilleur_cout_algo:
                    meilleur_cout_algo = cout
                    meilleur_mapping_algo = list(mapping)

                print(f"Coût = {cout} | Temps = {duree:.2f}s | Évals Qiskit = {nb_evals}")

            cout_min = min(couts_runs)
            cout_max = max(couts_runs)
            cout_moy = sum(couts_runs) / nb_runs
            cout_std = statistics.stdev(couts_runs) if nb_runs > 1 else 0.0
            temps_moy = sum(temps_runs) / nb_runs
            temps_min = min(temps_runs)
            temps_max = max(temps_runs)
            evals_moy = sum(evals_runs) / nb_runs

            print(
                f"  [BILAN {algo_name} | Inst {inst}] "
                f"Best: {cout_min} | Moy: {cout_moy:.2f} (±{cout_std:.2f}) | Temps moy: {temps_moy:.2f}s"
            )

            if save_txt and meilleur_mapping_algo is not None:
                sauvegarder_si_record(inst, meilleur_mapping_algo, cout_min)

            ligne = {
                **meta,
                "nb_runs": nb_runs,
                "instance": inst,
                "n": n,
                "m": m,
                "algo": algo_name,
                "nom_affiche": nom_affiche_final,
                "cout_min": cout_min,
                "cout_moy": cout_moy,
                "cout_max": cout_max,
                "cout_std": cout_std,
                "temps_moy": temps_moy,
                "temps_min": temps_min,
                "temps_max": temps_max,
                "evals_moy": evals_moy,
                "meilleur_mapping": " ".join(map(str, meilleur_mapping_algo or [])),
            }
            resultats.append(ligne)

            # Sauvegarde incrémentale : fichier CSV dédié à ce run + HTML consolidé
            ajouter_a_historique_csv([ligne], run_csv_path)
            generate_html_report(RUNS_DIR, RAPPORT_HTML, nom_groupe=NOM_GROUPE, records_dir=SOLUTIONS_DIR)

    return run_csv_path


# =======================================================
# 4. SAUVEGARDE HISTORIQUE CSV & GÉNÉRATION DU RAPPORT HTML
# =======================================================
def ajouter_a_historique_csv(resultats, csv_path):
    """Ajoute les nouveaux résultats à l'historique CSV sans écraser les précédents."""
    if not resultats:
        return

    file_exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
    fieldnames = CSV_FIELDS
    if file_exists:
        with open(csv_path, "r", newline="", encoding="utf-8") as rf:
            existing_header = next(csv.reader(rf), None)
            if existing_header:
                fieldnames = existing_header

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerows(resultats)


def parser_args():
    parser = argparse.ArgumentParser(description="Benchmark comparatif & suivi de versions.")
    parser.add_argument("--instances", nargs="+", type=int, default=INSTANCES_A_TESTER, help="Liste des instances (ex: 1 2 3 4)")
    parser.add_argument("--algos", nargs="+", default=ALGORITHMES, help="Liste des algos dans Scripts/ (défaut: auto)")
    parser.add_argument("--runs", type=int, default=NB_RUNS, help="Nombre de runs par couple (algo, instance)")
    parser.add_argument("--note", type=str, default="", help="Note/label pour identifier cette version")
    parser.add_argument("--save-txt", action="store_true", default=SAUVEGARDER_MEILLEURS_TXT, help="Met à jour les fichiers GroupeC_Challenge_X.txt")
    parser.add_argument("--report-only", action="store_true", help="Régénère uniquement le HTML depuis l'historique CSV")
    return parser.parse_args()


if __name__ == "__main__":
    args = parser_args()
    if not args.report_only:
        meta = collecter_metadonnees_version(note=args.note)
        run_csv = lancer_benchmark(args.instances, args.algos, args.runs, meta, save_txt=args.save_txt)
        print(f"\nRun sauvegardé dans : {run_csv}")

    out_html = generate_html_report(RUNS_DIR, RAPPORT_HTML, nom_groupe=NOM_GROUPE, records_dir=SOLUTIONS_DIR)
    print(f"Dashboard HTML dynamique généré : {out_html}")
