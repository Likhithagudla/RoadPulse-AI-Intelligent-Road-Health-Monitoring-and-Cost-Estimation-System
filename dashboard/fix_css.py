
import os

path = r'd:\Road_AI_Project\dashboard\styles.css'
with open(path, 'rb') as f:
    content = f.read()

null_index = content.find(b'\x00')
if null_index != -1:
    # Check if there is some valid text before the null bytes that shouldn't be there
    # or if we should just truncate.
    clean_content = content[:null_index]
    
    # We also want to remove any trailing partial lines if we truncated in the middle of a line
    # but since we want to remove the WHOLE messed up section, this is fine.
    
    with open(path, 'wb') as f:
        f.write(clean_content)
    print(f"Truncated file at index {null_index}")
else:
    print("No null bytes found.")
