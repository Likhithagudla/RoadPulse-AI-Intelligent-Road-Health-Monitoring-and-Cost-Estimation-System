import os
from collections import Counter

label_dir = r'd:\Road_AI_Project\ai_models\dataset\unified\labels\train'
class_counts = Counter()

if os.path.exists(label_dir):
    files = os.listdir(label_dir)
    print(f"Total label files: {len(files)}")
    for filename in files:
        if filename.endswith('.txt'):
            with open(os.path.join(label_dir, filename), 'r') as f:
                for line in f:
                    parts = line.split()
                    if parts:
                        class_counts[int(parts[0])] += 1
    
    print("\nClass distribution in training set:")
    for cid in sorted(class_counts.keys()):
        print(f"Class {cid}: {class_counts[cid]} instances")
else:
    print(f"Directory not found: {label_dir}")
