import subprocess

with open('chatbot/swarm_agents.py', 'rb') as f:
    content = f.read()

# Decode with latin-1 to preserve all bytes, then replace problematic sequences
text = content.decode('latin-1')

# UTF-8 sequences decoded as latin-1
replacements = {
    '\xe2\x80\x94': '--',       # em dash —
    '\xe2\x80\x93': '-',        # en dash –
    '\xe2\x80\x98': "'",        # left single quote '
    '\xe2\x80\x99': "'",        # right single quote '
    '\xe2\x80\x9c': '"',        # left double quote "
    '\xe2\x80\x9d': '"',        # right double quote "
    '\xe2\x80\xa6': '...',      # ellipsis …
    '\xe2\x80\xa2': '*',        # bullet •
    '\xe2\x9c\x85': '(check)',  # checkmark ✅
    '\xe2\x9d\x8c': '(x)',      # cross ❌
    '\xf0\x9f\x94\xa7': '',     # wrench 🔧
    '\xe2\x94\x80': '-',        # box drawing ─
    '\xc3\xa9': 'e',            # é
    '\xc3\xa0': 'a',            # à
}

for old, new in replacements.items():
    text = text.replace(old, new)

with open('chatbot/swarm_agents.py', 'wb') as f:
    f.write(text.encode('utf-8'))

print('File rewritten. Checking syntax...')
result = subprocess.run(
    ['python', '-m', 'py_compile', 'chatbot/swarm_agents.py'],
    capture_output=True, text=True
)
print('STDOUT:', result.stdout)
print('STDERR:', result.stderr)
print('Return code:', result.returncode)
if result.returncode == 0:
    print('SUCCESS: swarm_agents.py is now valid Python!')
else:
    print('STILL HAS ERRORS')
