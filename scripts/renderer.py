import bpy
import numpy as np


def configure(config, scratch):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = config['samples']
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 2
    scene.cycles.transmission_bounces = 2
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = .035
    scene.render.resolution_x,scene.render.resolution_y = config['resolution']
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.color_depth = '8'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'Filmic'
    scene.view_settings.look = 'Medium High Contrast'
    scene.render.use_motion_blur = False
    scene.view_layers[0].use_pass_object_index = True
    scene.view_layers[0].pass_alpha_threshold = .5
    scene.use_nodes = True
    nodes,links = scene.node_tree.nodes,scene.node_tree.links
    nodes.clear()
    layers = nodes.new('CompositorNodeRLayers')
    composite = nodes.new('CompositorNodeComposite')
    links.new(layers.outputs['Image'],composite.inputs[0])
    ids = nodes.new('CompositorNodeOutputFile')
    ids.name = 'RawInstanceIds'
    ids.base_path = str(scratch)
    ids.format.file_format = 'OPEN_EXR'
    ids.format.color_mode = 'RGB'
    ids.format.color_depth = '32'
    ids.format.exr_codec = 'ZIP'
    ids.file_slots[0].path = 'instance_'
    links.new(layers.outputs['IndexOB'],ids.inputs[0])


def render(rgb_path, seed, scratch):
    scene = bpy.context.scene
    scene.cycles.seed = seed % 2147483647
    scene.render.filepath = str(rgb_path)
    scene.frame_set(1)
    bpy.ops.render.render(write_still=True)
    raw_path = scratch / 'instance_0001.exr'
    image = bpy.data.images.load(str(raw_path), check_existing=False)
    image.colorspace_settings.name = 'Non-Color'
    w,h = image.size
    pixels = np.empty(w*h*4,dtype=np.float32)
    image.pixels.foreach_get(pixels)
    raw = pixels.reshape(h,w,4)[::-1,:,0]
    if not np.allclose(raw,np.rint(raw),atol=1e-4):
        raise ValueError('Instance pass contains non-integer values')
    result = np.rint(raw).astype(np.uint16)
    bpy.data.images.remove(image)
    raw_path.unlink()
    return result
