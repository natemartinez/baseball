"""
Base Running Logic.

Pure functions for advancing runners on base hits and walks.
Functions return (new_bases_dict, runs_scored) without mutating input state.
"""

from typing import Any, Dict, Tuple


def advance_on_hit(
    bases: Dict[str, Any], bases_taken: int, batter_summary: Dict[str, Any]
) -> Tuple[Dict[str, Any], int]:
    """
    Advances existing runners forward by ``bases_taken`` and places batter.
    Returns (new_bases, runs_scored).
    """
    runs = 0
    new_bases = {'first': None, 'second': None, 'third': None}

    order = ['third', 'second', 'first']
    base_map = {'first': 1, 'second': 2, 'third': 3}
    rev_map = {1: 'first', 2: 'second', 3: 'third'}

    for b_name in order:
        runner = bases.get(b_name)
        if runner:
            dest = base_map[b_name] + bases_taken
            if dest >= 4:
                runs += 1
            else:
                new_bases[rev_map[dest]] = runner

    if bases_taken >= 4:
        runs += 1
    elif bases_taken == 1:
        new_bases['first'] = batter_summary
    elif bases_taken == 2:
        new_bases['second'] = batter_summary
    elif bases_taken == 3:
        new_bases['third'] = batter_summary

    return new_bases, runs


def advance_on_walk(
    bases: Dict[str, Any], batter_summary: Dict[str, Any]
) -> Tuple[Dict[str, Any], int]:
    """
    Forces runners forward on a base on balls.
    Returns (new_bases, runs_scored).
    """
    runs = 0
    new_bases = dict(bases)
    b1 = bases.get('first')
    b2 = bases.get('second')
    b3 = bases.get('third')

    if b1 and b2 and b3:
        runs += 1
        new_bases['third'] = b2
        new_bases['second'] = b1
        new_bases['first'] = batter_summary
    elif b1 and b2:
        new_bases['third'] = b2
        new_bases['second'] = b1
        new_bases['first'] = batter_summary
    elif b1:
        new_bases['second'] = b1
        new_bases['first'] = batter_summary
    else:
        new_bases['first'] = batter_summary

    return new_bases, runs

