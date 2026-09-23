"""Re-fetch the exact selected public assets using the recorded provider metadata.

Uses standard BlenderKit download endpoints; no account tokens are required for
these free assets. Source licenses are documented in assets/README.md.
"""
import hashlib
import json
import urllib.request
import uuid
from pathlib import Path


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent':'SynthData-learning-demo/1.0'})
    return urllib.request.urlopen(request,timeout=120)


def main():
    root=Path(__file__).resolve().parent
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    for entry in manifest['assets']:
        target=root/entry['file']
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==entry['sha256']:
            print('Already verified:',entry['file'])
            continue
        source=json.loads((root/entry['source_metadata']).read_text(encoding='utf-8-sig'))
        item=next(f for f in source['files'] if f['fileType']==entry['file_type'])
        with fetch(item['downloadUrl']+'?scene_uuid='+str(uuid.uuid4())) as response:
            download=json.load(response)
        partial=target.with_suffix('.part')
        with fetch(download['filePath']) as response, partial.open('wb') as output:
            while True:
                chunk=response.read(1024*1024)
                if not chunk:
                    break
                output.write(chunk)
        if hashlib.sha256(partial.read_bytes()).hexdigest()!=entry['sha256']:
            raise RuntimeError('Downloaded asset hash differs from the tested source: '+str(partial))
        partial.replace(target)
        print('Downloaded and verified:',entry['file'])


if __name__=='__main__':
    main()
