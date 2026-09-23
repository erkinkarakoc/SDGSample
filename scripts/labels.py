import numpy as np
from image_io import box_from_mask, encode_rle


def derive_labels(instance_mask, metadata):
    known = {x['instance_id']: x for x in metadata['instances']}
    unexpected = set(np.unique(instance_mask).tolist()) - {0} - set(known)
    if unexpected:
        raise ValueError(f'Unknown rendered instance IDs: {unexpected}')
    semantic = np.zeros(instance_mask.shape, dtype=np.uint8)
    objects = []
    hidden = []
    h,w = instance_mask.shape
    for identifier, info in known.items():
        binary = instance_mask == identifier
        bounds = box_from_mask(binary)
        if bounds is None:
            hidden.append(identifier)
            continue
        semantic[binary] = info['category_id']
        x0,y0,x1,y1 = bounds
        objects.append({**info, 'bbox_xyxy': bounds, 'bbox_xywh': [x0,y0,x1-x0,y1-y0],
                        'area': int(binary.sum()), 'segmentation': encode_rle(binary),
                        'touches_image_border': x0==0 or y0==0 or x1==w or y1==h})
    return semantic,objects,hidden
