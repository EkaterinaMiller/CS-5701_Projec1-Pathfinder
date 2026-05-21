from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Node:
    position: tuple[int, int]
    wait: int
    parent: Optional["Node"] = None

WAIT = {
    "R": 1,  # Road
    "F": 3,  # Field
    "O": 5,  # Forest
    "H": 8,  # Hills
    "M": 15,  # Mountains
    "S": 0,   # Start
    "E": 1,   # End
}


def find_start(grid: list[list[str]]) -> tuple[int, int] | None:
    """Find the coordinates of the start position 'S' in the grid."""
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] == "S":
                return (r, c)
    return None


def reconstruct_path(close_list: list[Node], grid: list[list[str]]) -> list[Node]:
    """Rebuild a path from the goal node back to start using parent pointers."""
    if not close_list:
        return []

    goal = close_list[-1]
    gr, gc = goal.position
    if grid[gr][gc] != "E":
        return []

    path = [goal]
    current = goal.parent
    while current is not None:
        path.append(current)
        current = current.parent
    return path[::-1]


def breadth_first_steps(grid: list[list[str]]) -> list[tuple[list[Node], list[Node], bool]]:
    """Return BFS snapshots as (open_list, close_list, found_goal) for animation."""
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0

    # Find the start position (S).
    start = find_start(grid)
    if start is None:
        raise ValueError("Start position 'S' not found in the grid.")
    
    # Queue for BFS, starting with the initial position.
    open_list: list[Node] = [Node(position=start, wait=0)]
    close_list: list[Node] = []  # To keep track of visited nodes.
    open_positions: set[tuple[int, int]] = {start}
    closed_positions: set[tuple[int, int]] = set()
    steps: list[tuple[list[Node], list[Node], bool]] = []

    while open_list:
        current = open_list.pop(0)
        open_positions.discard(current.position)
        r, c = current.position

        if (r, c) in closed_positions:
            continue

        if grid[r][c] == "E":
            close_list.append(current)
            closed_positions.add((r, c))
            steps.append((open_list.copy(), close_list.copy(), True))
            return steps

        # Explore neighbors (up, right, down, left).
        for dr, dc in [(-1, 0), (0, 1), (1, 0), (0, -1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                symbol = grid[nr][nc]
                if symbol == "W":
                    continue
                if (nr, nc) in closed_positions or (nr, nc) in open_positions:
                    continue

                wait = current.wait + WAIT[symbol]
                # Insert in open_list sorted by wait cost.
                inserted = False
                new_node = Node(position=(nr, nc), wait=wait, parent=current)
                for i in range(len(open_list)):
                    if open_list[i].wait > wait:
                        open_list.insert(i, new_node)
                        inserted = True
                        break
                if not inserted:
                    open_list.append(new_node)
                open_positions.add((nr, nc))

        close_list.append(current)
        closed_positions.add((r, c))
        steps.append((open_list.copy(), close_list.copy(), False))

    return steps


def breadth_first(grid: list[list[str]]) -> tuple[list[Node], list[Node]]:
    """Perform a breadth-first search to find the shortest path from S to E."""
    steps = breadth_first_steps(grid)
    if not steps:
        return [], []
    open_list, close_list, _ = steps[-1]
    return open_list, close_list