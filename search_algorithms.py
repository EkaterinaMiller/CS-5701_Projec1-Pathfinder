from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional
from math import sqrt


@dataclass
class Node:
    position: tuple[int, int]
    weight: int
    parent: Optional["Node"] = None

WEIGHTS = {
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

def find_end(grid: list[list[str]]) -> tuple[int, int] | None:
    """Find the coordinates of the end position 'E' in the grid."""
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] == "E":
                return (r, c)
    return None

def initialize_search(grid: list[list[str]], start_weight = 0) -> tuple[list[Node], list[Node]]:
    """Create initial open/close lists for step-by-step search visualization."""
    start = find_start(grid)
    if start is None:
        raise ValueError("Start position 'S' not found in the grid.")
    return [Node(position=start, weight=start_weight)], []

def euclidean_distance(pos1: tuple[int, int], pos2: tuple[int, int]) -> float:
    """Calculate the Euclidean distance between two positions."""
    return sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)

def manhattan_distance(pos1: tuple[int, int], pos2: tuple[int, int]) -> int:
    """Calculate the Manhattan distance between two positions."""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

# def initialize_uninform_cost(grid: list[list[str]]) -> tuple[list[Node], list[Node]]:
#     """Create initial open/close lists for step-by-step uniform-cost search visualization."""
#     return initialize_breadth_first(grid)


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


def _insert_sorted_by_weight(open_list: list[Node], node: Node) -> None:
    """Insert a node into open_list ordered by ascending node.weight."""
    for i in range(len(open_list)):
        if open_list[i].weight > node.weight:
            open_list.insert(i, node)
            return
    open_list.append(node)


def _search_step(
    grid: list[list[str]],
    open_list: list[Node],
    close_list: list[Node],
    ordered: bool,
    weight_fn: Callable[[Node, tuple[int, int], str], float],
) -> tuple[list[Node], list[Node]]:
    """Shared one-step expansion logic used by BFS/UCS/GBF/A*."""
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0

    if not open_list:
        return open_list, close_list

    closed_positions: set[tuple[int, int]] = {node.position for node in close_list}
    open_positions: set[tuple[int, int]] = {node.position for node in open_list}

    current = open_list.pop(0)
    open_positions.discard(current.position)
    r, c = current.position

    if (r, c) in closed_positions:
        return open_list, close_list

    close_list.append(current)
    closed_positions.add((r, c))

    if grid[r][c] == "E":
        return open_list, close_list

    for dr, dc in [(-1, 0), (0, 1), (1, 0), (0, -1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            symbol = grid[nr][nc]
            if symbol == "W":
                continue
            if (nr, nc) in closed_positions or (nr, nc) in open_positions:
                continue

            node_weight = weight_fn(current, (nr, nc), symbol)
            new_node = Node(position=(nr, nc), weight=node_weight, parent=current)
            if ordered:
                _insert_sorted_by_weight(open_list, new_node)
            else:
                open_list.append(new_node)
            open_positions.add((nr, nc))

    return open_list, close_list


def breadth_first_steps(
    grid: list[list[str]],
    open_list: list[Node],
    close_list: list[Node],
) -> tuple[list[Node], list[Node]]:
    """Perform one true BFS step in place: FIFO expansion (ignores weights for ordering)."""
    return _search_step(
        grid,
        open_list,
        close_list,
        ordered=False,
        weight_fn=lambda current, _npos, symbol: current.weight + WEIGHTS[symbol],
    )


def uninform_cost_steps(
    grid: list[list[str]],
    open_list: list[Node],
    close_list: list[Node],
) -> tuple[list[Node], list[Node]]:
    """Perform one uniform-cost step in place: expand by lowest accumulated cost."""
    return _search_step(
        grid,
        open_list,
        close_list,
        ordered=True,
        weight_fn=lambda current, _npos, symbol: current.weight + WEIGHTS[symbol],
    )

def greedy_best_first_steps(
    grid: list[list[str]],
    open_list: list[Node],
    close_list: list[Node],
    end_pos: tuple[int, int],
) -> tuple[list[Node], list[Node]]:
    """Perform one greedy best-first step in place: expand by lowest heuristic cost."""
    return _search_step(
        grid,
        open_list,
        close_list,
        ordered=True,
        weight_fn=lambda _current, npos, _symbol: manhattan_distance(npos, end_pos),
    )

def a_star_euclidean_steps(
    grid: list[list[str]],
    open_list: list[Node],
    close_list: list[Node],
    end_pos: tuple[int, int],
) -> tuple[list[Node], list[Node]]:
    """Perform one A* Euclidean step in place using f(n) = g(n) + h(n)."""
    def weight_fn(current: Node, npos: tuple[int, int], symbol: str) -> float:
        # Keep backward-compatible behavior: current.weight stores f(n).
        h_current = 0.0 if current.parent is None else euclidean_distance(current.position, end_pos)
        g_current = current.weight - h_current
        g_next = g_current + WEIGHTS[symbol]
        h_next = euclidean_distance(npos, end_pos)
        return g_next + h_next

    return _search_step(grid, open_list, close_list, ordered=True, weight_fn=weight_fn)


def a_star_manhattan_steps(
    grid: list[list[str]],
    open_list: list[Node],
    close_list: list[Node],
    end_pos: tuple[int, int],
    factor: float = 1.0,
) -> tuple[list[Node], list[Node]]:
    """Perform one A* Manhattan step in place using f(n) = g(n) + h(n)."""
    def weight_fn(current: Node, npos: tuple[int, int], symbol: str) -> float:
        # Keep backward-compatible behavior: current.weight stores f(n).
        h_current = 0.0 if current.parent is None else factor * manhattan_distance(current.position, end_pos)
        g_current = current.weight - h_current
        g_next = g_current + WEIGHTS[symbol]
        h_next = factor * manhattan_distance(npos, end_pos)
        return g_next + h_next

    return _search_step(grid, open_list, close_list, ordered=True, weight_fn=weight_fn)

def breadth_first(grid: list[list[str]]) -> tuple[list[Node], list[Node]]:
    """Run true BFS (FIFO queue) from S to E."""
    open_list, close_list = initialize_search(grid)
    while open_list:
        open_list, close_list = breadth_first_steps(grid, open_list, close_list)
        if close_list and grid[close_list[-1].position[0]][close_list[-1].position[1]] == "E":
            break
    return open_list, close_list


def uninform_cost(grid: list[list[str]]) -> tuple[list[Node], list[Node]]:
    """Run uniform-cost search from S to E."""
    open_list, close_list = initialize_search(grid)
    while open_list:
        open_list, close_list = uninform_cost_steps(grid, open_list, close_list)
        if close_list and grid[close_list[-1].position[0]][close_list[-1].position[1]] == "E":
            break
    return open_list, close_list

def greedy_best_first(grid: list[list[str]]) -> tuple[list[Node], list[Node]]:
    """Run greedy best-first search from S to E."""
    end_pos = find_end(grid)
    open_list, close_list = initialize_search(grid)
    while open_list:
        open_list, close_list = greedy_best_first_steps(grid, open_list, close_list, end_pos)
        if close_list and grid[close_list[-1].position[0]][close_list[-1].position[1]] == "E":
            break
    return open_list, close_list

def a_star_euclidean(grid: list[list[str]]) -> tuple[list[Node], list[Node]]:
    """Run A* search with Euclidean heuristic from S to E."""
    end_pos = find_end(grid)
    open_list, close_list = initialize_search(grid)
    while open_list:
        open_list, close_list = a_star_euclidean_steps(grid, open_list, close_list, end_pos)
        if close_list and grid[close_list[-1].position[0]][close_list[-1].position[1]] == "E":
            break
    return open_list, close_list


def a_star_manhattan(grid: list[list[str]]) -> tuple[list[Node], list[Node]]:
    """Run A* search with Manhattan heuristic from S to E."""
    end_pos = find_end(grid)
    open_list, close_list = initialize_search(grid)
    while open_list:
        open_list, close_list = a_star_manhattan_steps(grid, open_list, close_list, end_pos, factor=1.0)
        if close_list and grid[close_list[-1].position[0]][close_list[-1].position[1]] == "E":
            break
    return open_list, close_list