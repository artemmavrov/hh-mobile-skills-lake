"""Shared definitions for skill stacks (single skills, pairs, triples)."""
from math import comb

STACK_SIZES = (1, 2, 3)
STACK_NAMES = {1: "skills", 2: "pairs", 3: "triples"}


def result_key(engine: str, size: int) -> str:
    return f"results/{engine}/{STACK_NAMES[size]}.csv"


def header(size: int) -> list[str]:
    return [f"skill_{i}" for i in range(1, size + 1)] + ["vacancies"]


def ordered(counts: dict[tuple, int]) -> list[tuple]:
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def combinations_emitted(skill_counts: list[int], size: int) -> int:
    return sum(comb(k, size) for k in skill_counts)
