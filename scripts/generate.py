"""Blender entry point. -- --count 1 --output outputs/quality_check for a pilot."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from asset_manager import load_template
from scene_builder import make_sample
from renderer import configure,render
from labels import derive_labels
from exporter import json_write,write_sample,finalize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config/dataset.json')
    parser.add_argument('--count',type=int)
    parser.add_argument('--start',type=int,default=0)
    parser.add_argument('--output')
    parser.add_argument('--resume',action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    config = json.loads((ROOT/args.config).read_text(encoding='utf-8'))
    if args.output:
        config['output_dir'] = args.output
    output = (ROOT/config['output_dir']).resolve()
    if not output.is_relative_to(ROOT/'outputs'):
        raise ValueError('Dataset output must stay within project outputs/')
    for folder in ['images','instance','semantic','overlays','labels','metadata','annotations','_scratch']:
        (output/folder).mkdir(parents=True,exist_ok=True)
    fingerprint = hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    previous = output/'config_used.json'
    if args.resume and previous.exists() and json.loads(previous.read_text()) != config:
        raise ValueError('Resume configuration differs from the dataset configuration')
    json_write(previous,config)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    templates = {name:load_template(ROOT/data['file'],name,data['length_m']) for name,data in config['assets'].items()}
    # Drop unused imported shader/image datablocks (including removed badge textures).
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)
    for img in list(bpy.data.images):
        if img.users == 0:
            bpy.data.images.remove(img)
    asset_hashes = {k:hashlib.sha256((ROOT/v['file']).read_bytes()).hexdigest() for k,v in config['assets'].items()}
    source_hash = hashlib.sha256(b''.join(p.read_bytes() for p in sorted((ROOT/'scripts').glob('*.py')))).hexdigest()
    total = config['count'] if args.count is None else args.count
    if args.start < 0 or args.start + total > config['count']:
        raise ValueError('Requested sample range exceeds configured dataset size')
    for index in range(args.start,args.start+total):
        stem = f'{index:06d}'
        if args.resume and (output/'metadata'/f'{stem}.json').exists():
            existing = json.loads((output/'metadata'/f'{stem}.json').read_text(encoding='utf-8'))
            required = [output/folder/(stem+suffix) for folder,suffix in
                        [('images','.png'),('semantic','.png'),('instance','.png'),('overlays','.png'),('labels','.txt')]]
            if existing.get('config_sha256') == fingerprint and existing.get('asset_sha256') == asset_hashes and existing.get('source_sha256') == source_hash and all(p.exists() for p in required):
                continue
        started = time.perf_counter()
        metadata = make_sample(config,templates,index)
        configure(config,output/'_scratch')
        masks = render(output/'images'/f'{stem}.png',metadata['seed'],output/'_scratch')
        semantic,objects,hidden = derive_labels(masks,metadata)
        present = {o['category_id'] for o in objects if o['area']>=config['min_visible_pixels']}
        if present != {1,2}:
            raise RuntimeError(f'{stem}: both classes must have sufficient visible pixels')
        train_end = config['split_counts']['train']
        val_end = train_end + config['split_counts']['val']
        metadata.update({'split':'train' if index<train_end else 'val' if index<val_end else 'test',
                         'blender_version':bpy.app.version_string,'config_sha256':fingerprint,
                         'asset_sha256':asset_hashes,'source_sha256':source_hash,
                         'render_seconds':round(time.perf_counter()-started,3)})
        camera = bpy.context.scene.camera
        bpy.context.view_layer.update()
        metadata['camera']['matrix_world'] = [list(row) for row in camera.matrix_world]
        w,h = config['resolution']
        focal = metadata['camera']['focal_length_mm']/36*w
        metadata['camera']['K'] = [[focal,0,w/2],[0,focal,h/2],[0,0,1]]
        metadata['camera']['convention'] = 'Blender local -Z forward, +Y up; K uses image x right/y down; square pixels'
        write_sample(output,metadata,masks,semantic,objects,hidden)
        if index == 0:
            bpy.ops.wm.save_as_mainfile(filepath=str(output/'example_scene.blend'))
        print(f'SAMPLE_COMPLETE {index+1}/{config["count"]} seconds={metadata["render_seconds"]} objects={len(objects)}',flush=True)
    records = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((output/'metadata').glob('*.json'))]
    finalize(output,config,records)
    print(f'DATASET_COMPLETE count={len(records)} path={output}',flush=True)


if __name__ == '__main__':
    main()
