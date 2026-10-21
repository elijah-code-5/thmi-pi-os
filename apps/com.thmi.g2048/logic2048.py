"""Pure 2048 rules."""


def slide_row(row):
    """Slide a row of 4 to the left. Returns (new_row, points)."""
    nums = [v for v in row if v]
    out, pts, i = [], 0, 0
    while i < len(nums):
        if i + 1 < len(nums) and nums[i] == nums[i + 1]:
            out.append(nums[i] * 2)
            pts += nums[i] * 2
            i += 2
        else:
            out.append(nums[i])
            i += 1
    return out + [0] * (4 - len(out)), pts


def move(board, d):
    """board = 4 lists of 4. d in left/right/up/down. Returns (new_board, points, changed)."""
    def rot(b):          # rotate clockwise
        return [[b[3 - c][r] for c in range(4)] for r in range(4)]
    turns = {"left": 0, "down": 1, "right": 2, "up": 3}[d]
    b = [r[:] for r in board]
    for _ in range(turns):
        b = rot(b)
    total, new = 0, []
    for row in b:
        r, p = slide_row(row)
        new.append(r)
        total += p
    for _ in range((4 - turns) % 4):
        new = rot(new)
    return new, total, new != board


def has_moves(board):
    return any(move(board, d)[2] for d in ("left", "right", "up", "down"))
