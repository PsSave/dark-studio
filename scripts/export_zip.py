"""Pack a validated manifest into a ZIP without recompressing video files."""
import json, sys, zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'.data/media'
manifest=json.loads(sys.stdin.read())
with zipfile.ZipFile(sys.argv[1],'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
    for filename in manifest:
        file=(root/filename).resolve()
        if not file.is_relative_to(root.resolve()) or not file.is_file():
            raise ValueError('Arquivo indisponível no acervo.')
        archive.write(file,arcname=filename)
