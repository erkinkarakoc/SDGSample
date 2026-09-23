import bpy
from pathlib import Path
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
for path in (root / 'assets').glob('*.blend'):
    if path.stat().st_size == 0:
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = src.objects
    for obj in dst.objects:
        if obj:
            bpy.context.scene.collection.objects.link(obj)
    graph = bpy.context.evaluated_depsgraph_get()
    graph.update()
    print('ASSET', path.name, flush=True)
    for obj in dst.objects:
        if obj:
            ev = obj.evaluated_get(graph)
            print(obj.name, obj.type, 'hide', obj.hide_render, 'dims', tuple(round(v, 3) for v in ev.dimensions),
                  'location', tuple(round(v, 3) for v in ev.matrix_world.translation),
                  'polys', len(ev.data.polygons) if obj.type == 'MESH' else 0,
                  'materials', [m.name for m in obj.data.materials if m] if obj.type == 'MESH' else [], flush=True)
