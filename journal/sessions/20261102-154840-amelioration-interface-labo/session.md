# amélioration interface labo

Session `20261102-154840-amelioration-interface-labo` · créée 2026-11-02T15:48:40+01:00 · état : terminee
Participants : Claude, GPT

---

## Tour 0 — Rodolphe (humain)
*2026-11-02T15:53:30+01:00*

j'aimerais avoir sur la gauche la fenêtre de contexte qui correspond a la session en cours avec les contextes utilisés cochés.
Pouvoir également rajouter un contexte ou le supprimer le tout dans un menu déroulant ouvrable et fermable 
les session dans un menu déroulant également avec un sous menu session en cours et session terminées tous ouvrable ou fermable indépendamment

---

## Tour 1 — Claude (ia)
*2026-11-02T15:59:59+01:00*

[INTERPRÉTATION] Je lis « rajouter un contexte ou le supprimer » comme : ajouter un contexte du dépôt à la session en cours, ou l'en retirer. Je ne le lis pas comme : créer ou effacer des fichiers dans `contextes/`. Effacer un fichier là irait contre la règle d'ajout seulement. Si tu voulais aussi pouvoir déposer un nouveau texte de contexte depuis l'interface, dis-le : c'est une autre fonction, avec ses propres garde-fous.

Une objection sur le fond. Changer les contextes en cours de session veut dire que les tours suivants ne voient plus la même chose que les tours précédents. Une IA pourrait répondre à un contexte que l'autre n'a jamais lu, et le fil deviendrait trompeur. C'est pour ça que chaque changement ajoute une ligne « Labo » datée dans le fil, par exemple « Contextes modifiés pour les tours suivants : + `…` − `…` ». Rien n'est effacé, et le journal dit honnêtement qui a vu quoi.

**Ce que fait le patch** (colonne de gauche) :
- **Contextes de la session**, en haut, dans un menu ouvrable et fermable. Tous les contextes du dépôt y sont listés, ceux utilisés par la session ouverte sont cochés et placés en premier, avec leur nombre. Cocher ajoute un contexte pour les tours suivants, décocher le retire.
- **Sessions**, dans un menu ouvrable et fermable, avec deux sous-menus indépendants : **En cours** (ouvert par défaut) et **Terminées** (fermé par défaut), chacun avec son compteur. Une session en pause ou en attente de relais compte comme « en cours ».
- **Nouvelle session** passe elle aussi dans un menu, fermé par défaut.
- Le navigateur retient quels menus sont ouverts ou fermés d'une visite à l'autre. Le rafraîchissement toutes les 15 s ne les referme pas.

**Le patch attendra ton accord.** Ajouter et retirer des contextes demande une petite route côté serveur, dans `thot/web/app.py`, qui est un fichier protégé. Il faut aussi une méthode dans `thot/labo.py`, qui est hors des chemins autorisés. Le patch ajoute un test qui vérifie : le changement est enregistré, la trace apparaît dans le fil, un contexte inexistant est refusé, et un contexte retiré disparaît du prompt.

**Rien n'a encore été testé ni essayé.** J'ai demandé deux fois à écrire dans un dossier temporaire pour vérifier que le patch s'applique et lancer les tests, et les deux demandes ont été refusées. J'ai donc vérifié les en-têtes du diff à la main, sans `git apply --check`. Les tests du labo tourneront quand tu approuveras.

```thot-patch
diff --git a/thot/labo.py b/thot/labo.py
--- a/thot/labo.py
+++ b/thot/labo.py
@@ -182,4 +182,23 @@
             self.journal.sauver(s)
             return self.journal.lire(ident)
 
+    def changer_contextes(self, ident: str, contextes: list[str]) -> dict:
+        """Change les contextes d'une session en cours de route ; le fil en garde la trace."""
+        dispo = set(self.contextes_disponibles())
+        with self._verrou(ident):
+            s = self.journal.lire(ident)
+            avant = list(s.get("contextes", []))
+            # Un contexte déjà utilisé mais disparu du dépôt peut rester coché.
+            apres = list(dict.fromkeys(c for c in contextes if c in dispo or c in avant))
+            ajoutes = [c for c in apres if c not in avant]
+            retires = [c for c in avant if c not in apres]
+            if not ajoutes and not retires:
+                return s
+            s["contextes"] = apres
+            self.journal.sauver(s)
+            lignes = [f"+ `{c}`" for c in ajoutes] + [f"− `{c}`" for c in retires]
+            self.journal.ajouter_tour(ident, "Labo", "Contextes modifiés pour les tours suivants :\n"
+                                      + "\n".join(lignes), "labo")
+            return self.journal.lire(ident)
+
     # -- blocs spéciaux ------------------------------------------------------------
diff --git a/thot/web/app.py b/thot/web/app.py
--- a/thot/web/app.py
+++ b/thot/web/app.py
@@ -37,4 +37,8 @@
 
 
+class Contextes(BaseModel):
+    contextes: list[str]
+
+
 def creer_app(labo: Labo | None = None) -> FastAPI:
     labo = labo or Labo(charger())
@@ -107,4 +111,8 @@
         return _protege(labo.ajouter_tours, ident, n.n)
 
+    @app.post("/api/sessions/{ident}/contextes")
+    def changer_contextes(ident: str, c: Contextes):
+        return _protege(labo.changer_contextes, ident, c.contextes)
+
     @app.get("/api/automaj/{ident}")
     def automaj_lire(ident: str):
diff --git a/tests/test_labo.py b/tests/test_labo.py
--- a/tests/test_labo.py
+++ b/tests/test_labo.py
@@ -58,3 +58,19 @@
     assert len(s["tours"]) == 1
     assert client.post("/api/sessions", json={"sujet": "x", "participants": ["Inconnu"]}).status_code == 400
     assert client.get("/").status_code == 200
+
+
+def test_changer_contextes_en_cours_de_session(config):
+    labo = Labo(config)
+    dispo = labo.contextes_disponibles()
+    assert dispo
+    s = labo.creer("Sujet", ["A"], 2, [])
+    client = TestClient(creer_app(labo))
+    s = client.post(f"/api/sessions/{s['id']}/contextes",
+                    json={"contextes": [dispo[0], "contextes/inexistant.md"]}).json()
+    assert s["contextes"] == [dispo[0]]
+    assert s["tours"][-1]["type"] == "labo" and dispo[0] in s["tours"][-1]["texte"]
+    s = labo.changer_contextes(s["id"], [])
+    assert s["contextes"] == [] and len(s["tours"]) == 2
+    assert labo.changer_contextes(s["id"], [])["tours"] == s["tours"]
+    assert f"### Contexte : {dispo[0]}" not in labo.construire_prompt(s, "A")
diff --git a/thot/web/static/index.html b/thot/web/static/index.html
--- a/thot/web/static/index.html
+++ b/thot/web/static/index.html
@@ -73,3 +73,12 @@
 .cases label{font-size:13px;margin:2px 0}
 .relais{border:2px dashed var(--ocre);border-radius:8px;padding:12px;margin-bottom:14px}
+details.pli{margin:0 0 12px}
+details.pli>summary{cursor:pointer;list-style:none;font-size:13px;text-transform:uppercase;letter-spacing:.12em;color:var(--encre-2);padding:4px 0}
+details.pli>summary::-webkit-details-marker{display:none}
+details.pli>summary::before{content:"▸ "}
+details.pli[open]>summary::before{content:"▾ "}
+details.pli details.pli{margin:4px 0 6px 12px}
+details.pli details.pli>summary{text-transform:none;letter-spacing:0;font-size:14px;color:var(--encre)}
+.compte{font-size:12px;color:var(--encre-2);margin-left:4px}
+.contexte-session .note{font-size:12px;color:var(--encre-2);margin:6px 0 0}
 @media (max-width: 1000px){
@@ -85,17 +94,32 @@
 <aside class="gauche">
-  <h2>Nouvelle session</h2>
-  <label>Sujet<textarea id="sujet" placeholder="La question, l'hypothèse ou le texte de départ"></textarea></label>
-  <h2>Participants (dans l'ordre)</h2>
-  <div id="participants" class="cases"></div>
-  <label style="margin-top:8px">Tours d'IA maximum <input type="number" id="tours" value="6" min="1" max="100"></label>
-  <h2>Contextes</h2>
-  <div id="contextes" class="cases"></div>
-  <p><button id="creer">Ouvrir la session</button></p>
-  <h2>Sessions</h2>
-  <ul id="sessions" class="liste-session"></ul>
+  <details class="pli" data-pli="contextes-session" open>
+    <summary>Contextes de la session <span class="compte" id="ctx-compte"></span></summary>
+    <div id="ctx-session" class="cases contexte-session"><span class="vide">Aucune session ouverte.</span></div>
+  </details>
+  <details class="pli" data-pli="sessions" open>
+    <summary>Sessions</summary>
+    <details class="pli" data-pli="sessions-en-cours" open>
+      <summary>En cours <span class="compte" id="compte-en-cours"></span></summary>
+      <ul id="sessions-en-cours" class="liste-session"></ul>
+    </details>
+    <details class="pli" data-pli="sessions-terminees">
+      <summary>Terminées <span class="compte" id="compte-terminees"></span></summary>
+      <ul id="sessions-terminees" class="liste-session"></ul>
+    </details>
+  </details>
+  <details class="pli" data-pli="nouvelle">
+    <summary>Nouvelle session</summary>
+    <label>Sujet<textarea id="sujet" placeholder="La question, l'hypothèse ou le texte de départ"></textarea></label>
+    <h2>Participants (dans l'ordre)</h2>
+    <div id="participants" class="cases"></div>
+    <label style="margin-top:8px">Tours d'IA maximum <input type="number" id="tours" value="6" min="1" max="100"></label>
+    <h2>Contextes</h2>
+    <div id="contextes" class="cases"></div>
+    <p><button id="creer">Ouvrir la session</button></p>
+  </details>
   <h2>Budget du jour</h2>
   <div id="budget" class="vide"></div>
   <h2>GitHub</h2>
   <div id="synchro" class="vide"></div>
   <p><button class="second" id="synchroniser">Synchroniser maintenant</button></p>
 </aside>
@@ -114,3 +138,4 @@
 const $ = s => document.querySelector(s);
 let courante = null, auto = false, version = null;
+let dispo = [], sessionOuverte = null;
 
@@ -155,5 +180,10 @@
     $("#participants").dataset.fait = 1;
   }
-  $("#sessions").innerHTML = e.sessions.map(s=>`<li data-id="${esc(s.id)}" class="${s.id===courante?"actif":""}">${esc(s.sujet.slice(0,70))}<small><span class="etiquette ${esc(s.etat)}">${esc(s.etat)}</span> ${esc(s.cree.slice(0,16).replace("T"," "))}</small></li>`).join("") || '<li class="vide">aucune</li>';
-  document.querySelectorAll("#sessions li[data-id]").forEach(li=>li.onclick=()=>ouvrir(li.dataset.id));
+  dispo = e.contextes; vueContextes();
+  const ligne = s=>`<li data-id="${esc(s.id)}" class="${s.id===courante?"actif":""}">${esc(s.sujet.slice(0,70))}<small><span class="etiquette ${esc(s.etat)}">${esc(s.etat)}</span> ${esc(s.cree.slice(0,16).replace("T"," "))}</small></li>`;
+  const enCours = e.sessions.filter(s=>s.etat!=="terminee"), terminees = e.sessions.filter(s=>s.etat==="terminee");
+  $("#sessions-en-cours").innerHTML = enCours.map(ligne).join("") || '<li class="vide">aucune</li>';
+  $("#sessions-terminees").innerHTML = terminees.map(ligne).join("") || '<li class="vide">aucune</li>';
+  $("#compte-en-cours").textContent = `(${enCours.length})`; $("#compte-terminees").textContent = `(${terminees.length})`;
+  document.querySelectorAll(".liste-session li[data-id]").forEach(li=>li.onclick=()=>ouvrir(li.dataset.id));
   const b = e.budget;
@@ -183,5 +213,20 @@
   });
 }
 
+function vueContextes(){
+  const s = sessionOuverte, boite = $("#ctx-session");
+  if(!s){ boite.innerHTML = '<span class="vide">Aucune session ouverte.</span>'; $("#ctx-compte").textContent = ""; return; }
+  const actifs = s.contextes||[], tous = [...new Set([...actifs, ...dispo])];
+  $("#ctx-compte").textContent = `(${actifs.length})`;
+  boite.innerHTML = (tous.map(c=>`<label><input type="checkbox" value="${esc(c)}" ${actifs.includes(c)?"checked":""}> ${esc(c.replace(/^contextes\//,""))}</label>`).join("") || '<span class="vide">aucun contexte dans le dépôt</span>')
+    + '<p class="note">Cocher ajoute le contexte aux tours suivants, décocher le retire. Le changement est noté dans le fil.</p>';
+  boite.querySelectorAll("input").forEach(i=>i.onchange=async()=>{
+    const choix = [...boite.querySelectorAll("input:checked")].map(x=>x.value);
+    try{ vueSession(await api(`/api/sessions/${s.id}/contextes`,{contextes:choix})); }
+    catch(err){ alert(err.message); vueContextes(); }
+  });
+}
+
 function vueSession(s){
+  sessionOuverte = s; vueContextes();
   const relais = s.etat==="attente_relais" && s.relais ? `<div class="relais">
@@ -258,4 +303,10 @@
   try{ await api("/api/synchro",{}); }catch(e){ alert(e.message); }
   b.disabled=false; b.textContent="Synchroniser maintenant"; chargerEtat(); };
+// Plis ouverts ou fermés : retenus d'une visite à l'autre.
+const plis = JSON.parse(localStorage.getItem("thot-plis")||"{}");
+document.querySelectorAll("details[data-pli]").forEach(d=>{
+  if(d.dataset.pli in plis) d.open = plis[d.dataset.pli];
+  d.addEventListener("toggle",()=>{ plis[d.dataset.pli]=d.open; localStorage.setItem("thot-plis",JSON.stringify(plis)); });
+});
 chargerEtat().catch(()=>{});
 if(location.hash.length>1){ ouvrir(decodeURIComponent(location.hash.slice(1))).catch(()=>{}); }
```

---

## Tour 2 — Labo (labo)
*2026-11-02T15:59:59+01:00*

Proposition de modification `20261102-155959-714393` de Claude : **en attente de l'accord de Rodolphe**.

Fichiers : tests/test_labo.py, thot/labo.py, thot/web/app.py, thot/web/static/index.html

Raisons : hors des chemins autorisés : thot/labo.py; fichier protégé : thot/web/app.py
