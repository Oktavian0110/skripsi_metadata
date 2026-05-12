import os
import glob

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace('data-bs-theme="dark"', 'data-bs-theme="light"')
    content = content.replace('bg-dark', 'bg-white')
    content = content.replace('text-light', 'text-dark')
    content = content.replace('hover-bg-dark', 'hover-bg-light')
    content = content.replace('border-secondary border-opacity-50', 'border')
    content = content.replace('border-secondary border-opacity-25', 'border')
    content = content.replace('bg-opacity-50', '')
    
    # Optional: convert primary neon colors to simpler ones if needed, but the variables handle it

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for filepath in glob.glob('templates/*.html'):
    replace_in_file(filepath)

print('Done!')
