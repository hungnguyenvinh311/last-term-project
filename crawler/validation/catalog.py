from collections import Counter
from pathlib import Path
from crawler.config.settings import CATEGORIES,ROOT

def validate(products,manifest,target=20):
    ids=[p['articleID'] for p in products]
    valid=set(CATEGORIES.values())
    counts=Counter(p['categoryID'] for p in products)
    coverage={field:sum(bool(p.get(field)) for p in products) for field in ['productName','brand','description','price','imagePath']}
    missing_images=[p['articleID'] for p in products if p.get('imagePath') and not (ROOT/p['imagePath']).is_file()]
    provenance_ids=[entry['articleID'] for entry in manifest]
    return dict(products=len(products),category_counts={k:counts[v] for k,v in CATEGORIES.items()},
        shortfalls={k:max(0,target-counts[v]) for k,v in CATEGORIES.items()},coverage=coverage,
        duplicate_ids=len(ids)-len(set(ids)),invalid_category_ids=sorted({p['categoryID'] for p in products}-valid),
        missing_image_files=missing_images,provenance_matches=(sorted(ids)==sorted(provenance_ids)),
        image_download_status='External source images are not downloaded without a reviewed licence manifest',
        embeddings='Not generated; this is catalogue preparation, not an implemented retrieval model')
