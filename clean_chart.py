import os, glob

def update_charts(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace("Chart.defaults.color = '#94a3b8'", "Chart.defaults.color = '#64748b'")
    content = content.replace("pointBackgroundColor: '#0f172a'", "pointBackgroundColor: '#ffffff'")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for filepath in glob.glob('templates/*.html'):
    update_charts(filepath)

print('Charts updated.')
