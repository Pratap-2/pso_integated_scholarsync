import re

with open('chatbot/swarm_agents.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Replace all non-ascii characters with a space or appropriate ascii character
def replacer(match):
    char = match.group(0)
    # Some common replacements for readability
    if char in '—–': return '-'
    if char in '""': return '"'
    if char in "''": return "'"
    if char == '…': return '...'
    if char == '•': return '*'
    if char == '✅': return '[OK]'
    if char == '❌': return '[X]'
    if char == '🔧': return ''
    if char == '─': return '-'
    if char == 'é': return 'e'
    if char == 'à': return 'a'
    # Fallback for any other non-ascii character
    return ''

# Find any non-ascii characters
cleaned_text = re.sub(r'[^\x00-\x7F]', replacer, text)

with open('chatbot/swarm_agents.py', 'w', encoding='utf-8') as f:
    f.write(cleaned_text)

print('Cleaned non-ascii characters.')

import py_compile
try:
    py_compile.compile('chatbot/swarm_agents.py', doraise=True)
    print('SUCCESS! file compiles syntax check.')
except py_compile.PyCompileError as e:
    print('COMPILE ERROR:', e)
