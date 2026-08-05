import os
from collections import Counter

def check_dir(d):
    class_counts = Counter()
    if os.path.exists(d):
        files = os.listdir(d)
        for filename in files:
            if filename.endswith('.txt'):
                with open(os.path.join(d, filename), 'r') as f:
                    for line in f:
                        parts = line.split()
                        if parts:
                            class_counts[int(parts[0])] += 1
        return class_counts
    return None

print("VAL SET:")
print(check_dir(r'd:\Road_AI_Project\ai_models\dataset\unified\labels\val'))
print("\nTEST SET:")
print(check_dir(r'd:\Road_AI_Project\ai_models\dataset\unified\labels\test'))
