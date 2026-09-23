"""Independent on-disk label consistency checks; run with Blender's bundled Python."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import numpy as np
from image_io import read_mask_png, decode_rle, box_from_mask


def validate(output, expected=100):
    records = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((output/'metadata').glob('*.json'))]
    assert len(records)==expected, (len(records),expected)
    for directory, extension in [('images','png'),('semantic','png'),('instance','png'),('labels','txt'),('overlays','png')]:
        assert len(list((output/directory).glob('*.'+extension)))==expected,directory
    coco = json.loads((output/'annotations/coco.json').read_text(encoding='utf-8'))
    assert len(coco['images']) == expected
    assert len({a['id'] for a in coco['annotations']}) == len(coco['annotations'])
    assert {c['id']:c['name'] for c in coco['categories']}=={1:'car',2:'truck'}
    hashes, groups, counts, sizes = set(),{}, {1:0,2:0}, {1:[],2:[]}
    truncations = 0
    for r in records:
        stem = f"{r['sample_id']:06d}"
        instance = read_mask_png(output/'instance'/f'{stem}.png')
        semantic = read_mask_png(output/'semantic'/f'{stem}.png')
        assert instance.dtype.itemsize == 2
        assert semantic.dtype.itemsize == 1
        assert instance.shape == semantic.shape == (r['height'],r['width'])
        assert set(np.unique(semantic)) <= {0,1,2}
        assert np.array_equal(instance==0,semantic==0)
        assert set(np.unique(instance))-{0} == {o['instance_id'] for o in r['objects']}
        assert {o['category_id'] for o in r['objects']} == {1,2}
        rgb = (output/r['image']).read_bytes()
        assert struct.unpack('>II',rgb[16:24]) == (r['width'],r['height'])
        digest = hashlib.sha256(rgb).hexdigest()
        assert digest not in hashes, 'Duplicate RGB'
        hashes.add(digest)
        if r['group_id'] in groups:
            assert groups[r['group_id']] == r['split'],'Scene group leakage'
        groups[r['group_id']] = r['split']
        anns = {a['instance_id']:a for a in coco['annotations'] if a['image_id']==r['sample_id']}
        assert len(anns)==len(r['objects'])
        lines = (output/'labels'/f'{stem}.txt').read_text().splitlines()
        assert len(lines)==len(r['objects'])
        for o,line in zip(r['objects'],lines):
            binary = instance==o['instance_id']
            assert np.array_equal(decode_rle(o['segmentation']),binary)
            assert np.array_equal(decode_rle(anns[o['instance_id']]['segmentation']),binary)
            assert int(binary.sum())==o['area']==anns[o['instance_id']]['area']
            assert box_from_mask(binary)==o['bbox_xyxy']
            x,y,x1,y1 = o['bbox_xyxy']
            assert [x,y,x1-x,y1-y]==o['bbox_xywh']==anns[o['instance_id']]['bbox']
            assert np.all(semantic[binary]==o['category_id'])
            tokens = [float(x) for x in line.split()]
            expected_yolo = [o['category_id']-1,(x+x1)/2/r['width'],(y+y1)/2/r['height'],(x1-x)/r['width'],(y1-y)/r['height']]
            assert np.allclose(tokens,expected_yolo,atol=1e-7)
            counts[o['category_id']] += 1
            sizes[o['category_id']].append(o['area'])
            truncations += o['touches_image_border']
    for split in ('train','val','test'):
        subset = json.loads((output/'annotations'/f'{split}.json').read_text())
        ids = {r['sample_id'] for r in records if r['split']==split}
        assert {im['id'] for im in subset['images']} == ids
        assert all(a['image_id'] in ids for a in subset['annotations'])
    report = {'status':'PASS','images':len(records),'instances':sum(counts.values()),
              'class_counts':{'car':counts[1],'truck':counts[2]},
              'visible_area_px':{name:{'min':min(sizes[c]),'median':float(np.median(sizes[c])),'max':max(sizes[c])}
                                 for c,name in [(1,'car'),(2,'truck')]},
              'border_touching_instances':int(truncations),
              'split_counts':{s:sum(r['split']==s for r in records) for s in ['train','val','test']},
              'scene_groups':groups,
              'checks':['unique RGB','image and mask sizes','integer mask IDs','class and instance mapping',
                        'mask tight boxes','COCO RLE roundtrip','mask areas','YOLO coordinates',
                        'both classes per image','disjoint scene groups','export file counts'],
              'scope':'Structural annotation validation; not real-world model accuracy or photorealism certification'}
    (output/'validation_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    parser.add_argument('--expected',type=int,default=100)
    args=parser.parse_args()
    validate(args.output,args.expected)
