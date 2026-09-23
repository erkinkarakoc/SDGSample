import bpy


def principled(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color[:3], 1)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    mat.diffuse_color = (*color[:3], 1)
    return mat


def paint(name, color):
    mat = principled(name, color, 0.27, 0.55)
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Clearcoat'].default_value = 0.55
    bsdf.inputs['Clearcoat Roughness'].default_value = 0.16
    return mat


def asphalt():
    mat = principled('Asphalt', (0.065, 0.067, 0.073), .87)
    n, links = mat.node_tree.nodes, mat.node_tree.links
    tex = n.new('ShaderNodeTexNoise')
    tex.inputs['Scale'].default_value = 85
    tex.inputs['Detail'].default_value = 2
    coord = n.new('ShaderNodeTexCoord')
    links.new(coord.outputs['Object'], tex.inputs['Vector'])
    ramp = n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (.035, .038, .043, 1)
    ramp.color_ramp.elements[1].color = (.11, .115, .12, 1)
    links.new(tex.outputs['Fac'], ramp.inputs[0])
    links.new(ramp.outputs[0], n.get('Principled BSDF').inputs['Base Color'])
    bump = n.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .22
    bump.inputs['Distance'].default_value = .025
    links.new(tex.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs[0], n.get('Principled BSDF').inputs['Normal'])
    return mat
