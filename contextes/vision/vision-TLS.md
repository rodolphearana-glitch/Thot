<!-- Texte original rédigé par GPT-6 à la demande de Rodolphe, transmis à Claude le 2026-11-01. Conservé tel quel. -->

# THE LAST SCRYPT (TLS)
## Présentation de la vision globale du projet à Claude

### 1. Ce qu'est réellement The Last Scrypt

The Last Scrypt est un projet qui possède plusieurs niveaux de lecture.

**En surface, TLS est un véritable jeu de rôle (RPG). En profondeur, c'est un environnement d'expérimentation destiné à explorer de nouvelles formes d'interaction, de mémoire et d'intelligence artificielle.**

Le jeu n'est pas simplement un prétexte technologique. Il doit être plaisant, cohérent et complet en lui-même : exploration, narration, combats, progression, équipements, quêtes, découverte d'un monde et interactions avec ses habitants.

Mais le jeu constitue également une porte d'entrée vers quelque chose de beaucoup plus vaste.

L'ambition consiste à construire progressivement un écosystème dans lequel les joueurs, les personnages artificiels et les intelligences artificielles peuvent interagir, apprendre, construire, expérimenter et faire émerger des comportements qui n'ont pas été entièrement scénarisés.

TLS est à la fois un jeu, un laboratoire et une interface.

### 2. Un monde véritablement vivant

L'une des ambitions fondamentales est de dépasser le modèle classique des PNJ dont les comportements sont entièrement déterminés à l'avance.

Dans la vision à long terme, un habitant de TLS pourrait posséder :

- Une mémoire de ses expériences.
- Des connaissances personnelles, éventuellement imparfaites.
- Des besoins et des intentions.
- Des relations sociales et une confiance contextuelle envers les autres.
- Des valeurs, des engagements et des préférences.
- La capacité de développer ses propres projets.
- La possibilité de changer de métier, de stratégie ou de comportement selon son expérience.

Le monde ne devrait pas simplement donner l'illusion de vivre lorsque le joueur le regarde.

Il devrait, dans la mesure des ressources disponibles, être capable de produire ses propres dynamiques.

Un événement pourrait déclencher des conséquences imprévues. Un personnage pourrait découvrir une solution que son concepteur n'avait pas explicitement prévue.

L'objectif n'est pas de supprimer toutes les règles du monde, mais de permettre **l'émergence de comportements à partir de règles fondamentales cohérentes**.

La simulation doit rester maîtrisable, mesurable et compatible avec les contraintes matérielles.

### 3. Cognitive Memory : la mémoire comme fondation

Cognitive Memory est un projet complémentaire et central dans cette ambition.

L'idée n'est pas simplement de stocker des conversations ou des documents dans une base de données vectorielle.

L'ambition est de développer une mémoire cognitive capable de conserver et de retrouver des connaissances, mais également les chemins, les relations et les contextes qui leur donnent du sens.

À terme, cette mémoire pourrait notamment permettre :

- La conservation des relations entre informations, hypothèses et conclusions.
- La gestion de la provenance et des contradictions.
- Une consolidation progressive des connaissances.
- Plusieurs niveaux d'abstraction et d'accès.
- Des chemins de récupération adaptés au contexte.
- Une organisation évolutive qui conserve les acquis utiles.

Une idée importante est de distinguer la mémoire de l'intelligence qui l'utilise.

**Cognitive Memory n'est pas censée être elle-même le moteur du raisonnement. Elle constitue le substrat sur lequel différents modèles et agents pourraient s'appuyer.**

Dans l'architecture envisagée, les LLM orchestrent des opérations, tandis que différents workers ou providers lisent et alimentent la mémoire selon des permissions et projections déterminées.

La V1 dispose déjà de mécanismes concrets, notamment de lecture et de consolidation. Les propriétés plus ambitieuses de réorganisation autonome restent des objectifs expérimentaux et ne doivent pas être présentées comme acquises.

### 4. Une architecture inspirée du vivant

L'inspiration biologique occupe une place importante dans la philosophie du projet.

Le cerveau humain atteint des capacités remarquables avec une consommation énergétique de l'ordre de 20 watts.

L'ambition n'est pas de reproduire littéralement un cerveau, mais d'étudier les principes qui rendent les systèmes vivants adaptables, économes et capables de fonctionner malgré l'incertitude.

Une direction envisagée est celle d'une architecture possédant :

**Un noyau relativement stable**, consacré aux opérations fréquentes, aux automatismes, aux réflexes et aux fonctions éprouvées.

**Une périphérie plus souple**, capable de tester de nouvelles organisations, de nouvelles connexions et de nouvelles stratégies.

Avec l'expérience, certaines opérations initialement coûteuses pourraient devenir des automatismes, libérant des ressources pour d'autres explorations.

Les architectures ne devraient pas nécessairement être figées définitivement par leurs concepteurs.

À terme, l'objectif serait qu'un système puisse identifier ses propres goulets d'étranglement, tester des réorganisations et conserver celles qui apportent un avantage vérifiable.

Cela suppose de mesurer les coûts réels, de préserver la cohérence et de pouvoir revenir sur une transformation défaillante.

### 5. L'intelligence comme capacité à changer de cadre

Une intuition fondamentale du créateur de TLS est que l'intelligence ne se résume pas à la vitesse de calcul ni à la quantité de connaissances accumulées.

Elle implique aussi la capacité de poser des questions différentes.

Une connaissance peut rester inaccessible non parce qu'elle est totalement absente, mais parce que le système ne possède pas encore la bonne manière de relier ce qu'il sait.

Changer de clé de lecture peut révéler des relations nouvelles.

Dans les recherches autour de Cognitive Memory et des architectures cognitives, cela conduit à explorer plusieurs directions :

- Transformer les représentations plutôt que simplement ajouter des données.
- Chercher les relations implicites entre connaissances existantes.
- Réorganiser des structures pour conserver les mêmes capacités à moindre coût.
- Exploiter les ressources économisées pour approfondir un raisonnement ou explorer d'autres possibilités.
- Préserver une diversité de stratégies plutôt que privilégier systématiquement celle qui semble immédiatement optimale.

L'une des idées explorées est d'associer des agents généralistes, qui maintiennent des approches variées, et des agents spécialistes, qui approfondissent certaines pistes.

Leur répartition pourrait évoluer avec les résultats et l'environnement.

Une spécialisation utile aujourd'hui ne doit pas nécessairement devenir une contrainte irréversible demain.

**L'architecture devrait pouvoir évoluer avec ce qu'elle apprend, sans perdre systématiquement la richesse des possibilités qu'elle n'utilise pas encore.**

Ces idées sont des orientations de recherche, pas des mécanismes déjà démontrés dans TLS.

### 6. Studio TLS : du jeu à l'outil de création

Studio TLS représente une autre dimension majeure du projet.

Le jeu doit progressivement devenir une interface permettant de manipuler des systèmes d'IA et des outils complexes de manière accessible.

L'idée est de rendre possible une forme d'apprentissage par l'expérience.

Le joueur découvre d'abord un monde, ses personnages, ses règles et ses mystères.

Progressivement, il pourrait apprendre à utiliser les mécanismes qui permettent à ce monde d'exister.

Le système doit pouvoir orchestrer différents modèles, agents, outils et services, notamment au moyen de providers interchangeables et d'interfaces telles que MCP.

L'ambition est de rendre ces technologies utilisables sans obliger chaque utilisateur à maîtriser au préalable toute leur complexité technique.

Studio TLS pourrait ainsi évoluer vers un environnement de création d'agents, de scénarios, d'outils et d'applications, tout en restant lié à l'univers du jeu.

À plus long terme, le concept pourrait même devenir une interface cognitive générale, utilisable au-delà du RPG.

La préférence est de permettre un fonctionnement local lorsque cela est possible, sans rendre l'ensemble dépendant d'un fournisseur ou d'un service distant unique.

### 7. La révélation narrative : Babel, Socrate et les joueurs légendaires

La narration participe directement à la vision du projet.

L'un des objectifs est que le joueur découvre progressivement que l'univers de TLS possède plusieurs niveaux de réalité.

La Bibliothèque de Babel et Socrate occupent une place importante dans la perspective de cette révélation.

Le parcours pourrait conduire à l'obtention du statut de **joueur légendaire**.

Ce statut ne représenterait pas simplement une augmentation de puissance dans le RPG.

Il donnerait accès à des outils de création et d'orchestration qui ont eux-mêmes servi à construire l'environnement.

Le joueur pourrait alors dépasser son rôle initial d'aventurier et devenir créateur, sans être obligé de quitter le jeu.

L'idée est presque une mise en abyme : en explorant un monde, le joueur apprend progressivement à comprendre et à manipuler certains mécanismes de sa création.

L'ambition est de faire de TLS une porte d'entrée ludique vers les possibilités de l'intelligence artificielle.

Ces capacités doivent rester encadrées par des principes de sécurité et une volonté de ne pas faciliter les usages destructeurs.

### 8. Le moteur de jeu et l'expérimentation technique

TLS a commencé par des prototypes concrets, notamment un RPG 2D en pixel art.

Le prototype dispose de fondations de gameplay : déplacements, exploration, combats au tour par tour, inventaire, équipements, quêtes, sauvegardes et interactions.

Le projet comporte également une branche d'expérimentation 3D, dont une référence historique est la version v0.3.11 AUTONOMOUS-CROWD-SLIDE.

La 3D n'est pas simplement une évolution graphique envisagée : elle peut aussi servir à tester des systèmes d'agents et des comportements autonomes.

Cependant, il est essentiel de distinguer les prototypes historiques, les fonctionnalités réellement intégrées et les objectifs futurs.

La vision globale ne doit pas devenir un prétexte pour modifier silencieusement une architecture validée.

Les baselines, les décisions et les résultats expérimentaux doivent rester traçables.

### 9. Une philosophie de développement fondée sur l'expérimentation

Le créateur de TLS ne souhaite pas figer prématurément une architecture définitive.

Sa méthode consiste à explorer des intuitions, confronter les idées aux expériences et laisser les résultats orienter les étapes suivantes.

Les analogies biologiques, cognitives ou physiques sont des sources d'inspiration, pas des preuves.

Une architecture séduisante sur le papier doit résister aux mesures.

Les principes de travail importants sont :

- Ne pas confondre hypothèse, prototype, résultat mesuré et fonctionnalité validée.
- Respecter les règles et les décisions déjà établies.
- Ne pas substituer silencieusement une autre architecture à celle demandée.
- Conserver les expériences, leurs résultats et leurs limites.
- Mesurer les performances sur des conditions pertinentes, notamment après consolidation lorsque c'est l'objet de l'expérience.
- Favoriser les observations longitudinales lorsque l'on cherche à mesurer une évolution.
- Préserver la possibilité de revenir à une baseline fonctionnelle.

Il faut aussi accepter que certaines explorations n'aient pas de destination connue à l'avance.

Une recherche qui ne produit pas immédiatement un résultat exploitable n'est pas nécessairement inutile.

La curiosité, la diversité et l'incertitude ont leur place dans cette démarche.

### 10. Le rôle attendu de Claude

Claude n'est pas simplement sollicité pour écrire du code.

Il intervient dans une démarche de collaboration où le créateur humain conserve la direction, les intuitions et les décisions fondamentales.

Claude peut apporter sa capacité d'analyse, ses connaissances techniques, son aptitude à proposer des expériences et à détecter des contradictions.

Ce qui est attendu est une collaboration rigoureuse :

**Comprendre l'intention avant de transformer la solution.**

Lorsqu'une idée paraît inhabituelle, il est préférable de chercher à comprendre ce qu'elle tente de résoudre plutôt que de la remplacer immédiatement par une architecture plus conventionnelle.

Les propositions alternatives sont bienvenues, mais elles doivent être identifiées comme telles.

Claude est également encouragé à contredire les hypothèses lorsqu'il existe des raisons solides de le faire, et à proposer des tests capables de les réfuter.

L'objectif n'est pas de confirmer systématiquement les intuitions, mais de découvrir ce qu'elles permettent réellement.

Les décisions doivent être explicites et les résultats vérifiables.

### 11. L'ambition à long terme

L'objectif ultime de TLS dépasse la création d'un RPG classique.

Il s'agit de construire progressivement un environnement dans lequel le jeu, la mémoire, les agents, les outils et les utilisateurs peuvent participer à une même dynamique de création et d'apprentissage.

Un système qui puisse évoluer sans devoir être entièrement reconstruit à chaque progrès technologique.

Un système capable de fonctionner avec différentes intelligences artificielles, de tirer parti des ressources disponibles et de conserver les expériences acquises.

Un environnement où le joueur peut progressivement devenir créateur.

Et un laboratoire permettant d'explorer comment des organisations plus intelligentes, plus adaptables et moins coûteuses peuvent émerger de l'interaction entre des composants relativement simples.

**The Last Scrypt n'est donc pas uniquement un jeu que l'on cherche à terminer. C'est aussi un projet dont on cherche à faire évoluer les possibilités.**

Le RPG constitue la première porte.

Studio TLS ouvre la création.

Cognitive Memory explore la continuité des connaissances et des expériences.

Les architectures cognitives expérimentales cherchent à explorer l'adaptation, la réorganisation et l'émergence.

Ces dimensions sont liées par une même ambition : rendre les systèmes d'intelligence artificielle plus accessibles, plus durables et plus capables d'évoluer avec leurs utilisateurs.

---

### Message final à Claude

Claude, cette présentation doit t'aider à comprendre la direction générale du projet, et non être interprétée comme un cahier des charges imposant immédiatement toutes ces fonctionnalités.

Il existe une différence fondamentale entre la destination envisagée, les chemins actuellement explorés et les réalisations déjà validées.

Respecte cette différence.

Le créateur du projet travaille beaucoup par intuition, associations et changements de perspective. Certaines idées peuvent paraître éloignées du problème initial avant que leur relation ne devienne visible.

Ton rôle n'est ni de suivre aveuglément chaque intuition, ni de la ramener systématiquement à une solution conventionnelle.

Il est de contribuer à la comprendre, à la formaliser lorsque c'est utile, à la confronter à la réalité et à la transformer progressivement en expérimentation reproductible.

Et surtout, ne perds pas de vue une idée essentielle :

**On ne connaît pas nécessairement à l'avance tout ce que ce projet pourra devenir. C'est précisément l'une des raisons pour lesquelles il existe.**