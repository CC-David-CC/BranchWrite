"""CPU-only initial CAD installation check. Run in the dedicated CAD environment.

Creates temporary files, reopens real geometry, then removes those files.
This smoke check is not the isolated model executor or a complete design checker.
"""
import importlib.metadata
import json
import math
from pathlib import Path
import tempfile


def check():
    expected = {"build123d": "0.13.0", "bd-warehouse": "0.4.0"}
    versions = {name: importlib.metadata.version(name) for name in expected}
    if versions != expected:
        raise RuntimeError(f"Unsupported initial CAD environment: {versions!r}")
    import build123d as b
    from bd_warehouse.fastener import ClearanceHole, SocketHeadCapScrew

    types = sorted(SocketHeadCapScrew.types())
    sizes = SocketHeadCapScrew.sizes("iso4762")
    if "iso4762" not in types or "M4-0.7" not in sizes:
        raise RuntimeError("Required M4 catalogue entry is absent")
    screw = SocketHeadCapScrew("M4-0.7", 16, "iso4762", simple=True)
    with b.BuildPart() as plate:
        b.Box(20, 20, 4, align=(b.Align.CENTER, b.Align.CENTER, b.Align.MAX))
        ClearanceHole(screw, fit="Normal", depth=4, counter_sunk=False)
    measurements = {}
    with tempfile.TemporaryDirectory(prefix="bw-cad-install-check-") as tmp:
        for name, shape in (("m4_socket_head_screw", screw), ("clearance_plate", plate.part)):
            path = Path(tmp) / (name + ".step")
            b.export_step(shape, path)
            reopened = b.import_step(path)
            if not reopened.is_valid or len(reopened.solids()) != 1 or reopened.volume <= 0:
                raise RuntimeError(f"Invalid reopened component: {name}")
            bounds = reopened.bounding_box()
            measurements[name] = {"step_bytes": path.stat().st_size,
                                  "volume_mm3": reopened.volume,
                                  "bounds_min_mm": list(bounds.min),
                                  "bounds_max_mm": list(bounds.max)}
            if name == "m4_socket_head_screw":
                if abs(bounds.min.Z + 16) > 1e-6 or abs(bounds.max.Z - 4) > 1e-6:
                    raise RuntimeError("Screw axial dimensions differ from the fixed example")
            else:
                cylinders = [face for face in reopened.faces() if face.geom_type.name == "CYLINDER"]
                if len(cylinders) != 1 or abs(cylinders[0].radius - 2.25) > 1e-6:
                    raise RuntimeError("Actual M4 Normal clearance hole is not 4.5 mm")
                if abs(reopened.volume - (1600 - math.pi * 2.25 ** 2 * 4)) > 1e-5:
                    raise RuntimeError("Reopened clearance hole does not pass through the plate")
    return {"status": "PASS", "versions": versions, "catalogue_types": types,
            "catalogue_sizes_iso4762": sizes, "measurements": measurements,
            "temporary_exports_removed": True, "scope": "CPU installation smoke, no model inference"}


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
