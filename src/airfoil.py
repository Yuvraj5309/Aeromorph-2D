from pathlib import Path
import numpy as np
from display import plot_airfoil


class Airfoil:

    def __init__(self, filename):
        self.filename = filename
        self.name     = Path(filename).stem
        self.alpha    = 0.0
        self.points   = self.load_points()


    def load_points(self):
        points = []

        with open(self.filename, "r") as file:
            lines = file.readlines()[1:]

        for line in lines:
            x, y = line.split()
            points.append([float(x), float(y)])

        return np.array(points)


    def rotate(self, alpha_deg):
        self.alpha = alpha_deg
        alpha = np.radians(-alpha_deg)
        rotation_matrix = np.array([
            [np.cos(alpha), -np.sin(alpha)],
            [np.sin(alpha),  np.cos(alpha)]
        ])
        self.points = self.points @ rotation_matrix.T

    def plot(self, saved_regions=None):
        plot_airfoil(self.points, self.name, self.alpha, saved_regions)