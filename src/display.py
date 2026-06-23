import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


class AirfoilDisplay:

    HIGH = 'high'
    LOW  = 'low'

    def __init__(self, points, airfoil_name, alpha, saved_regions=None):
        self.points       = points
        self.airfoil_name = airfoil_name
        self.alpha        = alpha
        self.mode         = self.HIGH
        self.pending_idx  = None

        self.regions = []
        if saved_regions:
            for r in saved_regions:
                pts = np.array(r["points"])
                start = self._nearest_idx(pts[0, 0],  pts[0, 1])
                end   = self._nearest_idx(pts[-1, 0], pts[-1, 1])
                self.regions.append((start, end, r["mode"]))

        self.fig, self.ax = plt.subplots(figsize=(10, 4))
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
        self.fig.canvas.mpl_connect('key_press_event',   self._on_key)
        self._draw()
        plt.show()

    def _nearest_idx(self, x, y):
        dists = np.hypot(self.points[:, 0] - x, self.points[:, 1] - y)
        return int(np.argmin(dists))

    def _draw(self):
        self.ax.clear()

        self.ax.plot(self.points[:, 0], self.points[:, 1], 'k-', linewidth=1.5)

        for start, end, mode in self.regions:
            color = 'red' if mode == self.HIGH else 'blue'
            lo, hi = min(start, end), max(start, end)
            seg = self.points[lo:hi + 1]
            self.ax.plot(seg[:, 0], seg[:, 1], color=color, linewidth=5, alpha=0.6)

        if self.pending_idx is not None:
            px, py = self.points[self.pending_idx]
            color  = 'red' if self.mode == self.HIGH else 'blue'
            self.ax.scatter([px], [py], color=color, s=80, zorder=5)

        mode_color = 'red' if self.mode == self.HIGH else 'blue'
        mode_label = 'HIGH pressure' if self.mode == self.HIGH else 'LOW pressure'
        self.ax.set_title(
            f"Mode: {mode_label}  |  H = high  ·  L = low  ·  C = clear  ·  Enter = save",
            color=mode_color, fontsize=11
        )
        self.ax.axis('equal')
        self.ax.grid()
        self.fig.canvas.draw()

    def _on_click(self, event):
        if event.inaxes != self.ax or event.xdata is None:
            return

        idx = self._nearest_idx(event.xdata, event.ydata)

        if self.pending_idx is None:
            self.pending_idx = idx
        else:
            self.regions.append((self.pending_idx, idx, self.mode))
            self.pending_idx = None

        self._draw()

    def _on_key(self, event):
        if event.key == 'h':
            self.mode = self.HIGH
        elif event.key == 'l':
            self.mode = self.LOW
        elif event.key == 'c':
            self.regions.clear()
            self.pending_idx = None
        elif event.key == 'enter':
            self._save()
        self._draw()

    def _save(self):
        DATA_DIR.mkdir(exist_ok=True)

        filename = input("Save as (no extension): ").strip()
        if not filename:
            print("Save cancelled.")
            return

        output = {
            "airfoil": self.airfoil_name,
            "aoa":     self.alpha,
            "regions": [
                {
                    "mode":   mode,
                    "points": self.points[min(s, e):max(s, e) + 1].tolist()
                }
                for s, e, mode in self.regions
            ]
        }

        path = DATA_DIR / f"{filename}.json"
        with open(path, "w") as f:
            json.dump(output, f, indent=2)

        print(f"Saved to {path}")


def plot_airfoil(points, airfoil_name, alpha, saved_regions=None):
    AirfoilDisplay(points, airfoil_name, alpha, saved_regions)
