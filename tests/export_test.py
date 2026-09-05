import json, shutil, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path
class ExportTest(unittest.TestCase):
    def test_all_files_and_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'scripts').mkdir();media=root/'.data/media/perfil';media.mkdir(parents=True)
            shutil.copy('scripts/export_zip.py',root/'scripts/export_zip.py')
            for name in ['a.mp4','b.mp4']:(media/name).write_bytes(name.encode())
            output=root/'bundle.zip'
            subprocess.run([sys.executable,str(root/'scripts/export_zip.py'),str(output)],input=json.dumps(['perfil/a.mp4','perfil/b.mp4']),text=True,check=True)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.namelist(),['perfil/a.mp4','perfil/b.mp4'])
                self.assertIsNone(archive.testzip())
            invalid=subprocess.run([sys.executable,str(root/'scripts/export_zip.py'),str(output)],input=json.dumps(['../../scripts/export_zip.py']),text=True,capture_output=True)
            self.assertNotEqual(invalid.returncode,0)
if __name__=='__main__':unittest.main()
