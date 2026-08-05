import os

label_dir = r'd:\Road_AI_Project\ai_models\dataset\unified\labels\train'
count = 0
examples = []

if os.path.exists(label_dir):
    for filename in os.listdir(label_dir):
        if filename.endswith('.txt'):
            with open(os.path.join(label_dir, filename), 'r') as f:
                for line in f:
                    if line.startswith('13 '):
                        count += 1
                        examples.append(filename)
                        break
    print(f"Total files with Traffic_Sign labels in train set: {count}")
    if examples:
        print("\nSome examples:")
        print(examples[:10])
else:
    print(f"Directory not found: {label_dir}")
