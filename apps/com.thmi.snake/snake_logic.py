"""Pure snake rules (no screen code) so they can be tested anywhere."""
COLS, ROWS = 15, 15
DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}


def step(snake, direction, food):
    """snake is a list of (x, y), head first. Returns (new_snake, ate, dead)."""
    dx, dy = DIRS[direction]
    hx, hy = snake[0]
    head = (hx + dx, hy + dy)
    if not (0 <= head[0] < COLS and 0 <= head[1] < ROWS):
        return snake, False, True
    ate = head == food
    body = snake if ate else snake[:-1]
    if head in body:
        return snake, False, True
    return [head] + body, ate, False


def free_cell(snake, rnd):
    taken = set(snake)
    cells = [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in taken]
    return cells[rnd(len(cells))] if cells else None
