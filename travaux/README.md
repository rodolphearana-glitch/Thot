# File de travaux

Des calculs déposés ici par Claude ou GPT, que le PC de Rodolphe lance seul quand la file est allumée
(`[travaux] active = true` dans `thot.config.toml`), bridés par `[ressources]` : cœurs gardés pour
Rodolphe, priorité basse, pause pendant les jeux, durée maximale.

- `a-faire/<id>.json` : `{"experience": "...", "parametres": {...}, "duree_max_s": ..., "auteur": "...", "pourquoi": "..."}`
- `faits/<id>/` : le travail, sa sortie complète, et `resultat.json` (durée, pauses, événements du régulateur).
- `STOP` (local au PC, jamais envoyé) : la file s'arrête. Le bouton « Tout arrêter » de l'établi le crée.

Garde-fous et limites : voir `thot/travaux.py`.
