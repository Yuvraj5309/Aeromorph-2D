import json
from pathlib import Path
from airfoil import Airfoil

AIRFOILS_DIR = Path(__file__).parent.parent / "airfoils"
DATA_DIR     = Path(__file__).parent.parent / "data"

choice = input("Load existing file or create new? (load/new): ").strip().lower()

if choice == "load":
    files = sorted(DATA_DIR.glob("*.json"))
    if not files:
        print("No saved files found in data/. Starting new session.")
        choice = "new"
    else:
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f.stem}")
        selection = int(input("Select a file: ")) - 1
        data = json.loads(files[selection].read_text())

        airfoil_name   = data["airfoil"]
        alpha          = data["aoa"]
        saved_regions  = data["regions"]

        airfoil = Airfoil(AIRFOILS_DIR / f"{airfoil_name}.dat")
        airfoil.rotate(alpha)
        airfoil.plot(saved_regions)

if choice == "new":
    available = [p.stem for p in AIRFOILS_DIR.glob("*.dat")]
    print("Available airfoils:", ", ".join(sorted(available)))

    airfoil_name = input("Enter airfoil name: ").strip()
    alpha        = float(input("Enter angle of attack (degrees): "))

    airfoil = Airfoil(AIRFOILS_DIR / f"{airfoil_name}.dat")
    airfoil.rotate(alpha)
    airfoil.plot()
