import os, glob, re

def polish_final(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Fix Pie Chart legend color in visualisasi.html
    content = content.replace("color: '#e2e8f0'", "color: '#334155'")
    
    # 2. Fix Action icons alignment in data_master.html (wrap in d-flex)
    # Target the PDF tab actions
    content = content.replace('<td class="text-end">\n                                        <a href="{{ url_for(\'pdf_detail\', doc_id=row.id) }}"', 
                             '<td class="text-end">\n                                        <div class="d-flex justify-content-end gap-2">\n                                        <a href="{{ url_for(\'pdf_detail\', doc_id=row.id) }}"')
    content = content.replace('</form>\n                                    </td>', 
                             '</form>\n                                        </div>\n                                    </td>')
                             
    # Target the Git tab actions
    content = content.replace('<td class="text-end">\n                                        <a href="{{ url_for(\'repo_detail\', repo_name=row.repo_name) }}"', 
                             '<td class="text-end">\n                                        <div class="d-flex justify-content-end gap-2">\n                                        <a href="{{ url_for(\'repo_detail\', repo_name=row.repo_name) }}"')

    # 3. Fix Dashboard "Input via Google Drive" layout
    # Make sure the icon container is fixed size and perfectly centered
    content = content.replace('class="bg-primary-subtle text-primary p-3 rounded-4 me-3 d-flex align-items-center justify-content-center"', 
                             'class="bg-primary-subtle text-primary rounded-4 me-3 d-flex align-items-center justify-content-center" style="width: 48px; height: 48px; flex-shrink: 0;"')
    content = content.replace('class="bg-info-subtle text-info p-3 rounded-4 me-3 d-flex align-items-center justify-content-center"', 
                             'class="bg-info-subtle text-info rounded-4 me-3 d-flex align-items-center justify-content-center" style="width: 48px; height: 48px; flex-shrink: 0;"')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for filepath in glob.glob('templates/*.html'):
    polish_final(filepath)

# Update style.css for checkbox visibility and button sizing
style_path = 'static/css/style.css'
with open(style_path, 'r', encoding='utf-8') as f:
    style_content = f.read()

# Add specific rule for form-check-input to be visible
style_content += """
/* Fix for visible checkboxes in light mode */
.form-check-input {
    border: 2px solid #cbd5e1 !important;
    cursor: pointer;
}
.form-check-input:checked {
    background-color: var(--primary-color) !important;
    border-color: var(--primary-color) !important;
}

/* Ensure action buttons in tables stay small */
.table .btn-sm {
    padding: 0.4rem 0.6rem !important;
    border-radius: 0.5rem !important;
}
"""

with open(style_path, 'w', encoding='utf-8') as f:
    f.write(style_content)

print('Final polish complete.')
