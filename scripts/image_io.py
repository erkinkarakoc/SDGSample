"""Lossless integer PNG and COCO RLE. NumPy is bundled with Blender."""
import struct
import zlib
import numpy as np


def write_png(path, array):
    a = np.asarray(array)
    h, w = a.shape[:2]
    channels = 1 if a.ndim == 2 else a.shape[2]
    color_type = {1: 0, 3: 2, 4: 6}[channels]
    depth = 16 if a.dtype == np.uint16 else 8
    a = a.astype('>u2' if depth == 16 else np.uint8)
    raw = b''.join(b'\x00' + row.tobytes() for row in a)
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    content = b'\x89PNG\r\n\x1a\n'
    content += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, depth, color_type, 0, 0, 0))
    content += chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b'')
    path.write_bytes(content)


def read_mask_png(path):
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    offset, parts = 8, []
    while offset < len(data):
        n = struct.unpack('>I', data[offset:offset+4])[0]
        tag, payload = data[offset+4:offset+8], data[offset+8:offset+8+n]
        if tag == b'IHDR':
            w, h, depth, color, _, _, _ = struct.unpack('>IIBBBBB', payload)
            assert color == 0 and depth in (8, 16)
        if tag == b'IDAT':
            parts.append(payload)
        offset += n + 12
    raw = np.frombuffer(zlib.decompress(b''.join(parts)), dtype=np.uint8).reshape(h, 1+w*(depth//8))
    assert np.all(raw[:, 0] == 0), 'Reader supports this exporter\'s unfiltered masks only'
    return np.frombuffer(raw[:, 1:].copy().tobytes(), dtype='>u2' if depth == 16 else np.uint8).reshape(h, w)


def encode_rle(mask):
    flat = np.asarray(mask, dtype=np.uint8).ravel(order='F')
    changes = np.flatnonzero(flat[1:] != flat[:-1]) + 1
    counts = np.diff(np.r_[0, changes, flat.size]).tolist()
    if flat[0]:
        counts.insert(0, 0)
    return {"size": list(mask.shape), "counts": counts}


def decode_rle(rle):
    counts = rle['counts']
    return np.repeat(np.arange(len(counts)) % 2, counts).reshape(rle['size'], order='F').astype(bool)


def box_from_mask(mask):
    y, x = np.nonzero(mask)
    if not len(x):
        return None
    return [int(x.min()), int(y.min()), int(x.max()+1), int(y.max()+1)]
