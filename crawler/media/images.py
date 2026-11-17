from hashlib import sha256
from io import BytesIO
from pathlib import Path
from PIL import Image

ALLOWED_LICENSES={'CC0-1.0','CC-BY-4.0','CC-BY-SA-4.0','CC-BY-3.0','CC-BY-SA-3.0','Public domain'}

def validate_image(content):
    if len(content)>15*1024*1024:raise ValueError('Image exceeds downloader safety limit')
    with Image.open(BytesIO(content)) as image:
        image.verify()
    with Image.open(BytesIO(content)) as image:
        if min(image.size)<80:raise ValueError('Image too small for retrieval preparation')
        return dict(format=image.format,width=image.width,height=image.height,sha256=sha256(content).hexdigest())

def download_reviewed_image(entry,folder):
    import requests
    required=['url','source_url','license','creator','articleID']
    if any(not entry.get(k) for k in required):raise ValueError('Missing reviewed image provenance')
    if entry['license'] not in ALLOWED_LICENSES:raise ValueError('Unapproved image licence')
    if not entry['url'].startswith('https://'):raise ValueError('Require HTTPS media URL')
    # Approved manifest entries must also record a completed host robots/policy review.
    if entry.get('policy_reviewed') is not True:raise ValueError('Media host policy not reviewed')
    r=requests.get(entry['url'],headers={'User-Agent':'ElectronicsCourseworkDataset/1.0'},timeout=(10,30),verify=requests.certs.where())
    r.raise_for_status();metadata=validate_image(r.content)
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    suffix={'JPEG':'.jpg','PNG':'.png','WEBP':'.webp'}.get(metadata['format'])
    if suffix is None:raise ValueError('Unsupported image format')
    path=folder/(metadata['sha256']+suffix)
    if not path.exists():path.write_bytes(r.content)
    return dict(entry,**metadata,local_path=str(path))
