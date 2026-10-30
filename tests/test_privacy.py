import base64, pathlib, struct, sys, tempfile, unittest, zipfile, zlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import privacy_check
import package as source_package


def png_with_text(text):
    def chunk(kind,payload):
        return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'tEXt',b'Comment\0'+text.encode())+chunk(b'IDAT',zlib.compress(b'\0\0\0\0'))+chunk(b'IEND',b'')


class PrivacyTests(unittest.TestCase):
    def test_release_source_and_metadata_are_clean(self):
        _,problems=privacy_check.check(ROOT)
        self.assertEqual(problems,[])

    def test_private_paths_emails_and_credentials_are_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder)
            email='person'+'@'+'private.invalid'
            path='C:'+chr(92)+'Users'+chr(92)+'private-person'
            secret='sk'+'-ant-'+('x'*24)
            (root/'README.md').write_text('\n'.join([email,path,secret]),encoding='utf8')
            _,problems=privacy_check.check(root)
            reasons={reason for _,reason in problems}
            self.assertTrue({'email address','personal Windows path','provider token'}<=reasons)
            self.assertNotIn(secret,str(problems))

    def test_png_and_embedded_image_metadata_are_scanned(self):
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder);(root/'assets').mkdir()
            data=png_with_text('private-display-name')
            (root/'assets/image.png').write_bytes(data)
            (root/'README.md').write_text('data:image/png;base64,'+base64.b64encode(data).decode(),encoding='utf8')
            _,problems=privacy_check.check(root,deny_terms=['private-display-name'])
            self.assertEqual({name for name,reason in problems},{'assets/image.png','README.md'})

    def test_unapproved_binary_and_invalid_media_are_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder);(root/'assets').mkdir()
            (root/'assets/payload.bin').write_bytes(b'unknown')
            (root/'assets/image.png').write_bytes(b'invalid')
            _,problems=privacy_check.check(root)
            self.assertEqual(len(problems),2)

    def test_zip_excludes_local_files_and_uses_fixed_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder)/'source';root.mkdir()
            (root/'README.md').write_text('Clean source\n',encoding='utf8')
            for ignored in ['.git','.local','__pycache__']:
                (root/ignored).mkdir();(root/ignored/'private.txt').write_text('do not publish')
            archive=pathlib.Path(folder)/'release.zip'
            source_package.package(archive,root=root)
            with zipfile.ZipFile(archive) as reader:
                self.assertEqual(reader.namelist(),['claude/README.md'])
                self.assertEqual(reader.infolist()[0].date_time,(2020,1,1,0,0,0))


if __name__=='__main__':unittest.main()
