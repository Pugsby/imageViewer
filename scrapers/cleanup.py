# I wrote this entire script with AI, I'm way too lazy to do this

interval = 3600

def run():
    import os
    import hashlib
    from pathlib import Path
    from itertools import combinations
    from PIL import Image
    import imagehash

    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
    SIMILARITY_THRESHOLD = 97

    def get_images(root: str):
        images = []
        for path in Path(root).rglob('*'):
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                images.append(path)
        return images

    def compute_hash(path: Path):
        try:
            img = Image.open(path).convert('RGB')
            return imagehash.phash(img, hash_size=16)
        except Exception:
            return None

    def similarity(h1, h2) -> float:
        max_bits = len(h1.hash) ** 2
        diff = h1 - h2
        return (1 - diff / max_bits) * 100

    def image_quality_score(path: Path) -> tuple:
        """Score by resolution then file size — higher is better."""
        try:
            with Image.open(path) as img:
                w, h = img.size
            size = path.stat().st_size
            return (w * h, size)
        except Exception:
            return (0, 0)

    print("Scanning ./images recursively...")
    images = get_images('./images')
    print(f"Found {len(images)} image(s).")

    hashes = {}
    for img_path in images:
        h = compute_hash(img_path)
        if h is not None:
            hashes[img_path] = h

    visited = set()
    duplicate_groups = []

    paths = list(hashes.keys())
    for i, a in enumerate(paths):
        if a in visited:
            continue
        group = [a]
        for b in paths[i + 1:]:
            if b in visited:
                continue
            sim = similarity(hashes[a], hashes[b])
            if sim >= SIMILARITY_THRESHOLD:
                group.append(b)
                visited.add(b)
        if len(group) > 1:
            visited.add(a)
            duplicate_groups.append(group)

    if not duplicate_groups:
        print("No duplicate images found.")
        return

    print(f"\nFound {len(duplicate_groups)} duplicate group(s).")

    deleted = 0
    freed_bytes = 0

    for group in duplicate_groups:
        ranked = sorted(group, key=image_quality_score, reverse=True)
        keeper = ranked[0]
        to_delete = ranked[1:]

        print(f"\n  Keeping:  {keeper}  {image_quality_score(keeper)}")
        for path in to_delete:
            size = path.stat().st_size
            print(f"  Deleting: {path}  {image_quality_score(path)}")
            try:
                path.unlink()
                deleted += 1
                freed_bytes += size
            except Exception as e:
                print(f"    ERROR deleting {path}: {e}")

    print(f"\nDone. Deleted {deleted} file(s), freed {freed_bytes / 1024:.1f} KB.")
