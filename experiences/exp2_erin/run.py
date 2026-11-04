"""Expérience 2 : Erin Triples With Bobs (problème ouvert, Lindoff 1908 ; Knuth, avril 2026).

Trouver les 5 040 ordres de 7 cloches, chacun une fois, en suivant un gabarit fixe où l'on ne choisit
qu'une chose tous les six changements : « normal » (place 7) ou « bob » (place 5).

Méthodes (paramètre "methode") :
- "stedman" : TÉMOIN. Stedman Triples avec bobs, même machinerie, sixes rapides et lents alternés.
  Des solutions sont connues (Wyld 1994, Johnson, Saddleton). Si le modèle ne le résout pas, ce n'est
  pas une preuve qu'il est faux, mais ses résultats sur Erin ne valent plus rien.
- "erin"    : le problème ouvert, sixes tous identiques (3.1.3.1.3 puis 7 ou 5).
- "nul"     : CONTRÔLE NUL. Erin sans bob : impossible (une course régulière ne fait que 7 sixes).
  Contrôle faible : l'impossibilité se voit dès le graphe (rangées inatteignables), sans le solveur.

Le solveur est CP-SAT (OR-Tools), contrainte de circuit unique avec nœuds facultatifs : un nœud par
(tête de six, sorte de six), chaque rangée couverte par exactement un nœud actif. Toute solution trouvée est
revérifiée indépendamment en sonnant les 5 040 rangées.

Sortie : dernière ligne JSON. Fils : paramètre "fils", sinon THOT_FILS (donné par le régulateur de Thot).
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path


def echange(paires):
    p = list(range(7))
    for a, b in paires:
        p[a - 1], p[b - 1] = p[b - 1], p[a - 1]
    return tuple(p)


P1 = echange([(2, 3), (4, 5), (6, 7)])
P3 = echange([(1, 2), (4, 5), (6, 7)])
P5 = echange([(1, 2), (3, 4), (6, 7)])
P7 = echange([(1, 2), (3, 4), (5, 6)])
RAPIDE = (P3, P1, P3, P1, P3)
LENT = (P1, P3, P1, P3, P1)


def appliquer(rangee, ch):
    return tuple(rangee[ch[i]] for i in range(7))


def six(tete, sorte):
    rangees, r = [tete], tete
    for c in (RAPIDE if sorte == 0 else LENT):
        r = appliquer(r, c)
        rangees.append(r)
    return rangees, r


def graphe(methode):
    """Nœuds (tête, sorte) atteignables depuis les rangées initiales ; successeurs (normal, bob)."""
    alterne = methode == "stedman"
    fins = (P7,) if methode == "nul" else (P7, P5)
    depart = (tuple(range(7)), 0)
    noeuds, a_voir = {}, [depart]
    while a_voir:
        n = a_voir.pop()
        if n in noeuds:
            continue
        rangees, derniere = six(*n)
        sorte_suiv = (1 - n[1]) if alterne else n[1]
        succ = [(appliquer(derniere, f), sorte_suiv) for f in fins]
        noeuds[n] = (frozenset(rangees), succ)
        a_voir.extend(succ)
    return depart, noeuds


def resoudre(methode, duree_s, fils):
    from ortools.sat.python import cp_model
    depart, noeuds = graphe(methode)
    liste = list(noeuds)
    idx = {n: i for i, n in enumerate(liste)}
    blocs = {}
    for n, (rs, _) in noeuds.items():
        blocs.setdefault(rs, []).append(n)
    par_rangee = {}
    for n, (rs, _) in noeuds.items():
        for r in rs:
            par_rangee.setdefault(r, []).append(n)
    couvertes = len(par_rangee)
    if couvertes < 5040:
        # Certaines rangées ne sont dans aucun six atteignable : impossible, sans même lancer le solveur.
        return {"noeuds": len(liste), "blocs": len(blocs), "rangees_couvertes": couvertes,
                "statut": "INFEASIBLE", "raison": "rangées inatteignables", "temps_s": 0.0}
    m = cp_model.CpModel()
    arcs, actif, arc_var = [], {}, {}
    for n in liste:
        for k, s in enumerate(noeuds[n][1]):
            v = m.NewBoolVar("")
            arc_var[(n, k)] = v
            arcs.append((idx[n], idx[s], v))
        saute = m.NewBoolVar("")
        actif[n] = saute.Not()
        arcs.append((idx[n], idx[n], saute))
    # Chaque rangée est sonnée exactement une fois (formulation générale : vaut aussi quand les sixes
    # ne forment pas des blocs disjoints).
    for ns in par_rangee.values():
        m.AddExactlyOne([actif[n] for n in set(ns)])
    # Par symétrie (renommer les cloches ne change rien), on peut supposer que les rangées initiales
    # ouvrent un six ; pour Stedman, ce six peut être rapide ou lent.
    ronds = [n for n in liste if n[0] == depart[0]]
    m.AddBoolOr([actif[n] for n in ronds])
    m.AddCircuit(arcs)
    sv = cp_model.CpSolver()
    sv.parameters.max_time_in_seconds = float(duree_s)
    sv.parameters.num_workers = int(fils)
    t = time.time()
    st = sv.Solve(m)
    res = {"noeuds": len(liste), "blocs": len(blocs), "rangees_couvertes": couvertes,
           "statut": sv.StatusName(st), "temps_s": round(time.time() - t, 1)}
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        depart = next(n for n in ronds if sv.Value(actif[n]))
        res["sorte_initiale"] = "rapide" if depart[1] == 0 else "lent"
        appels, n = [], depart
        while True:
            k = next(k for k in range(len(noeuds[n][1])) if sv.Value(arc_var[(n, k)]))
            appels.append(k)
            n = noeuds[n][1][k]
            if n == depart:
                break
        res["appels"] = "".join("-B"[k] for k in appels)
        res["bobs"] = sum(appels)
        res["verifie"] = verifier(methode, appels, depart[1])
    return res


def verifier(methode, appels, sorte_initiale=0):
    """Sonne la composition rangée par rangée : 5 040 rangées distinctes et retour aux rangées initiales."""
    vues, tete, sorte = set(), tuple(range(7)), sorte_initiale
    for k in appels:
        rangees, derniere = six(tete, sorte)
        vues.update(rangees)
        tete = appliquer(derniere, P5 if k else P7)
        if methode == "stedman":
            sorte = 1 - sorte
    return len(vues) == 5040 and len(appels) * 6 == 5040 and tete == tuple(range(7)) and sorte == sorte_initiale


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    p = json.loads(ap.parse_args().params)
    methode = p.get("methode", "stedman")
    if methode not in ("stedman", "erin", "nul"):
        raise SystemExit(f"méthode inconnue : {methode}")
    fils = int(p.get("fils") or os.environ.get("THOT_FILS") or os.cpu_count() or 1)
    duree = float(p.get("duree_s", 600))
    print(f"exp2_erin : {methode}, {fils} fils, {duree:.0f} s au plus", flush=True)
    res = {"experience": "exp2_erin", "methode": methode, "fils": fils, "duree_max_s": duree,
           "quand": datetime.now().isoformat(timespec="seconds"), **resoudre(methode, duree, fils)}
    if p.get("sauver", True):
        d = Path(__file__).parent / "resultats"
        d.mkdir(exist_ok=True)
        (d / f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}-{methode}.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "appels"}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
