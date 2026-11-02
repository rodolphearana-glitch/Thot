"""Fournisseurs de modèles : Claude, GPT, IA locale (Ollama), relais manuel."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

import httpx

from ..config import Config, Participant


@dataclass
class Reponse:
    texte: str
    tokens: int = 0


class AttenteRelais(Exception):
    """Le participant est en relais manuel : Rodolphe doit coller la réponse."""


class ErreurProvider(Exception):
    pass


DELAI_S = 600.0
DELAI_CLI_S = 1800


def _anthropic(p: Participant, cle: str, systeme: str, prompt: str) -> Reponse:
    if not cle:
        raise ErreurProvider("Pas de clé Anthropic dans thot.config.toml.")
    r = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": cle,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": p.modele,
            "max_tokens": 8000,
            "system": systeme,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=DELAI_S,
    )
    if r.status_code >= 400:
        raise ErreurProvider(f"Anthropic {r.status_code} : {r.text[:500]}")
    d = r.json()
    texte = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
    u = d.get("usage", {})
    return Reponse(texte, int(u.get("input_tokens", 0)) + int(u.get("output_tokens", 0)))


def _openai(p: Participant, cle: str, systeme: str, prompt: str) -> Reponse:
    if not cle:
        raise ErreurProvider("Pas de clé OpenAI dans thot.config.toml.")
    if not p.modele or p.modele == "A_RENSEIGNER":
        raise ErreurProvider("Renseigne le nom du modèle GPT dans thot.config.toml.")
    r = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {cle}", "content-type": "application/json"},
        json={
            "model": p.modele,
            "messages": [
                {"role": "system", "content": systeme},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=DELAI_S,
    )
    if r.status_code >= 400:
        raise ErreurProvider(f"OpenAI {r.status_code} : {r.text[:500]}")
    d = r.json()
    texte = d["choices"][0]["message"].get("content") or ""
    return Reponse(texte, int(d.get("usage", {}).get("total_tokens", 0)))


def _ollama(p: Participant, systeme: str, prompt: str) -> Reponse:
    url = (p.url or "http://localhost:11434").rstrip("/")
    try:
        r = httpx.post(
            f"{url}/api/chat",
            json={
                "model": p.modele,
                "stream": False,
                "messages": [
                    {"role": "system", "content": systeme},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=DELAI_S,
        )
    except httpx.ConnectError as e:
        raise ErreurProvider(
            f"Ollama injoignable à {url}. Est-il lancé ? ({e})"
        ) from e
    if r.status_code >= 400:
        raise ErreurProvider(f"Ollama {r.status_code} : {r.text[:500]}")
    d = r.json()
    tokens = int(d.get("prompt_eval_count", 0)) + int(d.get("eval_count", 0))
    return Reponse(d.get("message", {}).get("content", ""), tokens)


NO_WINDOW = 0x08000000 if os.name == "nt" else 0
MOTS_LIMITE = ("usage limit", "rate limit", "limit reached", "limite d'utilisation", "quota")


def trouver_claude() -> str | None:
    """Claude Code installé sur le PC (même recherche que Studio TLS)."""
    trouve = shutil.which("claude")
    if trouve:
        return trouve
    maison = os.path.expanduser("~")
    for c in (os.path.join(maison, ".local", "bin", "claude.exe"),
              os.path.join(maison, ".local", "bin", "claude"),
              os.path.join(os.environ.get("APPDATA", ""), "npm", "claude.cmd"),
              os.path.join(maison, ".claude", "local", "claude")):
        if c and os.path.isfile(c):
            return c
    return None


def _executer(commande: list[str], entree: str, racine: Path, env=None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(commande, input=entree, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", cwd=racine, env=env, timeout=DELAI_CLI_S,
                              creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired as e:
        raise ErreurProvider(f"Pas de réponse après {DELAI_CLI_S} s.") from e
    except OSError as e:
        raise ErreurProvider(str(e)[:300]) from e


def _claude_code(p: Participant, systeme: str, prompt: str, racine: Path) -> Reponse:
    """Claude Code du PC, connecté au compte Claude (abonnement) : aucune clé d'API.

    Lecture seule : il peut lire le dépôt (contextes, expériences) mais ne modifie rien ; les modifications
    passent par les blocs thot-patch et l'auto-mise à jour."""
    exe = trouver_claude()
    if not exe:
        raise ErreurProvider("Claude Code introuvable sur ce PC (le même que celui du Studio TLS).")
    commande = [exe, "-p", "--output-format", "json", "--allowedTools", "Read,Glob,Grep",
                "--append-system-prompt", systeme]
    if p.modele:
        commande += ["--model", p.modele]
    # La connexion du compte, jamais une clé d'API qui traînerait dans l'environnement.
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    fait = _executer(commande, prompt, racine, env)
    try:
        res = json.loads(fait.stdout or "{}")
    except ValueError:
        res = {"result": fait.stdout}
    texte = (res.get("result") or "").strip()
    bilan = (texte + " " + fait.stderr).lower()
    if "not logged in" in bilan or "/login" in bilan:
        raise ErreurProvider("Claude Code n'est pas connecté au compte (lance `claude` une fois pour te connecter).")
    if any(m in bilan for m in MOTS_LIMITE) and (fait.returncode != 0 or res.get("is_error")):
        raise ErreurProvider("Limite d'utilisation de Claude atteinte : " + (texte or fait.stderr)[:300])
    if fait.returncode != 0 or res.get("is_error") or not texte:
        raise ErreurProvider("Claude Code : " + (texte or fait.stderr.strip()[:300] or f"code {fait.returncode}"))
    u = res.get("usage") or {}
    return Reponse(texte, int(u.get("input_tokens", 0) or 0) + int(u.get("output_tokens", 0) or 0))


def _codex(p: Participant, systeme: str, prompt: str, racine: Path) -> Reponse:
    """Codex du PC, connecté au compte ChatGPT : aucune clé d'API. Bac à sable en lecture seule."""
    exe = shutil.which("codex")
    if not exe:
        raise ErreurProvider("Codex introuvable sur ce PC (commande « codex » absente, la même que pour le Studio TLS).")
    dossier = racine / ".thot"
    dossier.mkdir(exist_ok=True)
    sortie = dossier / f"codex-{os.getpid()}-{threading.get_ident()}.txt"
    if sortie.exists():
        sortie.unlink()
    commande = [exe, "exec", "--skip-git-repo-check", "-C", str(racine), "--sandbox", "read-only",
                "-o", str(sortie)]
    if p.modele:
        commande += ["-m", p.modele]
    commande.append("-")
    fait = _executer(commande, f"{systeme}\n\n---\n\n{prompt}", racine)
    texte = sortie.read_text(encoding="utf-8", errors="replace").strip() if sortie.exists() else ""
    if sortie.exists():
        sortie.unlink()
    bilan = (fait.stderr + fait.stdout).lower()
    if not texte and any(m in bilan for m in MOTS_LIMITE):
        raise ErreurProvider("Limite d'utilisation de Codex atteinte : " + (fait.stderr or fait.stdout).strip()[-300:])
    if fait.returncode != 0 or not texte:
        raise ErreurProvider("Codex : " + ((fait.stderr or fait.stdout).strip()[-300:] or f"code {fait.returncode}"))
    return Reponse(texte, 0)


def _lmstudio(p: Participant, systeme: str, prompt: str) -> Reponse:
    """Modèle chargé dans LM Studio (serveur local compatible OpenAI, sans clé)."""
    url = (p.url or "http://localhost:1234").rstrip("/")
    try:
        r = httpx.post(f"{url}/v1/chat/completions", json={
            "model": p.modele,
            "messages": [{"role": "system", "content": systeme}, {"role": "user", "content": prompt}],
        }, timeout=DELAI_S)
    except httpx.ConnectError as e:
        raise ErreurProvider(f"LM Studio injoignable à {url} : lance son serveur local (onglet Developer).") from e
    if r.status_code >= 400:
        raise ErreurProvider(f"LM Studio {r.status_code} : {r.text[:500]}")
    d = r.json()
    texte = d["choices"][0]["message"].get("content") or ""
    return Reponse(texte, int(d.get("usage", {}).get("total_tokens", 0) or 0))


def _echo(p: Participant, systeme: str, prompt: str) -> Reponse:
    """Provider factice, pour les tests et les essais sans clé."""
    derniere = prompt.strip().splitlines()[-1] if prompt.strip() else ""
    return Reponse(f"[{p.nom} en mode écho] J'ai bien reçu le tour. Dernière ligne : {derniere}", 0)


def appeler(config: Config, p: Participant, systeme: str, prompt: str) -> Reponse:
    if p.provider == "claude":
        return _claude_code(p, systeme, prompt, config.racine)
    if p.provider == "codex":
        return _codex(p, systeme, prompt, config.racine)
    if p.provider == "anthropic":
        return _anthropic(p, config.cle("anthropic"), systeme, prompt)
    if p.provider == "openai":
        return _openai(p, config.cle("openai"), systeme, prompt)
    if p.provider == "ollama":
        return _ollama(p, systeme, prompt)
    if p.provider == "lmstudio":
        return _lmstudio(p, systeme, prompt)
    if p.provider == "echo":
        return _echo(p, systeme, prompt)
    if p.provider == "manuel":
        raise AttenteRelais(p.nom)
    raise ErreurProvider(f"Provider inconnu : {p.provider}")
