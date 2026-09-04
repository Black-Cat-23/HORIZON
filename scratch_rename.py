import os
from pathlib import Path

workspace = Path('c:/Users/Ankit/Desktop/Projects/HORIZON')
for path in workspace.rglob('*'):
    if path.is_file() and path.suffix in ['.md', '.html', '.cs', '.txt', '.json']:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content.replace('COARSE-ALIGN-X', 'HORIZON').replace('Coarse Align X', 'HORIZON').replace('coarse align x', 'HORIZON')
            
            if new_content != content:
                with open(path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(new_content)
                print(f"Updated {path}")
        except Exception as e:
            pass
