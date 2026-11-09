import shutil, os
from pathlib import Path

SAVE_PATH = str(Path(__file__).resolve().parent.parent / "ai_models/dataset")

DELETE_FOLDERS = [
    'archive_(10)',
    'archive_(12)',
    'archive_(14)',
    'archive_(13)',
    'archive_(9)',
    'archive_(2)',
    'archive_(4)',
    'pothole-images-kaggle',
    'road-issues-kaggle',
    'ravelling-kaggle',
    'rdd-kaggle',
    'road-damage-all-kaggle',
    'road-defects-kaggle',
    'road-hazards-kaggle',
    'lane-markings-kaggle',
    'Seg_Manhole',
]

DELETE_ZIPS = [
    'archive.zip', 'archive (1).zip', 'archive (2).zip', 'archive (3).zip',
    'archive (4).zip', 'archive (5).zip', 'archive (6).zip', 'archive (7).zip',
    'archive (8).zip', 'archive (9).zip', 'archive (10).zip', 'archive (11).zip',
    'archive (12).zip', 'archive (13).zip', 'archive (14).zip',
]

total_freed = 0

print('DELETING USELESS FOLDERS:')
print('=' * 50)
for folder in DELETE_FOLDERS:
    path = os.path.join(SAVE_PATH, folder)
    if os.path.exists(path):
        size = sum(f.stat().st_size for f in Path(path).rglob('*') if f.is_file())
        size_mb = size / (1024*1024)
        total_freed += size
        print(f'  [DEL] {folder} ({size_mb:.0f} MB)')
        shutil.rmtree(path)
    else:
        print(f'  [---] {folder} (not found)')

print()
print('DELETING ZIP FILES:')
print('=' * 50)
for zf in DELETE_ZIPS:
    path = os.path.join(SAVE_PATH, zf)
    if os.path.exists(path):
        size = os.path.getsize(path)
        size_mb = size / (1024*1024)
        total_freed += size
        print(f'  [DEL] {zf} ({size_mb:.0f} MB)')
        os.remove(path)
    else:
        print(f'  [---] {zf} (not found)')

gb_freed = total_freed / (1024*1024*1024)
print()
print('=' * 50)
print(f'  TOTAL SPACE FREED: {gb_freed:.2f} GB')
print('=' * 50)

print()
print('REMAINING USEFUL DATASETS:')
print('=' * 50)
for name in sorted(os.listdir(SAVE_PATH)):
    path = os.path.join(SAVE_PATH, name)
    if os.path.isdir(path):
        imgs = sum(len(list(Path(path).rglob(e))) for e in ['*.jpg','*.png','*.jpeg'])
        print(f'  {name}: {imgs} images')
