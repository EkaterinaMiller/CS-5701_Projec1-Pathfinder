from __future__ import annotations

import argparse
import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from breathfirst import breadth_first_steps, reconstruct_path


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


def create_app(initial_map: Path) -> tk.Tk:
	"""Create the GUI window and load the initial map."""
	root = tk.Tk()
	root.title("40x40 Terrain Map Viewer")
	root.resizable(False, False)
	animation_delay_ms = 40

	state: dict[str, object] = {
		"grid": None,
		"map_path": initial_map,
		"steps": [],
		"after_id": None,
	}

	toolbar = tk.Frame(root, padx=8, pady=6)
	toolbar.pack(fill="x")

	canvas = tk.Canvas(
		root,
		width=GRID_SIZE * CELL_SIZE,
		height=GRID_SIZE * CELL_SIZE,
		bg="white",
		highlightthickness=0,
	)
	canvas.pack(padx=8, pady=(0, 8))
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
		state["steps"] = []
		draw_map(canvas, grid)
		start_button.config(state="normal")
		status_var.set(f"Loaded map: {map_path.name}")

	def animate_step(step_index: int) -> None:
		steps = state.get("steps")
		grid = state.get("grid")
		if not isinstance(steps, list) or not isinstance(grid, list):
			start_button.config(state="normal")
			status_var.set("No map loaded.")
			return

		if step_index >= len(steps):
			start_button.config(state="normal")
			status_var.set("BFS complete.")
			state["after_id"] = None
			return

		open_list, close_list, found_goal = steps[step_index]
		open_positions = {node.position for node in open_list}
		closed_positions = {node.position for node in close_list}
		path_positions: set[tuple[int, int]] = set()

		if found_goal:
			path = reconstruct_path(close_list, grid)
			path_positions = {node.position for node in path}

		draw_map(canvas, grid, open_positions, closed_positions, path_positions)
		status_var.set(
			f"BFS step {step_index + 1}/{len(steps)} | Open: {len(open_list)} | Closed: {len(close_list)}"
		)
		state["after_id"] = root.after(animation_delay_ms, lambda: animate_step(step_index + 1))

	def start_bfs_animation() -> None:
		grid = state.get("grid")
		if not isinstance(grid, list):
			status_var.set("Load a map first.")
			return

		try:
			steps = breadth_first_steps(grid)
		except Exception as exc:
			messagebox.showerror("BFS Error", str(exc))
			return

		if not steps:
			status_var.set("No BFS steps were generated.")
			return

		cancel_animation()
		state["steps"] = steps
		start_button.config(state="disabled")
		animate_step(0)

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
	start_button = tk.Button(toolbar, text="Start BFS", command=start_bfs_animation)
	start_button.pack(side="left", padx=(8, 0))

	legend = (
		"Legend: R=Road, F=Field, O=Forest, H=Hills, M=Mountains, "
		"W=Water, S=Start, E=End, Open=Yellow, Closed=Orange, Path=Red Dots"
	)
	tk.Label(toolbar, text=legend).pack(side="left", padx=10)
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
