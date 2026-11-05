# Mémoire de construction de Thot

Tenue par les IA du labo (bloc thot-memoire), en ajout seulement. Rodolphe y signale les lignes fausses.

- 2026-11-05 (Claude) L'établi (/etabli) est né d'une demande de Rodolphe : une fenêtre fixe pour l'IA, des surfaces composées au besoin, une bibliothèque de modèles.
- 2026-11-05 (Claude) Les surfaces n'acceptent que des pièces connues (thot/surfaces.py), jamais de HTML venant d'une IA.
- 2026-11-05 (Claude) Les calculs passent par le régulateur : 6 cœurs gardés pour Rodolphe, priorité basse, pause pendant ses jeux.
- 2026-11-05 (Claude) La file de travaux est livrée éteinte : c'est Rodolphe qui l'allume.
- 2026-11-05 (Claude) Erin Triples : témoin Stedman d'abord ; Erin seulement si le témoin est résolu et vérifié.
- 2026-11-05 (Claude) 2026-11-05 (Claude) Rodolphe trouve la voix de Windows robotique et trop lente : lecture passée à 1,25 par défaut, voix naturelles locales en priorité ; Piper reste la vraie piste.
- 2026-11-05 (Claude) 2026-11-05 (Claude) CORRECTION : Thot parle déjà avec Piper ; le côté robotique vient de la voix Piper choisie, pas des voix de Windows.
- 2026-11-05 (Claude) 2026-11-05 (Claude) Piège : l'archive de la mémoire était nommée à la seconde près, deux archives dans la même seconde faisaient échouer les tests.
- 2026-11-05 (Claude) 2026-11-05 (Claude) CORRECTION de la correction : le paquet piper est installé mais aucune voix .onnx (pas de modeles/voix, pas de [voix] dans la config) ; la page lit encore avec Windows.
- 2026-11-05 (Claude) 2026-11-05 (Claude) Rodolphe ne voyait pas les cartes sous le chat : demande de les afficher dans le fil de conversation.
- 2026-11-05 (Claude) 2026-11-05 (Claude) Téléchargement de la voix Siwis accepté par Rodolphe mais bloqué par les permissions de Claude Code (curl vers huggingface.co).
- 2026-11-05 (Claude) 2026-11-05 (Claude) Claude Code lancé par Thot refuse les commandes non autorisées sans rien montrer à Rodolphe : pas de fenêtre d'autorisation, il faut ajouter la permission à l'avance ou qu'il lance la commande lui-même.
- 2026-11-05 (Claude) 2026-11-05 (Claude) Dans un tour de session, même l'écriture d'un fichier neuf à la racine du dépôt et Invoke-WebRequest sont refusés : Claude ne peut rien installer, seulement proposer (patch, codage, surface).
- 2026-11-05 (Claude) 2026-11-05 (Claude) Le oui de Rodolphe aux droits de téléchargement ne suffit pas : il faut que Thot lance Claude Code avec la permission (codage demandé) ; modeles/voix encore refusé ensuite.
- 2026-11-05 (Claude) 2026-11-05 (Claude) Rodolphe trouve les réponses lentes : chaque tour relance Claude Code depuis zéro avec toute la session ; éviter d'essayer des outils quand une réponse simple suffit.
- 2026-11-05 (Claude) 2026-11-05 (Claude) Rodolphe veut que Claude garde le contexte comme dans un chat : codage demandé pour reprendre la conversation Claude Code (--resume) au lieu de tout relancer à chaque tour.
- 2026-11-05 (Claude) 2026-11-05 (Claude) Rodolphe : le contexte complet de Thot ne doit être relu que s'il y a besoin, avec des règles pour ça ; il signale un « petit couac » de mélange avec le projet Thot (à préciser).
- 2026-11-05 (Claude) 2026-11-05 (Claude) Rodolphe : la conversation orale est un fonctionnement à part, une discussion avec Claude et GPT sans relire le contexte des sessions de Thot (codage demandé).
- 2026-11-05 (Claude) 2026-11-05 (Claude) La voix Siwis est dans modeles/voix ; il manque "*" = "fr_FR-siwis-medium.onnx" sous [voix.participants] dans thot.config.toml, et modeles/voix/ dans le .gitignore.
- 2026-11-05 (Claude) 2026-11-05 (Claude) Un geste sur une carte ne relançait pas les IA : codage demandé pour que les décisions déclenchent un tour.
- 2026-11-05 (Claude) 2026-11-05 (Claude) Claude ne peut pas modifier thot.config.toml dans un tour de session (écriture refusée) ; Rodolphe colle lui-même [voix.participants] en fin de fichier.
