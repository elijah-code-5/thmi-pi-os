"""Falling-block rules. Board is ROWS lists of COLS ints (0 empty, else piece color index)."""
COLS, ROWS = 10, 16
SHAPES = {
    "I": [(0, 1), (1, 1), (2, 1), (3, 1)], "O": [(1, 0), (2, 0), (1, 1), (2, 1)], "T": [(1, 0), (0, 1), (1, 1), (2, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)], "Z": [(0, 0), (1, 0), (1, 1), (2, 1)], "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
    "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
}
NAMES = "IOTSZJL"


def rotate(cells, size=4):
    """Rotate a piece 90 degrees clockwise inside a size x size box."""
    return [(size - 1 - y, x) for x, y in cells]


def fits(board, cells, ox, oy):
    for x, y in cells:
        bx, by = x + ox, y + oy
        if bx < 0 or bx >= COLS or by >= ROWS:
            return False
        if by >= 0 and board[by][bx]:
            return False
    return True


def lock(board, cells, ox, oy, color):
    for x, y in cells:
        if 0 <= y + oy < ROWS:
            board[y + oy][x + ox] = color


def clear_lines(board):
    keep = [row for row in board if not all(row)]
    n = ROWS - len(keep)
    return [[0] * COLS for _ in range(n)] + keep, n


SCORES = (0, 100, 300, 500, 800)
