import os

files = ['app.py', 'ai_grader.py', 'git_extractor.py', 'pdf_extractor.py', 'analyzer.py']

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if 'import logging' not in content:
        content = 'import logging\n' + content
        
    if f == 'app.py' and 'logging.basicConfig' not in content:
        content = content.replace('import logging\n', 'import logging\nlogging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", filename="app.log", filemode="a")\n')
        
    content = content.replace('print("WARNING:', 'logging.warning("')
    content = content.replace("print('WARNING:", "logging.warning('")
    content = content.replace('print("ERROR:', 'logging.error("')
    content = content.replace("print('ERROR:", "logging.error('")
    content = content.replace('print(f"ERROR', 'logging.error(f"ERROR')
    content = content.replace('print(f"Error', 'logging.error(f"Error')
    content = content.replace('print(f"Gagal', 'logging.error(f"Gagal')
    content = content.replace('print(f"WARNING', 'logging.warning(f"WARNING')
    content = content.replace('print(', 'logging.info(')
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)

print("Done")
