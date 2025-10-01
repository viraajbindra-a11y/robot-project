"""Adapters that shape chatbot responses to match WALL·E-like personality."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

Persona = Dict[str, str]
ResponseHook = Callable[[str, Persona], str]


@dataclass
class PersonalityAdapter:
    persona: Persona
    response_hook: Optional[ResponseHook] = None

    def apply(self, message: str) -> str:
        styled = self._apply_base_style(message)
        if self.response_hook:
            styled = self.response_hook(styled, self.persona)
        return styled

    def _apply_base_style(self, message: str) -> str:
        tone = self.persona.get('tone', 'playful')
        catchphrase = self.persona.get('catchphrase', '')
        prefix = self.persona.get('prefix', 'WALL-E:')
        suffix = f" {catchphrase}" if catchphrase else ''
        if tone == 'sarcastic':
            message = f"Oh sure, {message.lower()}"
        elif tone == 'excited':
            message = f"{message}!"
        return f"{prefix} {message}{suffix}"


DEFAULT_PERSONA: Persona = {
    'tone': 'sarcastic',
    'catchphrase': "Directive?",
    'prefix': 'WALL-E',
}


def load_persona_from_file(path: str) -> Persona:
    persona: Persona = DEFAULT_PERSONA.copy()
    with open(path, 'r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            persona[key.strip()] = value.strip()
    return persona
