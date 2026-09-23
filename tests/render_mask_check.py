"""Tiny actual-render regression: a front object occludes a rear object."""
import sys
import tempfile
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_builder import box
from materials import principled
from renderer import configure,render
from labels import derive_labels

bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
mat=principled('Test',(.5,.5,.5))
rear=box('rear',(0,0,0),(2,2,.2),mat)
rear.pass_index=1
front=box('front',(.5,.5,1),(1,1,.2),mat)
front.pass_index=2
hidden=box('hidden',(.5,.5,-1),(.3,.3,.2),mat)
hidden.pass_index=3
camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'))
scene.collection.objects.link(camera)
camera.location=(0,0,10)
camera.rotation_euler=(Vector((0,0,0))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO'
camera.data.ortho_scale=4
scene.camera=camera
with tempfile.TemporaryDirectory() as temp:
    folder=Path(temp)
    configure({'samples':4,'resolution':[64,64]},folder)
    scene.cycles.use_denoising=False
    mask=render(folder/'rgb.png',123,folder)
    assert set(np.unique(mask))=={0,1,2},np.unique(mask)
    assert mask[20,40]==2,'Front object must own upper-right pixels'
    assert mask[40,20]==1,'Rear object must remain visible lower-left'
    assert mask[0,0]==0,'Background must be zero'
    semantic,objects,unseen=derive_labels(mask,{'instances':[
        {'instance_id':1,'category_id':1}, {'instance_id':2,'category_id':2},
        {'instance_id':3,'category_id':1}]})
    assert unseen==[3]
    assert all(obj['area']>0 for obj in objects)
    print('PASS: actual Cycles IndexOB, Y orientation, occlusion, hidden-object omission, background IDs',flush=True)
