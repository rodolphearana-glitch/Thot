"""Fournisseurs de modèles : Claude, GPT, IA locale (Ollama), relais manuel."""
from __future__ import annotations

from dataclasses import dataclass

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


def _echo(p: Participant, systeme: str, prompt: str) -> Reponse:
    """Provider factice, pour les tests et les essais sans clé."""
    derniere = prompt.strip().splitlines()[-1] if prompt.strip() else ""
    return Reponse(f"[{p.nom} en mode écho] J'ai bien reçu le tour. Dernière ligne : {derniere}", 0)


def appeler(config: Config, p: Participant, systeme: str, prompt: str) -> Reponse:
    if p.provider == "anthropic":
        return _anthropic(p, config.cle("anthropic"), systeme, prompt)
    if p.provider == "openai":
        return _openai(p, config.cle("openai"), systeme, prompt)
    if p.provider == "ollama":
        return _ollama(p, systeme, prompt)
    if p.provider == "echo":
        return _echo(p, systeme, prompt)
    if p.provider == "manuel":
        raise AttenteRelais(p.nom)
    raise ErreurProvider(f"Provider inconnu : {p.provider}")
