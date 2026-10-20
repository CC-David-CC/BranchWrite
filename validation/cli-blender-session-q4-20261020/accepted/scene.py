import bpy
import math


def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)
    for light in list(bpy.data.lights):
        if light.users == 0:
            bpy.data.lights.remove(light)


def make_material(name, color, metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


def add_box(name, size, location, material, mesh_offset=(0.0, 0.0, 0.0)):
    sx, sy, sz = size
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    ox, oy, oz = mesh_offset

    verts = [
        (ox - hx, oy - hy, oz - hz),
        (ox + hx, oy - hy, oz - hz),
        (ox + hx, oy + hy, oz - hz),
        (ox - hx, oy + hy, oz - hz),
        (ox - hx, oy - hy, oz + hz),
        (ox + hx, oy - hy, oz + hz),
        (ox + hx, oy + hy, oz + hz),
        (ox - hx, oy + hy, oz + hz),
    ]
    faces = [
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (2, 3, 7, 6),
        (0, 4, 7, 3),
        (1, 2, 6, 5),
    ]

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    bpy.context.collection.objects.link(obj)

    if material is not None:
        obj.data.materials.append(material)

    return obj


def add_sphere(name, radius, location, material, segments=24, rings=16):
    mesh = bpy.data.meshes.new(name)
    verts = []
    faces = []

    for ring in range(rings + 1):
        phi = math.pi * ring / rings
        z = radius * math.cos(phi)
        ring_radius = radius * math.sin(phi)
        start = len(verts)

        if ring_radius < 1e-8:
            verts.append((0.0, 0.0, z))
        else:
            for seg in range(segments):
                theta = 2.0 * math.pi * seg / segments
                verts.append(
                    (
                        ring_radius * math.cos(theta),
                        ring_radius * math.sin(theta),
                        z,
                    )
                )

        if ring > 0:
            prev_start = len(verts) - (segments if ring > 1 else 1) - (segments if ring == rings else 0)
            # Simpler triangulation below is sufficient for small eyes.

    # Use Blender's primitive sphere operator for robust normals and shading.
    bpy.data.meshes.remove(mesh)
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius,
        segments=segments,
        ring_count=rings,
        location=location,
    )
    obj = bpy.context.active_object
    obj.name = name
    if material is not None:
        obj.data.materials.append(material)
    return obj


def main():
    clear_scene()

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 24
    scene.render.fps = 12
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16

    orange = make_material("OrangePlatform", (0.95, 0.32, 0.04), roughness=0.55)
    blue = make_material("BlueRobot", (0.04, 0.22, 0.85), roughness=0.35)
    silver = make_material("SilverArm", (0.86, 0.88, 0.92), metallic=1.0, roughness=0.22)
    white = make_material("EyeWhite", (0.95, 0.95, 0.95), roughness=0.25)
    black = make_material("EyePupil", (0.02, 0.02, 0.02), roughness=0.35)

    # Orange rectangular platform.
    add_box("Platform", (4.0, 3.0, 0.2), (0.0, 0.0, 0.1), orange)

    # Blue robot body and head.
    add_box("RobotBody", (1.2, 0.8, 1.0), (0.0, 0.0, 0.7), blue)
    add_box("RobotHead", (0.8, 0.6, 0.6), (0.0, 0.0, 1.5), blue)

    # Simple eyes on the front face, which is negative Y.
    add_sphere("EyeLeft", 0.09, (-0.18, -0.32, 1.55), white)
    add_sphere("EyeRight", 0.09, (0.18, -0.32, 1.55), white)
    add_sphere("PupilLeft", 0.04, (-0.18, -0.38, 1.55), black)
    add_sphere("PupilRight", 0.04, (0.18, -0.38, 1.55), black)

    # Two silver mechanical arms. Origins are at the shoulders.
    arm_right = add_box(
        "ArmRight",
        (1.0, 0.18, 0.18),
        (0.6, 0.0, 1.0),
        silver,
        mesh_offset=(0.5, 0.0, 0.0),
    )
    add_box(
        "ArmLeft",
        (1.0, 0.18, 0.18),
        (-0.6, 0.0, 1.0),
        silver,
        mesh_offset=(-0.5, 0.0, 0.0),
    )

    # Animate only the right arm through 45 degrees over frames 1 to 24.
    arm_right.rotation_euler = (0.0, 0.0, 0.0)
    arm_right.keyframe_insert("rotation_euler", frame=1)

    arm_right.rotation_euler = (0.0, -math.radians(45.0), 0.0)
    arm_right.keyframe_insert("rotation_euler", frame=24)

    if arm_right.animation_data and arm_right.animation_data.action:
        for fcurve in arm_right.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = "LINEAR"

    # Simple lighting so the controlled views are readable.
    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 3.0
    sun_data.angle = math.radians(5.0)
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = (math.radians(55.0), 0.0, math.radians(25.0))
    bpy.context.collection.objects.link(sun)

    bpy.ops.wm.save_as_mainfile(filepath="/work/scene.blend")


main()
