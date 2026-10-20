from build123d import *

# Parameterized mounting plate dimensions (mm)
width_x = 100.0
length_y = 60.0
thickness_z = 4.0

hole_diameter = 5.0
spacing_x = 76.0
spacing_y = 36.0

notch_depth = 6.0
notch_width = 10.0

# Base plate: centered in X/Y, bottom at Z=0
plate = Box(
    width_x,
    length_y,
    thickness_z,
    align=(Align.CENTER, Align.CENTER, Align.MIN),
)

# Four centered through-holes
hole_radius = hole_diameter / 2.0
for x in (-spacing_x / 2.0, spacing_x / 2.0):
    for y in (-spacing_y / 2.0, spacing_y / 2.0):
        hole = Cylinder(
            hole_radius,
            thickness_z + 2.0,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ).located(Location((x, y, -1.0)))
        plate = plate.cut(hole)

# Locating notch on positive-X edge, centered in Y, through thickness
notch = Box(
    notch_depth,
    notch_width,
    thickness_z + 2.0,
    align=(Align.MIN, Align.CENTER, Align.MIN),
).located(Location((width_x / 2.0 - notch_depth, 0.0, -1.0)))
plate = plate.cut(notch)

export_step(plate, "part.step")

