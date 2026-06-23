import threading
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import numpy as np
import pyvista as pv
import pyvista_cad as pvcad
import vtkmodules.all as vtk


BG_DARK  = "#1e1e1e"
BG_PANEL = "#2b2b2b"
BG_BTN   = "#3c3f41"
FG       = "#ffffff"
FG_DIM   = "#888888"
ACCENT   = "#4a9eff"

DATA_DIR = Path(__file__).parent.parent / "data"

COLOR_DEFAULT = (173, 216, 230)
COLOR_HIGH    = (220,  50,  50)
COLOR_LOW     = ( 50, 100, 220)


class App:

    def __init__(self, root):
        self.root          = root
        self.root.title("Aeromorph 3D")
        self.root.geometry("1100x650")
        self.root.configure(bg=BG_DARK)
        self._viewer_thread = None
        self.current_mesh   = None
        self.pressure_data  = None

        self._build_sidebar()
        self._build_viewer()

    def _build_sidebar(self):
        sidebar = tk.Frame(self.root, bg=BG_PANEL, width=220)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="AEROMORPH", bg=BG_PANEL, fg=ACCENT,
                 font=("Helvetica", 13, "bold")).pack(pady=(24, 4))
        tk.Label(sidebar, text="3D CAD Viewer", bg=BG_PANEL, fg=FG_DIM,
                 font=("Helvetica", 9)).pack(pady=(0, 30))

        for label, cmd in [
            ("New File",          self.new_file),
            ("Modify Existing",   self.modify_file),
            ("Optimize Existing", self.optimize_file),
        ]:
            tk.Button(
                sidebar, text=label, command=cmd,
                bg=BG_BTN, fg=FG, relief="flat",
                activebackground=ACCENT, activeforeground=FG,
                font=("Helvetica", 10), pady=12, cursor="hand2"
            ).pack(fill=tk.X, padx=16, pady=4)

        tk.Frame(sidebar, bg=BG_PANEL).pack(fill=tk.Y, expand=True)

        tk.Button(
            sidebar, text="Save as VTU", command=self.save_file,
            bg=BG_BTN, fg=ACCENT, relief="flat",
            activebackground=ACCENT, activeforeground=FG,
            font=("Helvetica", 10), pady=12, cursor="hand2"
        ).pack(fill=tk.X, padx=16, pady=(0, 20))

    def _build_viewer(self):
        viewer = tk.Frame(self.root, bg=BG_DARK)
        viewer.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.status_label = tk.Label(
            viewer, text="No file loaded",
            bg=BG_DARK, fg=FG_DIM, font=("Helvetica", 14)
        )
        self.status_label.place(relx=0.5, rely=0.5, anchor="center")

    def _init_mesh(self, mesh):
        n = mesh.n_cells

        # Restore pressure if already saved in the file, otherwise start blank
        if 'pressure' in mesh.cell_data:
            self.pressure_data = mesh.cell_data['pressure'].astype(np.int8).copy()
        else:
            self.pressure_data = np.zeros(n, dtype=np.int8)

        # Build RGB colour array from pressure values
        colors = np.full((n, 3), COLOR_DEFAULT, dtype=np.uint8)
        colors[self.pressure_data ==  1] = COLOR_HIGH
        colors[self.pressure_data == -1] = COLOR_LOW
        mesh.cell_data['rgb'] = colors

    def _open_viewer(self, mesh, title):
        from vtkmodules.vtkInteractionStyle import vtkInteractorStyleUser

        paint_mode    = ['high']
        in_paint_mode = [False]

        plotter = pv.Plotter(title=title)
        actor = plotter.add_mesh(mesh, scalars='rgb', rgb=True,
                                 show_scalar_bar=False, smooth_shading=True)

        # Pull the array from the mapper's copy of the dataset — pyvista may
        # have deep-copied the mesh, so editing the original array has no effect
        color_array = actor.mapper.dataset.GetCellData().GetArray('rgb')

        # Write text actor directly to renderer so we can reliably update it
        text_actor = vtk.vtkTextActor()
        text_actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
        text_actor.SetPosition(0.01, 0.95)
        text_actor.GetTextProperty().SetFontSize(11)
        plotter.renderer.AddViewProp(text_actor)

        # Grab pyvista's camera style so we can restore it
        view_style  = plotter.iren.interactor.GetInteractorStyle()
        paint_style = vtkInteractorStyleUser()
        paint_style.SetCurrentRenderer(plotter.renderer)

        def update_text():
            if not in_paint_mode[0]:
                text_actor.SetInput("VIEW  |  P = enter paint mode")
                text_actor.GetTextProperty().SetColor(0.75, 0.75, 0.75)
            else:
                labels = {
                    'high':    ("HIGH",  (0.86, 0.20, 0.20)),
                    'low':     ("LOW",   (0.20, 0.39, 0.86)),
                    'unpaint': ("ERASE", (0.75, 0.75, 0.75)),
                }
                label, color = labels[paint_mode[0]]
                text_actor.SetInput(
                    f"PAINT [{label}]  |  P = exit   H = high   L = low   U = erase"
                )
                text_actor.GetTextProperty().SetColor(*color)
            plotter.render()

        def toggle_paint():
            if not in_paint_mode[0]:
                in_paint_mode[0] = True
                plotter.iren.interactor.SetInteractorStyle(paint_style)
            else:
                in_paint_mode[0] = False
                plotter.iren.interactor.SetInteractorStyle(view_style)
            update_text()

        def set_pressure(m):
            paint_mode[0] = m
            update_text()

        def paint_cell(cell_id):
            m = paint_mode[0]
            if m == 'high':
                color_array.SetTuple3(cell_id, *COLOR_HIGH)
                self.pressure_data[cell_id] = 1
            elif m == 'low':
                color_array.SetTuple3(cell_id, *COLOR_LOW)
                self.pressure_data[cell_id] = -1
            else:
                color_array.SetTuple3(cell_id, *COLOR_DEFAULT)
                self.pressure_data[cell_id] = 0
            color_array.Modified()
            actor.mapper.dataset.GetCellData().Modified()
            plotter.render()

        def on_left_press(obj, event):
            if not in_paint_mode[0]:
                return
            pos     = obj.GetEventPosition()
            picker  = vtk.vtkCellPicker()
            picker.SetTolerance(0.005)
            picker.Pick(pos[0], pos[1], 0, plotter.renderer)
            cell_id = picker.GetCellId()
            if cell_id >= 0:
                paint_cell(cell_id)

        plotter.add_key_event('p', toggle_paint)
        plotter.add_key_event('h', lambda: set_pressure('high'))
        plotter.add_key_event('l', lambda: set_pressure('low'))
        plotter.add_key_event('u', lambda: set_pressure('unpaint'))

        plotter.iren.interactor.AddObserver('LeftButtonPressEvent', on_left_press, 1.0)

        update_text()
        plotter.show()

    def _launch_viewer(self, name):
        self.status_label.config(text=f"Loaded: {name}")
        self._viewer_thread = threading.Thread(
            target=self._open_viewer,
            args=(self.current_mesh, name),
            daemon=True
        )
        self._viewer_thread.start()

    def new_file(self):
        path = filedialog.askopenfilename(
            title="Select a STEP file",
            filetypes=[("STEP files", "*.step *.stp"), ("All files", "*.*")]
        )
        if not path:
            return

        raw = pv.read(path)
        self.current_mesh = raw.combine() if isinstance(raw, pv.MultiBlock) else raw
        self._init_mesh(self.current_mesh)
        self._launch_viewer(Path(path).name)

    def modify_file(self):
        path = filedialog.askopenfilename(
            title="Select a VTU file",
            initialdir=DATA_DIR,
            filetypes=[("VTU files", "*.vtu"), ("All files", "*.*")]
        )
        if not path:
            return

        self.current_mesh = pv.read(path)
        self._init_mesh(self.current_mesh)
        self._launch_viewer(Path(path).name)

        # TODO: apply mesh modifications to self.current_mesh, display result

    def save_file(self):
        if self.current_mesh is None:
            self.status_label.config(text="No file loaded to save.")
            return

        DATA_DIR.mkdir(exist_ok=True)

        path = filedialog.asksaveasfilename(
            title="Save as VTU",
            initialdir=DATA_DIR,
            defaultextension=".vtu",
            filetypes=[("VTU files", "*.vtu")]
        )
        if not path:
            return

        # Attach latest pressure values before saving
        if self.pressure_data is not None:
            self.current_mesh.cell_data['pressure'] = self.pressure_data

        self.current_mesh.save(path)
        self.status_label.config(text=f"Saved: {Path(path).name}")

    def optimize_file(self):
        # TODO: load a VTU from data/, run optimization model, display result
        pass


root = tk.Tk()
App(root)
root.mainloop()
