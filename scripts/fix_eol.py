from pathlib import Path

files = [
    Path('.github/workflows/unit.yml'),
    Path('.github/workflows/integration.yml'),
]

for p in files:
    if not p.exists():
        print('Missing', p)
        continue
    b = p.read_bytes()
    nb = b.replace(b"\r\n", b"\n")
    if nb != b:
        p.write_bytes(nb)
        print('Fixed EOL for', p)
    else:
        print('No change for', p)
