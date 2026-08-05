import torch
import os

model_path = "D:/Road_AI_Project/ai_models/weights/best.pt"
if os.path.exists(model_path):
    try:
        data = torch.load(model_path, map_location='cpu', weights_only=False)
        # For YOLO models, class names are often in the model data
        names = data.get('names', None)
        if hasattr(data.get('model'), 'names'):
            names = data['model'].names
        
        print("Model Classes Found:")
        print(names)
        
        # If names is not found, try to see the architecture
        if not names:
           # Check if it's a dict or model
           if isinstance(data, dict):
               print("Keys in data:", data.keys())
               if 'model' in data:
                   m = data['model']
                   if hasattr(m, 'names'):
                       print("Model Names:", m.names)
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Model not found")
