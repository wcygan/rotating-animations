"""Render a horizontal rotation of a glTF model to a PNG sequence.

Run inside Blender (no uv — Blender provides its own Python):
  blender -b -P scripts/render_spin.py -- models/hotdog.glb frames 120
  blender -b -P scripts/render_spin.py -- models/teacup.glb frames_teacup 120 upright

Orient modes:
  lay_flat (default) — rotate the longest axis to +X (good for hotdog-shaped objects)
  upright            — keep the model's existing Z-up orientation (good for cups, vases)
"""

import bpy
import sys
import math
import os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
model_path, out_dir, n_frames = argv[0], argv[1], int(argv[2])
orient_mode = argv[3] if len(argv) > 3 else "lay_flat"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=model_path)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]


def world_bbox(objs):
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for m in objs:
        for v in m.bound_box:
            wv = m.matrix_world @ Vector(v)
            for i in range(3):
                mins[i] = min(mins[i], wv[i])
                maxs[i] = max(maxs[i], wv[i])
    return mins, maxs


# Step 1: center model on origin
mins, maxs = world_bbox(meshes)
center = (mins + maxs) / 2
for m in meshes:
    m.location -= center
bpy.context.view_layer.update()

# Step 2: detect longest axis and pre-rotate so it lies along +X (horizontal)
mins, maxs = world_bbox(meshes)
dims = maxs - mins
long_axis = max(range(3), key=lambda i: dims[i])

# Outer empty: spins around Z each frame
# Inner empty: fixed lay-flat rotation
bpy.ops.object.empty_add(location=(0, 0, 0))
spin = bpy.context.object
bpy.ops.object.empty_add(location=(0, 0, 0))
orient = bpy.context.object
orient.parent = spin
for m in meshes:
    m.parent = orient

if orient_mode == "upright":
    # Leave the model in its native Z-up orientation; only the outer `spin`
    # empty rotates each frame.
    pass
elif long_axis == 0:  # already X — but we also want to roll the bun upright
    orient.rotation_euler = (math.radians(90), 0, 0)
elif long_axis == 1:  # Y → X
    orient.rotation_euler = (0, 0, math.radians(-90))
else:  # Z → X
    orient.rotation_euler = (0, math.radians(90), 0)

bpy.context.view_layer.update()

# Step 3: bbox after orientation, used for camera framing
mins, maxs = world_bbox(meshes)
dims = maxs - mins
size = max(dims.x, dims.y, dims.z)

# Camera tilted 45° downward so we see into the open bun (mustard visible
# at every rotation angle, not just the end-on shots).
bpy.ops.object.camera_add(
    location=(0, -size * 2.5, size * 2.0),
    rotation=(math.radians(52), 0, 0),
)
cam = bpy.context.object
cam.data.type = "ORTHO"
cam.data.ortho_scale = size * 1.3
bpy.context.scene.camera = cam


def add_light(loc, energy, kind="AREA"):
    bpy.ops.object.light_add(type=kind, location=loc)
    light = bpy.context.object
    light.data.energy = energy
    if kind == "AREA":
        light.data.size = size * 2
    return light


add_light((size * 3, -size * 3, size * 4), 2000)
add_light((-size * 3, -size, size * 2), 800)
add_light((0, size * 3, size * 3), 1000)

world = bpy.data.worlds.new("w")
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.4, 0.4, 0.4, 1.0)
bg.inputs["Strength"].default_value = 0.6
bpy.context.scene.world = world

s = bpy.context.scene
s.render.engine = "CYCLES"
s.cycles.samples = 32
s.cycles.use_denoising = True
try:
    s.cycles.device = "GPU"
except Exception:
    pass

s.render.resolution_x = 800
s.render.resolution_y = 656
s.render.image_settings.file_format = "PNG"
s.render.image_settings.color_mode = "RGBA"
s.render.film_transparent = True

os.makedirs(out_dir, exist_ok=True)
for i in range(n_frames):
    spin.rotation_euler = (0, 0, (i / n_frames) * 2 * math.pi)
    s.render.filepath = os.path.join(out_dir, f"f_{i:03d}.png")
    bpy.ops.render.render(write_still=True)

print(f"rendered {n_frames} frames to {out_dir}")
