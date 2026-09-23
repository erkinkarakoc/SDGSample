"""Bake licensed assets into static meshes; retain source provenance separately."""
import bpy
from mathutils import Matrix, Vector
from materials import principled, paint


def load_template(path, class_name, length):
    scene = bpy.context.scene
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        target.objects = source.objects
    imported = [o for o in target.objects if o]
    for obj in imported:
        scene.collection.objects.link(obj)
    graph = bpy.context.evaluated_depsgraph_get()
    graph.update()
    pieces = []
    for obj in imported:
        if obj.type != 'MESH' or obj.hide_render or obj.name.startswith(('WGT-', 'logo_', 'latters')):
            continue
        evaluated = obj.evaluated_get(graph)
        if not evaluated.data.polygons:
            continue
        mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=graph)
        mesh.transform(evaluated.matrix_world)
        pieces.append(mesh)
    if not pieces:
        raise ValueError('No renderable geometry in ' + str(path))
    coords = [v.co for mesh in pieces for v in mesh.vertices]
    lo = Vector([min(v[i] for v in coords) for i in range(3)])
    hi = Vector([max(v[i] for v in coords) for i in range(3)])
    scale = length / (hi.y-lo.y)
    transform = Matrix.Scale(scale, 4) @ Matrix.Translation(Vector((-(lo.x+hi.x)/2, -(lo.y+hi.y)/2, -lo.z)))
    for mesh in pieces:
        mesh.transform(transform)
        mesh.use_fake_user = True
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)
    glass = principled(class_name+'_opaque_glass', (.028, .045, .055), .13, .65)
    # Opaque tinted glazing is an explicit exterior-label policy: no see-through IDs.
    if class_name == 'car':
        shared = {
            'paint': paint('TemplatePaint', (.18,.23,.29)),
            'rubber': principled('Rubber', (.018,.018,.02), .8),
            'metal': principled('Metal', (.32,.34,.36), .23, .9),
            'red': principled('RearLamp', (.3,.009,.006), .2),
            'light': principled('HeadLamp', (.75,.8,.84), .12, .4)
        }
        for mesh in pieces:
            for i, mat in enumerate(mesh.materials):
                name = mat.name.lower() if mat else ''
                if 'car_paint' in name:
                    mesh.materials[i] = shared['paint']
                elif 'glass_red' in name or 'red_emm' in name:
                    mesh.materials[i] = shared['red']
                elif 'glass' in name:
                    mesh.materials[i] = glass
                elif 'chrome' in name or 'mirror' == name:
                    mesh.materials[i] = shared['metal']
                elif 'light' in name:
                    mesh.materials[i] = shared['light']
                else:
                    mesh.materials[i] = shared['rubber']
    else:
        for mesh in pieces:
            for i, mat in enumerate(mesh.materials):
                if mat and ('glass' in mat.name.lower() or 'window' in mat.name.lower()):
                    mesh.materials[i] = glass
    print('TEMPLATE', class_name, 'parts', len(pieces), 'dimensions_m', tuple((hi-lo)*scale), flush=True)
    return pieces


def spawn(template, class_name, instance_id, position, yaw, color):
    root = bpy.data.objects.new(f'{class_name}_{instance_id:03d}', None)
    bpy.context.scene.collection.objects.link(root)
    root.location = position
    root.rotation_euler.z = yaw
    car_paint = paint(f'Paint_{instance_id}', color) if class_name == 'car' else None
    truck_materials = {}
    for mesh in template:
        obj = bpy.data.objects.new(f'{root.name}_{mesh.name}', mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.parent = root
        obj.pass_index = instance_id
        if car_paint:
            for slot in obj.material_slots:
                if slot.material and slot.material.name.startswith('TemplatePaint'):
                    slot.link = 'OBJECT'
                    slot.material = car_paint
        else:
            for slot in obj.material_slots:
                base = slot.material
                if not base or base.name not in ('Body', 'Cloth'):
                    continue
                if base.name not in truck_materials:
                    tinted = base.copy()
                    nodes, links = tinted.node_tree.nodes, tinted.node_tree.links
                    for bsdf in [n for n in nodes if n.type == 'BSDF_PRINCIPLED']:
                        socket = bsdf.inputs['Base Color']
                        if socket.is_linked:
                            source = socket.links[0].from_socket
                            hue = nodes.new('ShaderNodeHueSaturation')
                            hue.inputs['Saturation'].default_value = 0
                            hue.inputs['Value'].default_value = 1
                            links.new(source,hue.inputs['Color'])
                            mix = nodes.new('ShaderNodeMixRGB')
                            mix.blend_type = 'MULTIPLY'
                            mix.inputs[0].default_value = 1
                            mix.inputs[2].default_value = (*[min(1,c+.1) for c in color],1)
                            links.new(hue.outputs[0],mix.inputs[1])
                            links.new(mix.outputs[0],socket)
                        else:
                            socket.default_value = (*color,1)
                    truck_materials[base.name] = tinted
                slot.link = 'OBJECT'
                slot.material = truck_materials[base.name]
    return root
