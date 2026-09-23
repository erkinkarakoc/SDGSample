import tempfile
from pathlib import Path
import unittest
import numpy as np
from image_io import write_png,read_mask_png,encode_rle,decode_rle
from labels import derive_labels


class LabelTests(unittest.TestCase):
    def test_integer_png_preserves_large_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'ids.png'
            a=np.array([[0,1,257],[4096,65535,2]],dtype=np.uint16)
            write_png(path,a)
            np.testing.assert_array_equal(read_mask_png(path),a)

    def test_coco_column_major_rle(self):
        a=np.array([[0,1,0],[1,1,0]],dtype=bool)
        self.assertEqual(encode_rle(a),{'size':[2,3],'counts':[1,3,2]})
        np.testing.assert_array_equal(decode_rle(encode_rle(a)),a)
        for a in [np.zeros((2,3),bool),np.ones((2,3),bool)]:
            np.testing.assert_array_equal(decode_rle(encode_rle(a)),a)

    def test_occlusion_class_merge_and_hidden_instances(self):
        # Two cars remain distinct instances, one truck occludes the first car.
        ids=np.array([[1,1,0,3],[1,2,2,3],[0,2,2,0]],dtype=np.uint16)
        meta={'instances':[{'instance_id':i,'category_id':c} for i,c in [(1,1),(2,2),(3,1),(4,2)]]}
        semantic,objects,hidden=derive_labels(ids,meta)
        self.assertEqual(hidden,[4])
        self.assertEqual(objects[0]['bbox_xyxy'],[0,0,2,2])
        self.assertEqual(objects[0]['area'],3)
        self.assertEqual(objects[2]['bbox_xyxy'],[3,0,4,2])
        np.testing.assert_array_equal(semantic,[[1,1,0,1],[1,2,2,1],[0,2,2,0]])

    def test_unknown_render_id_rejected(self):
        with self.assertRaises(ValueError):
            derive_labels(np.array([[7]],dtype=np.uint16),{'instances':[]})


if __name__=='__main__':
    unittest.main()
