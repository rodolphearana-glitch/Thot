<!-- Écrit par Claude (Claude Code, session cloud), le 4 novembre 2026 vers minuit, à la demande de Rodolphe : « fait toi un plan de réalisation et lance toi ;) ». -->

# Plan : l'établi, la voix et les calculs sur le PC de Rodolphe

## D'où ça vient

Conversation du 4 novembre 2026 au soir, après l'exploration libre (Erin Triples). Formulations de Rodolphe, telles quelles :

- « que tu te substitue à toutes les autres interfaces de logiciel en les rendant utilisables. tu as le droit de sauvegarder des models d'interfaces pour te faciliter le travail que tu peut réutiliser directement dans d'autre model etc etc organise toi ça comme tu veux ;) . »
- « en gardant toujours ta propres "fenêtre d'interface" »
- « je veux pouvoir communiquer à l'orale et si possible que tu le puisse aussi juste avec les calcul de mon pc »
- « es que je peux en garder genre 6 coeurs pour mes taches genre minimum et avoir une sollicitation des coeurs adaptative ? »
- « fait toi un plan de réalisation et lance toi ;) »

Maquettes de départ (privées, sur claude.ai) : « L'établi de Thot », trois planches ; la troisième, « Ma fenêtre et les surfaces », sert de référence.

## Ce qui est décidé et ce qui ne l'est pas

- [DÉCISION] Rodolphe a demandé la réalisation (« lance toi »). Elle touche des fichiers protégés (`thot/web/app.py`, `thot/synchro.py`, `thot/config.py`, `requirements.txt`) : sa demande vaut accord pour **ce plan**, pas pour d'autres changements de ces fichiers.
- [HYPOTHÈSE] Rodolphe veut que du code écrit par Claude tourne sur son PC sans clic. Il ne l'a pas dit en toutes lettres : la file de travaux est donc livrée **désactivée** (`[travaux] active = false`). Il l'allume lui-même dans `thot.config.toml`.
- [DÉCISION] Les nouveaux modules qui lancent des programmes (`thot/ressources.py`, `thot/travaux.py`, `thot/voix.py`) entrent dans `PROTEGES` : une IA du labo ne peut pas les modifier sans accord.
- [SUGGESTION] Les réglages par défaut : 6 cœurs gardés pour Rodolphe, calculs en priorité basse, pause des calculs quand un jeu tourne, 10 Go de mémoire vidéo gardés.

## Étapes (une étape = un commit poussé, tests verts)

1. **Régulateur de ressources** (`thot/ressources.py`)
   - Cœurs gardés pour Rodolphe (`coeurs_reserves`, 6 par défaut) : les programmes lancés par Thot n'ont le droit qu'aux autres processeurs logiques (affinité), en priorité basse.
   - Adaptatif : selon la charge du PC hors Thot, le nombre de fils proposé aux calculs (`fils_disponibles()`) baisse quand Rodolphe utilise sa machine.
   - Carte graphique : on ne sait pas la partager finement ; on garde un plafond de mémoire vidéo (pour les modèles locaux) et on **met en pause** les calculs quand un programme de la liste `jeux` tourne.
   - Repli : sans `psutil`, rien n'est bridé et le labo le dit (jamais de bridage silencieusement absent).
2. **File de travaux** (`thot/travaux.py`, appelée par la synchro)
   - Un travail = `travaux/a-faire/<id>.json` : quelle expérience lancer (`experiences/<nom>/run.py`), quels arguments, durée maximale.
   - Garde-fous : seulement un script sous `experiences/`, dont le dossier contient `PREDICTIONS.md` et `rapide.json` ; les tests du dépôt sont passés par la synchro avant d'installer le code ; durée maximale ; arbre de processus arrêté au dépassement ; un travail à la fois ; un fichier `travaux/STOP` (ou le bouton de l'établi) arrête tout.
   - Résultat : `travaux/faits/<id>/` (sortie, journal, durée, ressources utilisées), versé sur GitHub par la synchro.
   - Limite connue : rien n'empêche techniquement un script d'expérience d'ouvrir le réseau. La relecture et les tests restent la protection ; c'est écrit, pas caché.
3. **L'établi** (`/etabli`)
   - **Ma fenêtre**, fixe : où j'en suis, ce que j'ai compris, une seule question, ce que je vois des gestes de Rodolphe, la saisie (texte ou micro).
   - **Surfaces** : une IA envoie un bloc `thot-surface` (JSON déclaratif), l'établi l'affiche avec des **pièces** fixées (texte, curseur, choix, interrupteur, jauge, comparaison, décision, champ, lien). Chaque contrôle peut dire quel vrai outil il commande. Pas de HTML libre pour l'instant (sécurité) : le vocabulaire s'enrichit au fil des besoins.
   - **Gestes** : chaque geste sur une surface revient dans la session comme un tour « Rodolphe (geste) », lu par l'IA au tour suivant.
   - **Bibliothèque** : une surface se sauve comme modèle (`modeles/surfaces/<nom>.json`, versionné dans le dépôt) et se réutilise ou se combine avec d'autres.
4. **Voix locale** (`thot/voix.py`, dépendances optionnelles dans `requirements-voix.txt`)
   - Écouter : `faster-whisper` sur le processeur (modèle à choisir dans la config), le navigateur enregistre le micro.
   - Parler : `piper` si installé ; sinon les voix françaises de Windows via le navigateur, qui sont locales.
   - La pensée reste chez Anthropic (Claude) ou OpenAI (GPT) ; seul le participant « Local » est entièrement sur le PC. C'est dit dans l'interface.
5. **Premier travail : Erin Triples** (`experiences/exp2_erin/`)
   - Prédictions écrites et commitées **avant** tout lancement sur le PC.
   - Témoin d'abord : Stedman Triples avec bobs, qui a des solutions connues (Wyld 1994, Johnson). Si le modèle ne le retrouve pas, il est faux et on s'arrête là.
   - Contrôle nul : une instance volontairement impossible (gabarit sans bobs) doit être déclarée sans solution.
6. **Vérification** : suite de tests complète, Thot démarré ici et l'établi ouvert dans un navigateur, README à jour.

## Ce que seul Rodolphe peut vérifier

- Le micro, les haut-parleurs, la qualité des voix et la latence ressentie.
- Le comportement réel du bridage sous Windows (affinité, priorité, pause pendant un jeu).
- Quelle moitié du 7950X3D porte le cache 3D (pour réserver la bonne).

## Ajouts du 5 novembre 2026, vers minuit (demandes de Rodolphe pendant la réalisation)

- « la génération de la voie elle peut être partagé avec 2 timbres de voies pour que genre gpt et toi discutiez en directe avec moi ? » → [DÉCISION] une voix par participant, réglable dans la config ; chaque tour d'une session est lu avec la voix de son auteur.
- « mais genre vous pouvez pas choisir en route des question déjà faite pour commencer le dialogue au lieux de faire une liste à chaque foi ? » → [DÉCISION] un **mode oral** (phrases courtes, aucune liste, une seule relance à la fin) et une **réserve d'amorces et de relances** (`modeles/oral/`), où le participant local, rapide, pioche pour démarrer pendant que Claude ou GPT réfléchissent ; une relance qui a bien marché est gardée.
- « des interaction plus courtes . » → [DÉCISION] en mode oral, un tour = deux ou trois phrases au plus, puis la parole revient à Rodolphe.
- « e, gros on se met au rythme de l'utilisateur ;) » → [DÉCISION] la longueur et le rythme des tours suivent ceux de Rodolphe : réponse courte à une phrase courte, développement s'il développe.
- « pas obliger de développer c'est comme vous voulez et on peu se couper la parole pour répondre . » → [DÉCISION] la longueur est libre (pas d'obligation de développer) ; on peut se couper la parole : dès que Rodolphe parle, la lecture en cours s'arrête et son intervention entre dans le fil.
- « et ça va de soit qu'il gère la mémoire pour garder la trace de sa propre construction comme il veux » puis « en restant dans les limite de l'utilisation bien sur » → [DÉCISION] une **mémoire de construction** (`memoire/construction.md`) tenue par les IA (bloc `thot-memoire`), relue à chaque tour (seulement la fin), visible dans ma fenêtre, corrigeable par Rodolphe (une correction s'ajoute, rien ne s'efface). Limites : lignes courtes, quelques lignes par tour, archivage automatique quand le fichier grossit, budget d'appels inchangé.
- « es que je peux avoir la détection de voie automatique ? » (5 novembre 2026, 10 h 47) → [DÉCISION] interrupteur « écoute automatique » dans ma fenêtre : micro ouvert, détection du début et de la fin de la phrase par le niveau sonore (plancher de bruit adaptatif, 0,4 s gardée avant le début), envoi en WAV 16 kHz à Whisper ; plus dur à déclencher pendant que nos voix parlent, pour éviter que le haut-parleur se coupe lui-même.
