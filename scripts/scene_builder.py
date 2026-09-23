import math
import random
import bpy
from mathutils import Vector
from materials import principled, asphalt
from asset_manager import spawn

PALETTE = [(0.55,.035,.025), (.025,.12,.42), (.65,.67,.69), (.04,.045,.05),
           (.18,.26,.12), (.55,.44,.26), (.73,.73,.69), (.12,.17,.22)]


def box(name, location, dimensions, mat, bevel=0):
    verts = [(x/2,y/2,z/2) for x,y,z in
             [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
    faces = [(0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(x*dimensions[0],y*dimensions[1],z*dimensions[2]) for x,y,z in verts], [], faces)
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name,mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    if bevel:
        mod = obj.modifiers.new('Edge bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
    return obj


def environment(group_seed):
    rng = random.Random(group_seed)
    scene = bpy.context.scene
    road = asphalt()
    ground = principled('Ground', (.13,.15,.11), .95)
    concrete = principled('Concrete', (.43,.42,.39), .87)
    white = principled('Road marking', (.7,.69,.62), .8)
    dark = principled('Street metal', (.075,.085,.095), .5, .6)
    windows = principled('Building windows', (.08,.13,.17), .25, .55)
    box('Ground', (0,0,-.15), (250,250,.2), ground)
    box('Road', (0,0,-.025), (8.2,200,.05), road)
    for side in [-1,1]:
        box('Sidewalk', (side*5.05,0,.06), (1.8,160,.12), concrete, .03)
        box('Edge marking', (side*3.8,0,.003), (.1,160,.006), white)
        for y in range(-35,51,2):
            box('Curb', (side*4.15,y,.1), (.2,1.96,.2), concrete, .02)
        for y in range(-28,50,15):
            height = rng.uniform(4,10)
            width = rng.uniform(6,10)
            facade = principled('Facade', (rng.uniform(.3,.55),rng.uniform(.3,.5),rng.uniform(.28,.45)), .8)
            x = side*rng.uniform(19,23)
            box('Building', (x,y,height/2), (width,10,height), facade, .08)
            for z in range(2,int(height),3):
                for wy in [-3,0,3]:
                    box('Window', (x-side*(width/2+.015),y+wy,z), (.025,1.5,1.35), windows)
            box('Lamp post',(side*5.4,y,2.9),(.09,.09,5.8),dark)
            box('Lamp arm',(side*4.95,y,5.8),(1,.08,.08),dark)
            box('Lamp',(side*4.55,y,5.75),(.5,.22,.12),dark,.04)
    for y in range(-65,66,6):
        box('Center dash',(0,y,.004),(.13,3,.008),white)
    # Deterministic environment layout belongs to a split group, not a frame.
    return {'layout_seed': group_seed, 'road_width_m': 8.2, 'lane_centers_m': [-1.9,1.9]}


def make_sample(config, templates, index):
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in (bpy.data.meshes,bpy.data.materials,bpy.data.worlds,bpy.data.cameras,bpy.data.lights):
        for data in list(collection):
            if data.users == 0:
                collection.remove(data)
    seed = config['seed'] + index
    rng = random.Random(seed)
    group = index // 10
    env = environment(config['seed'] + 10000 + group)
    count = rng.randint(*config['vehicles_per_image'])
    classes = ['car', 'truck'] + [rng.choice(['car','truck']) for _ in range(count-2)]
    rng.shuffle(classes)
    slots = [(-1.9,-7),(-1.9,1),(-1.9,9),(1.9,-7),(1.9,1),(1.9,9)]
    rng.shuffle(slots)
    instances = []
    for instance_id, (category, (x,y)) in enumerate(zip(classes, slots), 1):
        color = rng.choice(PALETTE)
        position = [x+rng.uniform(-.13,.13),y+rng.uniform(-.5,.5),.01]
        # Assets point -Y. Right-hand traffic: positive X lane travels +Y.
        yaw = (math.pi if x>0 else 0) + rng.uniform(-.02,.02)
        spawn(templates[category], category, instance_id, position, yaw, color)
        instances.append({'instance_id': instance_id, 'category_id': 1 if category=='car' else 2,
                          'class_name': category, 'asset_id': category,
                          'position_m':position, 'yaw_rad':yaw, 'paint_color_linear':list(color)})
    cam_data = bpy.data.cameras.new('Camera')
    camera = bpy.data.objects.new('Camera',cam_data)
    scene.collection.objects.link(camera)
    camera.location = [rng.choice([-1,1])*rng.uniform(7,10), -rng.uniform(*config['camera_distance_m']),
                       rng.uniform(*config['camera_height_m'])]
    target = Vector((0,rng.uniform(-1,3),.5))
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z','Y').to_euler()
    cam_data.lens = rng.uniform(*config['focal_length_mm'])
    cam_data.sensor_width = 36
    cam_data.sensor_fit = 'HORIZONTAL'
    scene.camera = camera
    world = bpy.data.worlds.new('Sky')
    world.use_nodes = True
    nodes,links = world.node_tree.nodes, world.node_tree.links
    sky = nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'NISHITA'
    elevation = rng.uniform(*config['sun_elevation_deg'])
    rotation = rng.uniform(0,2*math.pi)
    sky.sun_elevation = math.radians(elevation)
    sky.sun_rotation = rotation
    sky.sun_disc = True
    sky.altitude = .1
    sky.air_density = rng.uniform(.8,1.2)
    sky.dust_density = rng.uniform(.4,1.5)
    links.new(sky.outputs['Color'],nodes.get('Background').inputs['Color'])
    nodes.get('Background').inputs['Strength'].default_value = .07
    scene.world = world
    scene.view_settings.exposure = rng.uniform(-.3,.3)
    return {'sample_id':index,'seed':seed,'group_id':group,'environment':env,'instances':instances,
            'camera':{'location_m':list(camera.location),'target_m':list(target),
                      'focal_length_mm':cam_data.lens,'sensor_width_mm':36},
            'lighting':{'sun_elevation_deg':elevation,'sun_rotation_rad':rotation,
                        'exposure_stops':scene.view_settings.exposure}}
