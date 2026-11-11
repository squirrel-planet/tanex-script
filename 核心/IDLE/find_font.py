with open('E:\\代码\\项目\\Tanex Script\\核心\\IDLE\\doc_viewer.py', 'rb') as f:
    content = f.read()

# Find all occurrences of font = self.FONT_FAMILY, 10

import re

matches = list(re.finditer(b'font\\s*=\\s*self\\.FONT_FAMILY\\s*,\\s*10\\s*,\\s*[\\\'\\"].*?[\\\'"]', content))
for m in re.finditer(b'font\\s*=\\s*self\\.FONT_FAMILY\\s*,\\s*10\\s*,\\s*[\\\'\\"].*?[\\\'"]', content):
    print(f'Found at {m.start()}: {content[m.start():m.end()]}')

# Also check for self.font_family
matches2 = list(re.finditer(b'font\\s*=\\s*self\\.font_family\\s*,\\s*10\\s*,\\s*[\\\'\\"].*?[\\\'"]', content))
for m in matches2:
    print(f'Found at {m.start()}: {content[m.start():m.end()]}')
