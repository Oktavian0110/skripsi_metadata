import os, glob, re

def fix_ui(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Fix invisible badge text in data_master.html
    content = content.replace('class="badge bg-white border', 'class="badge bg-white text-dark border')
    
    # 2. Fix checkboxes in data_master.html
    content = content.replace('class="form-check-input bg-white border-light-subtle"', 'class="form-check-input border-secondary shadow-sm"')
    
    # 3. Fix dashboard icons (ensure they are perfectly square and centered)
    content = content.replace('class="bg-primary-subtle text-primary p-2 rounded-3 me-3"', 'class="bg-primary-subtle text-primary p-3 rounded-4 me-3 d-flex align-items-center justify-content-center"')
    content = content.replace('class="bg-info-subtle text-info p-2 rounded-3 me-3"', 'class="bg-info-subtle text-info p-3 rounded-4 me-3 d-flex align-items-center justify-content-center"')
    
    # Fix the missing heights on icons so they don't look weird
    content = content.replace('style="width: 20px;"', 'style="width: 24px; height: 24px;"')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for filepath in glob.glob('templates/*.html'):
    fix_ui(filepath)

# Fix CSS padding on btn-outline-info that was breaking btn-sm sizes
style_path = 'static/css/style.css'
with open(style_path, 'r', encoding='utf-8') as f:
    style_content = f.read()

# Remove hardcoded padding that overrides btn-sm
style_content = style_content.replace('padding: 0.75rem 1.5rem;', '')

with open(style_path, 'w', encoding='utf-8') as f:
    f.write(style_content)

print('UI alignment and visibility fixed.')
