"""Minesweeper rules."""
import random

N, MINES = 8, 10


def new_board(safe, rnd=random):
    """Place mines anywhere except the first tapped cell (and keep it zero if possible). Returns list of N*N mine flags."""
    spots = [i for i in range(N * N) if i != safe and i not in nbrs(safe)]
    if len(spots) < MINES:
        spots = [i for i in range(N * N) if i != safe]
    chosen = rnd.sample(spots, MINES)
    return [i in chosen for i in range(N * N)]


def nbrs(i):
    r, c = divmod(i, N)
    return [rr * N + cc for rr in range(max(0, r - 1), min(N, r + 2)) for cc in range(max(0, c - 1), min(N, c + 2)) if (rr, cc) != (r, c)]


def counts(mines):
    return [sum(mines[j] for j in nbrs(i)) for i in range(N * N)]


def reveal(i, mines, cnt, shown):
    """Reveal cell i (flood fill zeros). Returns True if a mine was hit."""
    if mines[i]:
        shown[i] = True
        return True
    stack = [i]
    while stack:
        k = stack.pop()
        if shown[k]:
            continue
        shown[k] = True
        if cnt[k] == 0:
            stack.extend(j for j in nbrs(k) if not shown[j] and not mines[j])
    return False


def won(mines, shown):
    return all(shown[i] or mines[i] for i in range(N * N))
