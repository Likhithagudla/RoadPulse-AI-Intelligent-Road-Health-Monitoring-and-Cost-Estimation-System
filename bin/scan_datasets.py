import zipfile, os, yaml, json
from pathlib import Path
import xml.etree.ElementTree as ET

SAVE_PATH = 'D:/Road_AI_Project/ai_models/dataset'

# Extract new ZIPs
for f in sorted(os.listdir(SAVE_PATH)):
    if f.endswith('.zip'):
        zip_path = os.path.join(SAVE_PATH, f)
        folder_name = f.replace('.zip','').replace(' ','_')
        extract_to = os.path.join(SAVE_PATH, folder_name)
        if os.path.exists(extract_to) and len(os.listdir(extract_to)) > 0:
            continue
        size_mb = os.path.getsize(zip_path) / (1024*1024)
        print(f'[EXTRACTING] {f} ({size_mb:.0f} MB)')
        try:
            os.makedirs(extract_to, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(extract_to)
            print('  [OK]')
        except Exception as e:
            print(f'  [FAILED] {e}')

print('\n' + '='*60)
print('  SCANNING ALL DATASETS')
print('='*60)

for ds_name in sorted(os.listdir(SAVE_PATH)):
    ds_path = os.path.join(SAVE_PATH, ds_name)
    if not os.path.isdir(ds_path):
        continue
    
    img_count = sum(len(list(Path(ds_path).rglob(e))) for e in ['*.jpg','*.jpeg','*.png','*.bmp'])
    xml_count = len(list(Path(ds_path).rglob('*.xml')))
    
    if img_count == 0 and xml_count == 0:
        continue
    
    print(f'\n=== {ds_name} ({img_count} imgs, {xml_count} xml) ===')
    
    # Folder structure - show class folders
    for item in sorted(Path(ds_path).iterdir()):
        if item.is_dir():
            subs = [s.name for s in list(item.iterdir())[:10]]
            print(f'  DIR: {item.name}/ -> {subs}')
            for sub in item.iterdir():
                if sub.is_dir():
                    sc = sum(len(list(sub.rglob(e))) for e in ['*.jpg','*.png'])
                    if sc > 0:
                        print(f'    {sub.name}/: {sc} imgs')
    
    # data.yaml
    for dy in list(Path(ds_path).rglob('data.yaml'))[:2]:
        try:
            with open(dy) as f:
                d = yaml.safe_load(f)
            names = d.get('names', {})
            if isinstance(names, list):
                names = dict(enumerate(names))
            print(f'  YOLO classes: {names}')
        except:
            pass
    
    # classes.txt
    for ct in list(Path(ds_path).rglob('classes.txt'))[:2]:
        lines = ct.read_text(errors='ignore').strip().split('\n')
        print(f'  classes.txt: {lines[:20]}')
    
    # Labels
    poly = 0
    bbox = 0
    for lf in list(Path(ds_path).rglob('*.txt'))[:300]:
        if lf.name in ['classes.txt','README.txt','README.roboflow.txt','notes.txt']:
            continue
        try:
            content = lf.read_text(errors='ignore').strip()
            if content:
                parts = content.split('\n')[0].split()
                if len(parts) > 5:
                    poly += 1
                elif len(parts) == 5:
                    bbox += 1
        except:
            pass
    if poly > 0 or bbox > 0:
        fmt = 'POLYGON' if poly > bbox else 'BBOX'
        print(f'  Labels: {fmt} (poly={poly}, bbox={bbox})')
    
    # COCO JSON
    for jf in list(Path(ds_path).rglob('*.json'))[:3]:
        try:
            with open(jf, errors='ignore') as f:
                data = json.load(f)
            if 'categories' in data:
                cats = [c['name'] for c in data['categories']]
                print(f'  COCO: {cats}')
                break
        except:
            pass
    
    # XML classes
    if xml_count > 0:
        class_names = set()
        for xf in list(Path(ds_path).rglob('*.xml'))[:100]:
            try:
                tree = ET.parse(xf)
                for obj in tree.getroot().findall('object'):
                    n = obj.find('name')
                    if n is not None:
                        class_names.add(n.text)
            except:
                pass
        if class_names:
            print(f'  XML classes: {sorted(class_names)}')
