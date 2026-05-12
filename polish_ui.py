import os, glob, re

def fix_ui(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix large circles in dashboard
    content = content.replace('bg-warning  p-3', 'bg-warning-subtle p-3')
    content = content.replace('bg-info  p-3', 'bg-info-subtle p-3')
    content = content.replace('bg-primary  p-3', 'bg-primary-subtle p-3')
    
    # Fix grid lines for light mode in charts
    content = content.replace("rgba(255, 255, 255, 0.05)", "rgba(0, 0, 0, 0.05)")
    content = content.replace("rgba(255, 255, 255, 0.1)", "rgba(0, 0, 0, 0.1)")
    
    # Darken chart font color
    content = content.replace("Chart.defaults.color = '#64748b'", "Chart.defaults.color = '#334155'")
    
    # Remove opacity-75 which makes text too light
    content = re.sub(r'\bopacity-75\b', '', content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for filepath in glob.glob('templates/*.html'):
    fix_ui(filepath)

# Update style.css text-secondary to be darker
style_path = 'static/css/style.css'
with open(style_path, 'r', encoding='utf-8') as f:
    style_content = f.read()

style_content = style_content.replace('--text-secondary: #64748b;', '--text-secondary: #475569;')
# Darken placeholders
style_content = style_content.replace('color: #64748b !important;', 'color: #94a3b8 !important;')

with open(style_path, 'w', encoding='utf-8') as f:
    f.write(style_content)

print('UI Polished.')
