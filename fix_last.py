import os, glob, re

def fix_all(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove all blur-3xl glowing divs
    content = re.sub(r'<div[^>]*blur-3xl[^>]*></div>', '', content)
    
    # 2. Fix unreadable badge in ai_results.html
    content = content.replace('bg-primary  text-info', 'bg-info-subtle text-info')
    content = content.replace('bg-primary text-info', 'bg-info-subtle text-info')
    
    # 3. Fix pie chart border in visualisasi.html
    content = content.replace("borderColor: 'rgba(30, 41, 59, 1)'", "borderColor: '#ffffff'")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for filepath in glob.glob('templates/*.html'):
    fix_all(filepath)

print('All final fixes applied.')
