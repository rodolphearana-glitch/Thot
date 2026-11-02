"""Expérience 1 — Une relation déductible est-elle accessible par une simple transformation ?

Version 0 (numpy pur, tourne sur n'importe quel PC, sans carte graphique).

Monde synthétique : N entités (0..N-1). Les relations de base sont des décalages
r_s(i) = i + s mod N. Un petit réseau apprend toutes les relations de base, puis on le gèle.

Question (l'exemple A→B→C de Rodolphe) : la relation composée c(i) = i + a + b n'a jamais été
apprise, mais elle est déductible (appliquer a puis b). Peut-on la lire dans le réseau gelé
avec une petite transformation linéaire T de son état interne, apprise sur la moitié des
entités et testée sur l'autre moitié ?

Conditions :
  structure   cible = vraie composition, réseau entraîné          (l'hypothèse)
  nulle       cible = permutation aléatoire, réseau entraîné      (doit échouer : sinon fuite)
  temoin      cible = vraie composition, réseau NON entraîné      (contrôle « le savoir est-il
                                                                    dans T ou dans le réseau ? »)
Référence : enchaîner explicitement deux passages dans le réseau (calcul à deux sauts).

Sortie : un rapport lisible, puis une dernière ligne JSON avec tous les chiffres.
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np

DEFAUTS = {
    "graine": 0,
    "N": 61,                    # nombre d'entités (premier : la structure cyclique est propre)
    "decalages": [1, 2, 5, 7, 13, 20],
    "a": 5, "b": 7,             # la composition testée : +12, absente des relations de base
    "d": 32, "cache": 128,
    "pas_modele": 4000, "pas_T": 3000,
    "rangs": [1, 2, 4, 8, 16, 32],
    "decroissance": 1e-3,
}


# ---------------------------------------------------------------------------- outils
class Adam:
    def __init__(self, params, lr=3e-3):
        self.p, self.lr = params, lr
        self.m = {k: np.zeros_like(v) for k, v in params.items()}
        self.v = {k: np.zeros_like(v) for k, v in params.items()}
        self.t = 0

    def pas(self, grads, decroissance=0.0):
        self.t += 1
        for k, g in grads.items():
            g = g + decroissance * self.p[k]
            self.m[k] = 0.9 * self.m[k] + 0.1 * g
            self.v[k] = 0.999 * self.v[k] + 0.001 * g * g
            mh = self.m[k] / (1 - 0.9 ** self.t)
            vh = self.v[k] / (1 - 0.999 ** self.t)
            self.p[k] -= self.lr * mh / (np.sqrt(vh) + 1e-8)


def softmax_ce(logits, cibles):
    z = logits - logits.max(1, keepdims=True)
    p = np.exp(z)
    p /= p.sum(1, keepdims=True)
    perte = -np.log(p[np.arange(len(cibles)), cibles] + 1e-12).mean()
    dz = p.copy()
    dz[np.arange(len(cibles)), cibles] -= 1
    return perte, dz / len(cibles)


# ---------------------------------------------------------------------------- modèle
def init_modele(rng, N, R, d, h):
    s = lambda *f: rng.normal(0, 1 / np.sqrt(f[0]), f)
    return {"E": s(N, d), "Rv": s(R, d), "W": s(2 * d, h), "bW": np.zeros(h),
            "U": s(h, N), "bU": np.zeros(N)}


def etat_interne(m, tetes, rels):
    x = np.concatenate([m["E"][tetes], m["Rv"][rels]], 1)
    return x, np.tanh(x @ m["W"] + m["bW"])


def entrainer_modele(m, tetes, rels, cibles, pas, decroissance):
    opt = Adam(m)
    for _ in range(pas):
        x, z = etat_interne(m, tetes, rels)
        logits = z @ m["U"] + m["bU"]
        _, dl = softmax_ce(logits, cibles)
        g = {"U": z.T @ dl, "bU": dl.sum(0)}
        dz = (dl @ m["U"].T) * (1 - z * z)
        g["W"], g["bW"] = x.T @ dz, dz.sum(0)
        dx = dz @ m["W"].T
        d = m["E"].shape[1]
        g["E"] = np.zeros_like(m["E"]); np.add.at(g["E"], tetes, dx[:, :d])
        g["Rv"] = np.zeros_like(m["Rv"]); np.add.at(g["Rv"], rels, dx[:, d:])
        opt.pas(g, decroissance)


def predire(m, tetes, rels):
    _, z = etat_interne(m, tetes, rels)
    return (z @ m["U"] + m["bU"]).argmax(1)


# ---------------------------------------------------------------------------- transformation
def apprendre_T(rng, m, rel_source, tetes_app, cibles_app, rang, pas):
    """T = A·B (rang k), appliquée à l'état interne z(tête, relation a) ; U et le reste sont gelés."""
    h = m["W"].shape[1]
    T = {"A": rng.normal(0, 0.1, (h, rang)), "B": rng.normal(0, 0.1, (rang, h)) + 0.0}
    _, z = etat_interne(m, tetes_app, np.full(len(tetes_app), rel_source))
    opt = Adam(T)
    for _ in range(pas):
        zt = z @ T["A"] @ T["B"]
        logits = zt @ m["U"] + m["bU"]
        _, dl = softmax_ce(logits, cibles_app)
        dzt = dl @ m["U"].T
        g = {"B": (z @ T["A"]).T @ dzt, "A": z.T @ (dzt @ T["B"].T)}
        opt.pas(g, 1e-4)
    return T


def precision_T(m, T, rel_source, tetes, cibles):
    _, z = etat_interne(m, tetes, np.full(len(tetes), rel_source))
    return float(((z @ T["A"] @ T["B"] @ m["U"] + m["bU"]).argmax(1) == cibles).mean())


# ---------------------------------------------------------------------------- expérience
def lancer(p: dict) -> dict:
    debut = time.time()
    rng = np.random.default_rng(p["graine"])
    # Sources de hasard séparables ; absentes, tout suit « graine » exactement comme avant.
    rng_partage = np.random.default_rng(p["graine_partage"]) if p.get("graine_partage") is not None else rng
    rng_T = np.random.default_rng(p["graine_T"]) if p.get("graine_T") is not None else rng
    N, S = p["N"], list(p["decalages"])
    ia, ib = S.index(p["a"]), S.index(p["b"])
    compo = (np.arange(N) + p["a"] + p["b"]) % N
    if (p["a"] + p["b"]) % N in [s % N for s in S]:
        raise ValueError("La composition ne doit pas déjà être une relation de base.")

    tetes = np.repeat(np.arange(N), len(S))
    rels = np.tile(np.arange(len(S)), N)
    cibles = (tetes + np.array(S)[rels]) % N

    entraine = init_modele(rng, N, len(S), p["d"], p["cache"])
    entrainer_modele(entraine, tetes, rels, cibles, p["pas_modele"], p["decroissance"])
    temoin = init_modele(rng, N, len(S), p["d"], p["cache"])  # jamais entraîné

    precision_base = float((predire(entraine, tetes, rels) == cibles).mean())
    inter = predire(entraine, np.arange(N), np.full(N, ia))
    deux_sauts = float((predire(entraine, inter, np.full(N, ib)) == compo).mean())

    ordre = rng_partage.permutation(N)
    app, test = ordre[: N // 2], ordre[N // 2:]
    nulle = rng_partage.permutation(N)

    conditions = {
        "structure": (entraine, compo),
        "nulle": (entraine, nulle),
        "temoin": (temoin, compo),
    }
    resultats = {}
    for nom, (modele, cible) in conditions.items():
        resultats[nom] = {}
        for k in p["rangs"]:
            T = apprendre_T(rng_T, modele, ia, app, cible[app], k, p["pas_T"])
            resultats[nom][str(k)] = {
                "app": precision_T(modele, T, ia, app, cible[app]),
                "test": precision_T(modele, T, ia, test, cible[test]),
                "parametres_T": int(T["A"].size + T["B"].size),
            }

    nb_params_modele = int(sum(v.size for v in entraine.values()))
    return {
        "parametres": p,
        "hasard": 1 / N,
        "precision_relations_de_base": precision_base,
        "reference_deux_sauts": deux_sauts,
        "parametres_modele": nb_params_modele,
        "resultats": resultats,
        "duree_s": round(time.time() - debut, 1),
    }


def rapport(r: dict) -> str:
    L = [
        "Expérience 1 — relation composée lue par une transformation de rang k",
        f"  hasard = {r['hasard']:.3f} | relations de base apprises : {r['precision_relations_de_base']:.3f}"
        f" | référence deux sauts : {r['reference_deux_sauts']:.3f}"
        f" | paramètres du modèle : {r['parametres_modele']}",
        "",
        "  précision sur les entités tenues à l'écart (test) :",
        "  rang k   " + "".join(f"{c:>12}" for c in r["resultats"]),
    ]
    for k in r["resultats"]["structure"]:
        ligne = f"  {k:>6}   " + "".join(
            f"{r['resultats'][c][k]['test']:>12.3f}" for c in r["resultats"])
        L.append(ligne + f"   (T = {r['resultats']['structure'][k]['parametres_T']} paramètres)")
    L.append(f"\n  durée : {r['duree_s']} s")
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}", help="JSON des paramètres à changer")
    args = ap.parse_args()
    params = {**DEFAUTS, **json.loads(args.params)}
    res = lancer(params)
    print(rapport(res))
    print(json.dumps(res, ensure_ascii=False))
