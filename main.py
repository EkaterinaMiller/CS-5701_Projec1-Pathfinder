from __future__ import annotations

import argparse
import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

from search_algorithms import (
	Node,
	WAIT,
	breadth_first_steps,
	find_end,
	initialize_search,
	reconstruct_path,
	uninform_cost_steps,
	greedy_best_first_steps,
)


GRID_SIZE = 40
CELL_SIZE = 18

TERRAIN_COLORS = {
	"R": "#9f7a52",  # Road
	"F": "#7ecb6f",  # Field
	"O": "#2f7d32",  # Forest
	"H": "#bda97a",  # Hills
	"M": "#8f8f8f",  # Mountains
	"W": "#4d8ed6",  # Water
	"S": "#f7ed7d",  # Start (also shows letter S)
	"E": "#f2f2f2",  # End (shows red star)
}


def read_map_file(file_path: Path) -> list[list[str]]:
	"""Read a 40x40 character map from a text file and validate contents."""
	if not file_path.exists():
		raise FileNotFoundError(f"Map file not found: {file_path}")

	rows = [line.rstrip("\n") for line in file_path.read_text(encoding="utf-8").splitlines()]

	if len(rows) != GRID_SIZE:
		raise ValueError(f"Map must have exactly {GRID_SIZE} rows, found {len(rows)}")

	grid: list[list[str]] = []
	allowed = set(TERRAIN_COLORS)

	for row_index, row in enumerate(rows, start=1):
		if len(row) != GRID_SIZE:
			raise ValueError(
				f"Row {row_index} must have exactly {GRID_SIZE} characters, found {len(row)}"
			)
		for col_index, cell in enumerate(row, start=1):
			if cell not in allowed:
				raise ValueError(
					f"Invalid symbol '{cell}' at row {row_index}, column {col_index}"
				)
		grid.append(list(row))

	return grid


def star_points(x0: int, y0: int, x1: int, y1: int) -> list[int]:
	"""Create a simple 5-point star polygon inside the cell bounds."""
	cx = (x0 + x1) / 2
	cy = (y0 + y1) / 2
	outer = min((x1 - x0), (y1 - y0)) * 0.4
	inner = outer * 0.45

	points: list[int] = []
	# 10 points: alternating outer and inner points around the center.
	for i in range(10):
		angle = -90 + i * 36
		radius = outer if i % 2 == 0 else inner
		x = cx + radius * math.cos(math.radians(angle))
		y = cy + radius * math.sin(math.radians(angle))
		points.extend([int(x), int(y)])
	return points


def draw_map(
	canvas: tk.Canvas,
	grid: list[list[str]],
	open_positions: set[tuple[int, int]] | None = None,
	closed_positions: set[tuple[int, int]] | None = None,
	path_positions: set[tuple[int, int]] | None = None,
) -> None:
	"""Draw terrain cells and special markers onto the canvas."""
	canvas.delete("all")
	open_positions = open_positions or set()
	closed_positions = closed_positions or set()
	path_positions = path_positions or set()

	for r in range(GRID_SIZE):
		for c in range(GRID_SIZE):
			symbol = grid[r][c]
			x0 = c * CELL_SIZE
			y0 = r * CELL_SIZE
			x1 = x0 + CELL_SIZE
			y1 = y0 + CELL_SIZE

			canvas.create_rectangle(
				x0,
				y0,
				x1,
				y1,
				fill=TERRAIN_COLORS[symbol],
				outline="#d9d9d9",
				width=1,
			)

			if (r, c) in closed_positions:
				canvas.create_rectangle(
					x0,
					y0,
					x1,
					y1,
					fill="#ff8c00",
					stipple="gray50",
					outline="",
				)

			if (r, c) in open_positions:
				canvas.create_rectangle(
					x0,
					y0,
					x1,
					y1,
					fill="#ffd400",
					stipple="gray50",
					outline="",
				)

			if (r, c) in path_positions and symbol not in {"S", "E"}:
				pad = CELL_SIZE * 0.32
				canvas.create_oval(
					x0 + pad,
					y0 + pad,
					x1 - pad,
					y1 - pad,
					fill="red",
					outline="",
				)

			if symbol == "S":
				canvas.create_text(
					(x0 + x1) // 2,
					(y0 + y1) // 2,
					text="S",
					fill="black",
					font=("Arial", 10, "bold"),
				)
			elif symbol == "E":
				canvas.create_polygon(
					star_points(x0, y0, x1, y1),
					fill="red",
					outline="#8b0000",
					width=1,
				)


def add_legend_panel(parent: tk.Widget) -> None:
	"""Add a visual legend panel showing map and animation markers."""
	legend_frame = tk.LabelFrame(parent, text="Legend", padx=8, pady=8)
	legend_frame.pack(side="left", fill="y", padx=(8, 0), pady=(0, 8))

	def label_with_cost(symbol: str, name: str) -> str:
		if symbol in WAIT:
			return f"{name} (cost {WAIT[symbol]})"
		if symbol == "W":
			return f"{name} (blocked)"
		return name

	legend_items = [
		("R", label_with_cost("R", "Road"), "#9f7a52", "tile"),
		("F", label_with_cost("F", "Field"), "#7ecb6f", "tile"),
		("O", label_with_cost("O", "Forest"), "#2f7d32", "tile"),
		("H", label_with_cost("H", "Hills"), "#bda97a", "tile"),
		("M", label_with_cost("M", "Mountains"), "#8f8f8f", "tile"),
		("W", label_with_cost("W", "Water"), "#4d8ed6", "tile"),
		("S", label_with_cost("S", "Start"), "#f7ed7d", "start"),
		("E", label_with_cost("E", "End"), "#f2f2f2", "end"),
		("", "Open list", "#ffd400", "overlay"),
		("", "Closed list", "#ff8c00", "overlay"),
		("", "Path", "red", "path"),
	]

	for row_index, (symbol, label, color, marker_type) in enumerate(legend_items):
		item = tk.Frame(legend_frame)
		item.grid(row=row_index, column=0, sticky="w", pady=2)

		swatch = tk.Canvas(item, width=20, height=20, highlightthickness=1, highlightbackground="#999")
		swatch.pack(side="left")
		swatch.create_rectangle(0, 0, 20, 20, fill=color, outline="")

		if marker_type == "start":
			swatch.create_text(10, 10, text="S", fill="black", font=("Arial", 9, "bold"))
		elif marker_type == "end":
			swatch.create_polygon(star_points(2, 2, 18, 18), fill="red", outline="#8b0000", width=1)
		elif marker_type == "overlay":
			swatch.create_rectangle(0, 0, 20, 20, fill=color, stipple="gray50", outline="")
		elif marker_type == "path":
			swatch.create_oval(6, 6, 14, 14, fill="red", outline="")

		title = f"{symbol} - {label}" if symbol else label
		tk.Label(item, text=title).pack(side="left", padx=6)


def create_app(initial_map: Path) -> tk.Tk:
	"""Create the GUI window and load the initial map."""
	root = tk.Tk()
	root.title("40x40 Terrain Map Viewer")
	# Set window size to fit inside a typical VNC desktop (e.g., 1024x768)
	# Extra width keeps the legend fully visible beside the map.
	window_width = min(1000, GRID_SIZE * CELL_SIZE + 300)
	window_height = min(900, GRID_SIZE * CELL_SIZE + 120)
	root.geometry(f"{window_width}x{window_height}+0+0")
	root.resizable(False, False)
	animation_delay_ms = 40

	state: dict[str, object] = {
		"grid": None,
		"map_path": initial_map,
		"open_list": [],
		"close_list": [],
		"step_index": 0,
		"after_id": None,
		"goal_found": False,
		"step_func": None,
		"algorithm_name": "",
	}

	toolbar = tk.Frame(root, padx=8, pady=6)
	toolbar.pack(fill="x")

	content = tk.Frame(root)
	content.pack(padx=8, pady=(0, 8))

	canvas = tk.Canvas(
		content,
		width=GRID_SIZE * CELL_SIZE,
		height=GRID_SIZE * CELL_SIZE,
		bg="white",
		highlightthickness=0,
	)
	canvas.pack(side="left")
	add_legend_panel(content)
	status_var = tk.StringVar(value="Load a map and press Start BFS.")

	def cancel_animation() -> None:
		after_id = state.get("after_id")
		if isinstance(after_id, str):
			root.after_cancel(after_id)
		state["after_id"] = None

	def load_map(map_path: Path) -> None:
		try:
			grid = read_map_file(map_path)
		except Exception as exc:
			messagebox.showerror("Map Load Error", str(exc))
			return

		cancel_animation()
		state["grid"] = grid
		state["map_path"] = map_path
		state["open_list"] = []
		state["close_list"] = []
		state["step_index"] = 0
		state["goal_found"] = False
		state["step_func"] = None
		state["algorithm_name"] = ""
		draw_map(canvas, grid)
		start_bfs_button.config(state="normal")
		start_ucs_button.config(state="normal")
		start_gbf_button.config(state="normal")
		status_var.set(f"Loaded map: {map_path.name}")

	def animate_step() -> None:
		grid = state.get("grid")
		open_list = state.get("open_list")
		close_list = state.get("close_list")
		step_func = state.get("step_func")
		algorithm_name = str(state.get("algorithm_name") or "Search")
		if not isinstance(grid, list) or not isinstance(open_list, list) or not isinstance(close_list, list):
			start_bfs_button.config(state="normal")
			start_ucs_button.config(state="normal")
			start_gbf_button.config(state="normal")
			status_var.set("No map loaded.")
			return
		if not callable(step_func):
			start_bfs_button.config(state="normal")
			start_ucs_button.config(state="normal")
			start_gbf_button.config(state="normal")
			status_var.set("Select an algorithm to start.")
			return

		goal_found = bool(state.get("goal_found"))
		if goal_found or not open_list:
			path_positions: set[tuple[int, int]] = set()
			if goal_found:
				path = reconstruct_path(close_list, grid)
				path_positions = {node.position for node in path}
			draw_map(
				canvas,
				grid,
				{node.position for node in open_list},
				{node.position for node in close_list},
				path_positions,
			)
			start_bfs_button.config(state="normal")
			start_ucs_button.config(state="normal")
			start_gbf_button.config(state="normal")
			status_var.set(
				f"{algorithm_name} complete." if goal_found else f"{algorithm_name} stopped: no path found."
			)
			state["after_id"] = None
			return

		open_list, close_list = step_func(grid, open_list, close_list)
		state["open_list"] = open_list
		state["close_list"] = close_list
		state["step_index"] = int(state.get("step_index", 0)) + 1

		found_goal = False
		if close_list:
			cr, cc = close_list[-1].position
			found_goal = grid[cr][cc] == "E"
		state["goal_found"] = found_goal

		open_positions = {node.position for node in open_list}
		closed_positions = {node.position for node in close_list}
		path_positions: set[tuple[int, int]] = set()

		if found_goal:
			path = reconstruct_path(close_list, grid)
			path_positions = {node.position for node in path}

		draw_map(canvas, grid, open_positions, closed_positions, path_positions)
		step_index = int(state.get("step_index", 0))
		status_var.set(
			f"{algorithm_name} step {step_index} | Open: {len(open_list)} | Closed: {len(close_list)}"
		)
		state["after_id"] = root.after(animation_delay_ms, animate_step)

	def start_search(
		algorithm_name: str,
		initializer: Callable[[list[list[str]]], tuple[list[Node], list[Node]]],
		step_func: Callable[[list[list[str]], list[Node], list[Node]], tuple[list[Node], list[Node]]],
	) -> None:
		grid = state.get("grid")
		if not isinstance(grid, list):
			status_var.set("Load a map first.")
			return

		try:
			open_list, close_list = initializer(grid)
		except Exception as exc:
			messagebox.showerror(f"{algorithm_name} Error", str(exc))
			return

		cancel_animation()
		state["open_list"] = open_list
		state["close_list"] = close_list
		state["step_index"] = 0
		state["goal_found"] = False
		state["step_func"] = step_func
		state["algorithm_name"] = algorithm_name
		start_bfs_button.config(state="disabled")
		start_ucs_button.config(state="disabled")
		start_gbf_button.config(state="disabled")
		animate_step()

	def start_bfs_animation() -> None:
		start_search("BFS", initialize_search, breadth_first_steps)

	def start_ucs_animation() -> None:
		start_search("UCS", initialize_search, uninform_cost_steps)

	def start_gbf_animation() -> None:
		grid = state.get("grid")
		if not isinstance(grid, list):
			status_var.set("Load a map first.")
			return

		end_pos = find_end(grid)
		if end_pos is None:
			messagebox.showerror("GBF Error", "End position 'E' not found in the grid.")
			return

		def gbf_step(
			current_grid: list[list[str]],
			open_list: list[Node],
			close_list: list[Node],
		) -> tuple[list[Node], list[Node]]:
			return greedy_best_first_steps(current_grid, open_list, close_list, end_pos)

		start_search("GBF", initialize_search, gbf_step)

	def choose_file_and_render() -> None:
		selected = filedialog.askopenfilename(
			title="Select Map File",
			filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
		)
		if selected:
			load_map(Path(selected))

	tk.Button(
		toolbar,
		text="Open Map File",
		command=choose_file_and_render,
	).pack(side="left")
	start_bfs_button = tk.Button(toolbar, text="Start BFS", command=start_bfs_animation)
	start_bfs_button.pack(side="left", padx=(8, 0))
	#button for Uniform Cost Search
	start_ucs_button = tk.Button(toolbar, text="Start UCS", command=start_ucs_animation)
	start_ucs_button.pack(side="left", padx=(8, 0))
	#Greedy Best-First Search
	start_gbf_button = tk.Button(toolbar, text="Start GBF", command=start_gbf_animation)
	start_gbf_button.pack(side="left", padx=(8, 0))
	start_button = tk.Button(toolbar, text="Start A* Euclidean", command=start_bfs_animation)
	start_button.pack(side="left", padx=(8, 0))
	start_button = tk.Button(toolbar, text="Start A* Manhattan", command=start_bfs_animation)
	start_button.pack(side="left", padx=(8, 0))

	tk.Label(root, textvariable=status_var, anchor="w").pack(fill="x", padx=8, pady=(0, 8))

	load_map(initial_map)
	return root


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Display a 40x40 terrain map using Tkinter.")
	parser.add_argument(
		"map_file",
		nargs="?",
		default="map1_stupid.txt",
		help="Path to the map text file (default: map1_stupid.txt)",
	)
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	map_path = Path(args.map_file)
	if not map_path.is_absolute():
		map_path = Path(__file__).resolve().parent / map_path
	app = create_app(map_path)
	app.mainloop()


if __name__ == "__main__":
	try:
		main()
	except Exception as exc:
		try:
			messagebox.showerror("Application Error", str(exc))
		except Exception:
			pass
		print(f"Application Error: {exc}")
		input("Press Enter to exit...")
