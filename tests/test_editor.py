"""Run with python3 -m unittest discover -s tests -v. All writes use a temporary copy."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile

SOURCE=Path(__file__).resolve().parents[1]

class EditorIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='tapas-editor-tests-')
        cls.root=Path(cls.temp.name)/'TAPAS-local'
        shutil.copytree(SOURCE,cls.root,ignore=shutil.ignore_patterns('local-backups','__pycache__','tests'))
        spec=importlib.util.spec_from_file_location('tapas_test_server',cls.root/'editor/server.py')
        cls.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.original={name:(cls.root/name).read_bytes() for name in cls.module.FILES}
        cls.http=cls.module.ThreadingHTTPServer(('127.0.0.1',0),cls.module.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.http.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join();cls.temp.cleanup()

    def setUp(self):
        for name,raw in self.original.items():(self.root/name).write_bytes(raw)
        shutil.rmtree(self.root/'local-backups',ignore_errors=True)
        self.module.build()

    def request(self,path,body=None,headers=None):
        h={'X-Editor-Token':self.module.TOKEN,**(headers or {})}
        if isinstance(body,dict):body=json.dumps(body).encode();h['Content-Type']='application/json'
        req=urllib.request.Request(self.base+path,data=body,headers=h)
        try:
            with urllib.request.urlopen(req) as res:return res.status,res.read()
        except urllib.error.HTTPError as ex:return ex.code,ex.read()

    def document(self):return copy.deepcopy(self.module.read_data())

    def test_legacy_build_does_not_modify_user_content(self):
        for name,raw in self.original.items():self.assertEqual((self.root/name).read_bytes(),raw)
        html=(self.root/'dist/index.html').read_text()
        self.assertEqual(html.count('class="highlight-card"'),9)
        self.assertNotIn('project-cover-image',html)
        code,raw=self.request('/api/images')
        self.assertEqual(code,200)
        self.assertTrue(all({'name','size','modified'}<=set(i) for i in json.loads(raw)))

    def test_covers_figures_save_backup_undo_and_export(self):
        data=self.document();p=data['content.json']['areas'][0]['projects'][0]
        p['cover']={'image':'kinetic.png','alt':'Cover <example>','fit':'cover','position':{'x':18,'y':84}}
        p['figures']=[{'image':'kinetic.png','caption':'Axes <intact> & 中文说明','alt':'Figure one'},
                      {'image':'magnetogenesis.png','caption':'Second figure','alt':'Figure two'}]
        code,raw=self.request('/api/save',data);self.assertEqual(code,200,raw)
        with zipfile.ZipFile(self.root/'local-backups'/json.loads(raw)['backup']) as z:
            for name,original in self.original.items():self.assertEqual(z.read(name),original)
        home=(self.root/'dist/index.html').read_text();page=(self.root/'dist/research/magnetogenesis/index.html').read_text()
        self.assertIn('object-fit:cover;object-position:18% 84%',home)
        self.assertIn('Axes &lt;intact&gt; &amp; 中文说明',page)
        self.assertEqual(page.count('class="project-figure"'),2)
        self.assertLess(page.index('Figure one'),page.index('Figure two'))
        self.assertIn('aria-label="Open original image"',page)
        code,raw=self.request('/api/export');self.assertEqual(code,200)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertFalse(any('local-backups/' in n for n in z.namelist()))
            self.assertIn('TAPAS-local/editor/editor.js',z.namelist())
            self.assertEqual(z.read('TAPAS-local/dist/assets/kinetic.png'),(SOURCE/'dist/assets/kinetic.png').read_bytes())
        code,raw=self.request('/api/undo',{});self.assertEqual(code,200,raw)
        self.assertEqual(self.module.read_data(),{name:json.loads(raw) for name,raw in self.original.items()})
        self.assertNotIn('project-cover-image',(self.root/'dist/index.html').read_text())

    def test_default_cover_is_uncropped_and_captions_optional(self):
        data=self.document();p=data['content.json']['areas'][0]['projects'][0]
        p['cover']={'image':'kinetic.png'};p['figures']=[{'image':'kinetic.png'}]
        code,raw=self.request('/api/save',data);self.assertEqual(code,200,raw)
        self.assertIn('object-fit:contain;object-position:50% 50%',(self.root/'dist/index.html').read_text())

    def test_uploads_preserve_bytes_and_reuse_existing_images(self):
        raw=(SOURCE/'dist/assets/kinetic.png').read_bytes()
        code,response=self.request('/api/upload',raw,{'X-Image-Type':'png','X-Image-Name':'different.png'})
        self.assertEqual(code,200);self.assertEqual(json.loads(response)['name'],'kinetic.png');self.assertTrue(json.loads(response)['reused'])
        # PNG permits ancillary metadata chunks before IEND; create a distinct original.
        import struct,zlib
        chunk=b'tEXt'+b'Comment\0Local test original'
        raw=raw[:-12]+struct.pack('>I',len(chunk)-4)+chunk+struct.pack('>I',zlib.crc32(chunk)&0xffffffff)+raw[-12:]
        code,response=self.request('/api/upload',raw,{'X-Image-Type':'png','X-Image-Name':'scientific%20figure.png'})
        self.assertEqual(code,200,response);info=json.loads(response);self.assertFalse(info['reused'])
        self.assertEqual((self.root/'dist/assets'/info['name']).read_bytes(),raw)
        code,response=self.request('/api/upload',raw,{'X-Image-Type':'png','X-Image-Name':'renamed.png'})
        self.assertTrue(json.loads(response)['reused']);self.assertEqual(json.loads(response)['name'],info['name'])
        data=self.document();data['content.json']['areas'][0]['projects'][0]['figures']=[{'image':info['name']}]
        self.assertEqual(self.request('/api/save',data)[0],200)
        self.assertEqual(self.request('/api/undo',{})[0],200)
        self.assertEqual((self.root/'dist/assets'/info['name']).read_bytes(),raw)

    def test_bad_media_cannot_replace_content(self):
        invalid=[{'cover':{'image':'../content.json'}},{'cover':{'image':'site.js'}},
                 {'cover':{'image':'absent.png'}},{'cover':{'image':'kinetic.png','fit':'invalid'}},
                 {'cover':{'image':'kinetic.png','position':{'x':101}}},
                 {'cover':{'image':'kinetic.png','position':{'x':float('nan')}}},
                 {'figures':[{'image':''}]},{'figures':[{'image':'kinetic.png','caption':99}]}]
        for media in invalid:
            with self.subTest(media=media):
                data=self.document();data['content.json']['areas'][0]['projects'][0].update(media)
                self.assertEqual(self.request('/api/save',data)[0],400)
                for name,raw in self.original.items():self.assertEqual((self.root/name).read_bytes(),raw)
        self.assertEqual(self.request('/api/upload',b'not an image',{'X-Image-Type':'png'})[0],400)

    def test_failed_build_restores_exact_content_and_preview(self):
        data=self.document();data['content.json']['homepage']['bio']='Test change'
        # Teaching renders after Home, so this fails after a partial site rebuild.
        del data['teaching.json']['courses'][0]['title']
        code,response=self.request('/api/save',data)
        self.assertEqual(code,400)
        self.assertIn('Page generation failed',json.loads(response)['error'])
        for name,raw in self.original.items():self.assertEqual((self.root/name).read_bytes(),raw)
        self.assertNotIn('Test change',(self.root/'dist/index.html').read_text())

    def test_repeated_saves_undo_most_recent_even_within_one_second(self):
        for i in range(3):
            data=self.document();data['content.json']['homepage']['bio']=f'Version {i}'
            self.assertEqual(self.request('/api/save',data)[0],200)
        self.assertEqual(self.request('/api/undo',{})[0],200)
        self.assertEqual(self.module.read_data()['content.json']['homepage']['bio'],'Version 1')
        self.assertEqual(len(list((self.root/'local-backups').glob('*.zip'))),4)

    def test_local_access_and_source_protection(self):
        self.assertEqual(self.request('/api/data',headers={'X-Editor-Token':'wrong'})[0],403)
        self.assertEqual(self.request('/api/undo',{},headers={'Origin':'https://example.invalid'})[0],403)
        for path in ['/content.json','/editor/server.py','/local-backups/']:
            self.assertEqual(self.request(path)[0],404)
        self.assertEqual(self.request('/editor/editor.js')[0],200)
        self.assertEqual(self.request('/editor/editor.css')[0],200)

    def test_preview_revision_changes_on_save_and_returns_on_undo(self):
        def revision():
            code,raw=self.request('/assets/preview-version.json')
            self.assertEqual(code,200)
            return json.loads(raw)['revision']
        before=revision()
        data=self.document();data['content.json']['homepage']['bio']='A newly saved preview'
        self.assertEqual(self.request('/api/save',data)[0],200)
        after=revision();self.assertNotEqual(before,after)
        for path in ['index.html','teaching/index.html','research/magnetogenesis/index.html']:
            html=(self.root/'dist'/path).read_text()
            self.assertIn(f'name="tapas-preview-revision" content="{after}"',html)
            self.assertIn(f'/assets/site.js?v={after}',html)
        self.assertEqual(self.request('/api/undo',{})[0],200)
        self.assertEqual(revision(),before)

    def test_research_keywords_remain_saved_but_not_displayed(self):
        data=self.document();data['content.json']['areas'][0]['tags']=['New <keyword>', 'Other tag']
        self.assertEqual(self.request('/api/save',data)[0],200)
        html=(self.root/'dist/research/magnetogenesis/index.html').read_text()
        self.assertNotIn('class="tag"',html)
        self.assertEqual(self.module.read_data()['content.json']['areas'][0]['tags'],['New <keyword>', 'Other tag'])

    def test_video_library_cover_gallery_and_undo(self):
        # Small ISO media header exercises transport and preservation without transcoding.
        original=b'\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isommp42'+bytes(range(256))
        code,raw=self.request('/api/upload',original,{'X-Image-Type':'mp4','X-Image-Name':'test-movie.mp4'})
        self.assertEqual(code,200,raw);name=json.loads(raw)['name']
        code,raw=self.request('/api/upload',original,{'X-Image-Type':'mp4','X-Image-Name':'renamed.mp4'})
        self.assertEqual(code,200);self.assertTrue(json.loads(raw)['reused'])
        self.assertEqual(json.loads(raw)['name'],name)
        code,raw=self.request('/api/images');self.assertIn({'name':name,'kind':'video'},[{k:i[k] for k in ('name','kind')} for i in json.loads(raw)])
        data=self.document();p=data['content.json']['areas'][0]['projects'][0]
        p['cover']={'image':name};p['figures']=[{'image':name,'caption':'Video caption'}]
        code,raw=self.request('/api/save',data);self.assertEqual(code,200,raw)
        home=(self.root/'dist/index.html').read_text();page=(self.root/'dist/research/magnetogenesis/index.html').read_text()
        self.assertIn('<video class="project-cover-image"',home)
        self.assertIn('autoplay data-cover-loop',home)
        self.assertIn('controls muted loop playsinline',page)
        self.assertIn('<figcaption>Video caption</figcaption>',page)
        code,raw=self.request('/api/export');self.assertEqual(code,200)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:self.assertEqual(z.read('TAPAS-local/dist/assets/'+name),original)
        self.assertEqual(self.request('/api/undo',{})[0],200)
        self.assertEqual((self.root/'dist/assets'/name).read_bytes(),original)
        data=self.document();data['content.json']['areas'][0]['image']=name
        self.assertEqual(self.request('/api/save',data)[0],400)

    def test_video_stream_ranges_and_head(self):
        original=bytes(range(256))*4
        (self.root/'dist/assets/range-test.mp4').write_bytes(original)
        for requested,expected in [('bytes=0-15',original[:16]),('bytes=100-',original[100:]),('bytes=-12',original[-12:])]:
            with self.subTest(requested=requested):
                req=urllib.request.Request(self.base+'/assets/range-test.mp4',headers={'Range':requested})
                with urllib.request.urlopen(req) as res:
                    self.assertEqual(res.status,206);self.assertEqual(res.read(),expected)
                    self.assertEqual(res.headers['Content-Type'],'video/mp4')
                    self.assertEqual(res.headers['Accept-Ranges'],'bytes')
        req=urllib.request.Request(self.base+'/assets/range-test.mp4',method='HEAD')
        with urllib.request.urlopen(req) as res:
            self.assertEqual(int(res.headers['Content-Length']),len(original));self.assertEqual(res.read(),b'')
        for requested in ['bytes=9999-','bytes=3-2','bytes=-0','bad-range']:
            self.assertEqual(self.request('/assets/range-test.mp4',headers={'Range':requested})[0],416)

    def test_local_previews_bypass_stale_browser_caches(self):
        request=urllib.request.Request(self.base+'/',headers={'If-Modified-Since':'Wed, 31 Dec 2099 23:59:59 GMT'})
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.status,200)
            self.assertIn('no-store',response.headers['Cache-Control'])
            self.assertIn('<!doctype html>',response.read().decode())

if __name__=='__main__':unittest.main()
