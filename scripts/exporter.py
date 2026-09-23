import json
from pathlib import Path
import numpy as np
from image_io import write_png

CATEGORIES = [{'id':1,'name':'car','supercategory':'vehicle'}, {'id':2,'name':'truck','supercategory':'vehicle'}]


def json_write(path, data):
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')


def write_sample(output, metadata, instance_mask, semantic, objects, hidden):
    stem = f"{metadata['sample_id']:06d}"
    write_png(output/'instance'/f'{stem}.png',instance_mask)
    write_png(output/'semantic'/f'{stem}.png',semantic)
    palette = np.array([[0,0,0],[49,186,255],[255,155,48]], dtype=np.uint8)
    rgba = np.zeros((*semantic.shape,4),dtype=np.uint8)
    rgba[:,:,:3] = palette[semantic]
    rgba[:,:,3] = np.where(semantic>0,155,0).astype(np.uint8)
    write_png(output/'overlays'/f'{stem}.png',rgba)
    h,w = semantic.shape
    rows = []
    for obj in objects:
        x,y,bw,bh = obj['bbox_xywh']
        rows.append(f"{obj['category_id']-1} {(x+bw/2)/w:.8f} {(y+bh/2)/h:.8f} {bw/w:.8f} {bh/h:.8f}")
    (output/'labels'/f'{stem}.txt').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    record = {**metadata,'width':w,'height':h,'image':f'images/{stem}.png',
              'bbox_definition':'tight visible raster mask; max edges exclusive',
              'unseen_instance_ids':hidden,'objects':objects}
    json_write(output/'metadata'/f'{stem}.json',record)
    return record


def finalize(output, config, records):
    records.sort(key=lambda r:r['sample_id'])
    all_coco = {'info':{'description':'Car / truck synthetic pilot; visible raster masks'},
                'images':[],'annotations':[],'categories':CATEGORIES}
    ann_id = 1
    for record in records:
        all_coco['images'].append({'id':record['sample_id'],'file_name':record['image'],
                                  'width':record['width'],'height':record['height'],
                                  'split':record['split'],'group_id':record['group_id']})
        for obj in record['objects']:
            all_coco['annotations'].append({'id':ann_id,'image_id':record['sample_id'],
                'category_id':obj['category_id'],'bbox':obj['bbox_xywh'],'area':obj['area'],
                'iscrowd':0,'segmentation':obj['segmentation'],'instance_id':obj['instance_id']})
            ann_id += 1
    json_write(output/'annotations'/'coco.json',all_coco)
    for split in ('train','val','test'):
        subset = {r['sample_id'] for r in records if r['split']==split}
        coco = {**all_coco,'images':[x for x in all_coco['images'] if x['id'] in subset],
                'annotations':[x for x in all_coco['annotations'] if x['image_id'] in subset]}
        json_write(output/'annotations'/f'{split}.json',coco)
        (output/f'{split}.txt').write_text('\n'.join('./'+r['image'] for r in records if r['split']==split)+'\n',encoding='utf-8')
    (output/'dataset.yaml').write_text(f'path: "{output.as_posix()}"\ntrain: train.txt\nval: val.txt\ntest: test.txt\nnames:\n  0: car\n  1: truck\n',encoding='utf-8')
    small_records = [{**{k:r[k] for k in ['sample_id','image','split','seed','group_id','width','height']},
                      'objects':[{k:o[k] for k in ['instance_id','class_name','bbox_xyxy','area']} for o in r['objects']]} for r in records]
    page = (Path(__file__).parent/'viewer.html').read_text(encoding='utf-8').replace('__RECORDS__',json.dumps(small_records))
    (output/'preview.html').write_text(page,encoding='utf-8')
    json_write(output/'manifest.json',{'count':len(records),'categories':CATEGORIES,'config':config,
               'blender_version':records[0]['blender_version'] if records else None,
               'mask_policy':'IndexOB integer surface IDs, no antialiasing; opaque glazing; no motion blur',
               'splits':{s:sum(r['split']==s for r in records) for s in ['train','val','test']}})
