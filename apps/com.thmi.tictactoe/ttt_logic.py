"""Tic-tac-toe rules and a perfect (minimax) computer player. Board = list of 9: ' ', 'X', 'O'."""
LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6))


def winner(b):
    for a, c, d in LINES:
        if b[a] != " " and b[a] == b[c] == b[d]:
            return b[a], (a, c, d)
    return None, None


def full(b):
    return " " not in b


def _score(b, turn, me):
    w, _ = winner(b)
    if w:
        return 1 if w == me else -1
    if full(b):
        return 0
    other = "X" if turn == "O" else "O"
    best = None
    for i in range(9):
        if b[i] == " ":
            b[i] = turn
            s = _score(b, other, me)
            b[i] = " "
            if best is None or (turn == me and s > best) or (turn != me and s < best):
                best = s
    return best


def best_move(b, me="O"):
    other = "X" if me == "O" else "O"
    best, move = None, None
    for i in (4, 0, 2, 6, 8, 1, 3, 5, 7):
        if b[i] == " ":
            b[i] = me
            s = _score(b, other, me)
            b[i] = " "
            if best is None or s > best:
                best, move = s, i
    return move
