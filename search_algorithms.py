from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
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

# Backward-compatible alias used by UI legend code.
WAIT = WEIGHTS


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

def initialize_search(grid: list[list[str]]) -> tuple[list[Node], list[Node]]:
    """Create initial open/close lists for step-by-step search visualization."""
    start = find_start(grid)
    if start is None:
        raise ValueError("Start position 'S' not found in the grid.")
    return [Node(position=start, weight=0)], []


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


def breadth_first_steps(
    grid: list[list[str]],
    open_list: list[Node],
    close_list: list[Node],
) -> tuple[list[Node], list[Node]]:
    """Perform one true BFS step in place: FIFO expansion (ignores weights for ordering)."""
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0

    if not open_list:
        return open_list, close_list

    closed_positions: set[tuple[int, int]] = {node.position for node in close_list}
    open_positions: set[tuple[int, int]] = {node.position for node in open_list}

    current = open_list.pop(0)
    open_positions.discard(current.position)
    r, c = current.position

    # Skip stale entries already expanded earlier.
    if (r, c) in closed_positions:
        return open_list, close_list

    close_list.append(current)
    closed_positions.add((r, c))

    if grid[r][c] == "E":
        return open_list, close_list

    # Explore neighbors (up, right, down, left).
    for dr, dc in [(-1, 0), (0, 1), (1, 0), (0, -1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            symbol = grid[nr][nc]
            if symbol == "W": #Water, impassable
                continue
            if (nr, nc) in closed_positions or (nr, nc) in open_positions:
                continue

            weight = current.weight + WEIGHTS[symbol]
            new_node = Node(position=(nr, nc), weight=weight, parent=current)
            # True BFS always appends to the queue tail.
            open_list.append(new_node)
            open_positions.add((nr, nc))

    return open_list, close_list


def uninform_cost_steps(
    grid: list[list[str]],
    open_list: list[Node],
    close_list: list[Node],
) -> tuple[list[Node], list[Node]]:
    """Perform one uniform-cost step in place: expand by lowest accumulated cost."""
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

            weight = current.weight + WEIGHTS[symbol]
            inserted = False
            new_node = Node(position=(nr, nc), weight=weight, parent=current)
            for i in range(len(open_list)):
                if open_list[i].weight > weight:
                    open_list.insert(i, new_node)
                    inserted = True
                    break
            if not inserted:
                open_list.append(new_node)
            open_positions.add((nr, nc))

    return open_list, close_list

def greedy_best_first_steps(
    grid: list[list[str]],
    open_list: list[Node],
    close_list: list[Node],
    end_pos: tuple[int, int],
) -> tuple[list[Node], list[Node]]:
    """Perform one greedy best-first step in place: expand by lowest heuristic cost."""
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
            
            # cost_to_goal = sqrt((nr - end_pos[0])**2 + (nc - end_pos[1])**2)  # Euclidean distance
            cost_to_goal = abs(nr - end_pos[0]) + abs(nc - end_pos[1])  # Manhattan distance
            weight =  cost_to_goal
            inserted = False
            new_node = Node(position=(nr, nc), weight=weight, parent=current)
            for i in range(len(open_list)):
                if open_list[i].weight > weight:
                    open_list.insert(i, new_node)
                    inserted = True
                    break
            if not inserted:
                open_list.append(new_node)
            open_positions.add((nr, nc))

    return open_list, close_list

def a_star_euclidean_steps(
    grid: list[list[str]],
    open_list: list[Node],
    close_list: list[Node],
    end_pos: tuple[int, int],
) -> tuple[list[Node], list[Node]]:
    """Perform one A* Euclidean step in place using f(n) = g(n) + h(n)."""
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

            # Store g(n) in Node.weight and sort frontier by f(n)=g(n)+h(n).
            g_cost = current.weight + WEIGHTS[symbol]
            h_cost = sqrt((nr - end_pos[0]) ** 2 + (nc - end_pos[1]) ** 2)
            new_priority = g_cost + h_cost
            inserted = False
            new_node = Node(position=(nr, nc), weight=g_cost, parent=current)
            for i in range(len(open_list)):
                existing = open_list[i]
                existing_h = sqrt((existing.position[0] - end_pos[0]) ** 2 + (existing.position[1] - end_pos[1]) ** 2)
                existing_priority = existing.weight + existing_h
                if existing_priority > new_priority:
                    open_list.insert(i, new_node)
                    inserted = True
                    break
            if not inserted:
                open_list.append(new_node)
            open_positions.add((nr, nc))

    return open_list, close_list


def a_star_manhattan_steps(
    grid: list[list[str]],
    open_list: list[Node],
    close_list: list[Node],
    end_pos: tuple[int, int],
) -> tuple[list[Node], list[Node]]:
    """Perform one A* Manhattan step in place using f(n) = g(n) + h(n)."""
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

            # Store g(n) in Node.weight and sort frontier by f(n)=g(n)+h(n).
            g_cost = current.weight + WEIGHTS[symbol]
            h_cost = abs(nr - end_pos[0]) + abs(nc - end_pos[1])
            new_priority = g_cost + h_cost
            inserted = False
            new_node = Node(position=(nr, nc), weight=g_cost, parent=current)
            for i in range(len(open_list)):
                existing = open_list[i]
                existing_h = abs(existing.position[0] - end_pos[0]) + abs(existing.position[1] - end_pos[1])
                existing_priority = existing.weight + existing_h
                if existing_priority > new_priority:
                    open_list.insert(i, new_node)
                    inserted = True
                    break
            if not inserted:
                open_list.append(new_node)
            open_positions.add((nr, nc))

    return open_list, close_list

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
    open_list, close_list = initialize_search(grid)
    end_pos = find_end(grid)
    while open_list:
        open_list, close_list = greedy_best_first_steps(grid, open_list, close_list, end_pos)
        if close_list and grid[close_list[-1].position[0]][close_list[-1].position[1]] == "E":
            break
    return open_list, close_list

def a_star_euclidean(grid: list[list[str]]) -> tuple[list[Node], list[Node]]:
    """Run A* search with Euclidean heuristic from S to E."""
    open_list, close_list = initialize_search(grid)
    end_pos = find_end(grid)
    while open_list:
        open_list, close_list = a_star_euclidean_steps(grid, open_list, close_list, end_pos)
        if close_list and grid[close_list[-1].position[0]][close_list[-1].position[1]] == "E":
            break
    return open_list, close_list


def a_star_manhattan(grid: list[list[str]]) -> tuple[list[Node], list[Node]]:
    """Run A* search with Manhattan heuristic from S to E."""
    open_list, close_list = initialize_search(grid)
    end_pos = find_end(grid)
    while open_list:
        open_list, close_list = a_star_manhattan_steps(grid, open_list, close_list, end_pos)
        if close_list and grid[close_list[-1].position[0]][close_list[-1].position[1]] == "E":
            break
    return open_list, close_list