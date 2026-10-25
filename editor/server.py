"""Local-only TAPAS editor. Python standard library; no external dependencies."""
import argparse, hashlib, json, math, os, re, secrets, subprocess, sys, tempfile, threading, time, webbrowser, zipfile
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, unquote
ROOT=Path(__file__).resolve().parents[1]
FILES=['content.json','publications-source.json','teaching.json']
TOKEN=secrets.token_urlsafe(32)
LOCK=threading.Lock()
IMAGE_SUFFIXES={'.jpg','.jpeg','.png','.webp','.svg'}
MEDIA_SUFFIXES=IMAGE_SUFFIXES|{'.mp4'}
MAX_UPLOAD=20*1024*1024
MAX_VIDEO_UPLOAD=100*1024*1024

def image_files():
    return sorted((p for p in (ROOT/'dist/assets').iterdir()
                   if p.is_file() and not p.is_symlink() and p.suffix.lower() in MEDIA_SUFFIXES),
                  key=lambda p:p.name.lower())

def image_info(path):
    stat=path.stat()
    return {'name':path.name,'size':stat.st_size,'modified':stat.st_mtime,'kind':'video' if path.suffix.lower()=='.mp4' else 'image'}

def validate_image(name,allow_video=False):
    if not isinstance(name,str):raise ValueError('图片文件名必须是文字')
    if not name:return
    path=ROOT/'dist/assets'/name
    if (Path(name).name!=name or '\\' in name or path.suffix.lower() not in (MEDIA_SUFFIXES if allow_video else IMAGE_SUFFIXES)
            or not path.is_file() or path.is_symlink()):
        raise ValueError('图片不存在，请从图片库重新选择')

def validate_project_media(project):
    cover=project.get('cover')
    if cover is not None:
        if not isinstance(cover,dict):raise ValueError('项目封面格式无效')
        validate_image(cover.get('image',''),allow_video=True)
        if cover.get('fit','contain') not in ('contain','cover'):raise ValueError('封面显示方式无效')
        position=cover.get('position',{'x':50,'y':50})
        if not isinstance(position,dict):raise ValueError('裁切位置无效')
        for axis in ('x','y'):
            value=position.get(axis,50)
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=100:
                raise ValueError('裁切位置必须在 0–100 之间')
        if not isinstance(cover.get('alt',''),str):raise ValueError('封面说明必须是文字')
    figures=project.get('figures',[])
    if not isinstance(figures,list):raise ValueError('项目图片必须是列表')
    for figure in figures:
        if not isinstance(figure,dict) or not figure.get('image'):raise ValueError('请为每张项目图片选择文件，或移除空白图片项')
        validate_image(figure['image'],allow_video=True)
        if any(not isinstance(figure.get(k,''),str) for k in ('alt','caption')):
            raise ValueError('图片说明必须是文字')

def upload_image(raw,ext,original_name):
    signatures={'png':raw.startswith(b'\x89PNG\r\n\x1a\n') and len(raw)>=33 and raw[12:16]==b'IHDR',
                'jpg':len(raw)>=16 and raw.startswith(b'\xff\xd8\xff'),
                'webp':len(raw)>=20 and raw[:4]==b'RIFF' and raw[8:12]==b'WEBP',
                'mp4':len(raw)>=24 and raw[4:8]==b'ftyp'}
    if not signatures.get(ext):raise ValueError('请选择有效的 PNG、JPEG、WebP 或 MP4 文件')
    digest=hashlib.sha256(raw).hexdigest()
    # Reuse identical originals, including images that predate the library.
    for path in image_files():
        if path.stat().st_size==len(raw) and hashlib.sha256(path.read_bytes()).hexdigest()==digest:
            return {**image_info(path),'reused':True}
    stem=re.sub(r'[^\w-]+','-',Path(unquote(original_name)).stem,flags=re.UNICODE).strip('-')[:60] or 'image'
    path=ROOT/'dist/assets'/f'uploaded-{digest[:16]}-{stem}.{ext}'
    if path.exists():path=path.with_name(f'uploaded-{digest}-{secrets.token_hex(3)}.{ext}')
    with path.open('xb') as f:f.write(raw)
    return {**image_info(path),'reused':False}

def read_data():return {f:json.loads((ROOT/f).read_text()) for f in FILES}
def validate(d):
    if set(d)!=set(FILES):raise ValueError('Incomplete content files')
    c=d['content.json'];papers=d['publications-source.json'];seen=set()
    for a in c['areas']:
        if not a['slug'] or a['slug'] in seen or any(x not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for x in a['slug']):raise ValueError('Research topic IDs must be unique URL slugs')
        seen.add(a['slug']);ids=set()
        for p in a['projects']:
            if not p['slug'] or p['slug'] in ids or any(x not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for x in p['slug']):raise ValueError('Project IDs must be unique URL slugs')
            ids.add(p['slug'])
            validate_project_media(p)
            if any(type(i)!=int or not 0<=i<len(papers) for i in p['papers']):raise ValueError('Invalid related publication number')
    for h in c['homepage']['highlights']:
        a=next((a for a in c['areas'] if a['slug']==h['area']),None)
        if a is None or not any(p['slug']==h['project'] for p in a['projects']):raise ValueError('A homepage card refers to a missing project; remove its card first')
        if h['art'] not in c['backgrounds']:raise ValueError('Unknown card artwork')
    for p in papers:
        if type(p['year'])!=int or not isinstance(p['authors'],list):raise ValueError('Publication year must be a number; authors must be a list')
    def walk(v,project_media=False):
        if isinstance(v,dict):
            for k,x in v.items():
                if k in ('url','source') and isinstance(x,str) and x and not x.startswith(('https://','http://','mailto:','/','#')):raise ValueError('Links must start with https://, http:// or mailto:')
                if k=='image' and x:validate_image(x,allow_video=project_media)
                walk(x,project_media or ('papers' in v and k in ('cover','figures')))
        elif isinstance(v,list):
            for x in v:walk(x,project_media)
    walk(d)
def build():
    result=subprocess.run([sys.executable,str(ROOT/'render.py')],cwd=ROOT,capture_output=True,text=True)
    if result.returncode:raise ValueError('Page generation failed: '+result.stderr[-2000:])
def backup():
    folder=ROOT/'local-backups';folder.mkdir(exist_ok=True)
    path=folder/(time.strftime('%Y%m%d-%H%M%S')+f'-{time.time_ns()%1_000_000_000:09d}-'+secrets.token_hex(3)+'.zip')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for f in FILES:z.write(ROOT/f,f)
    return path

def write_content(d):
    # Replace individual JSON files atomically; failed builds restore exact old bytes.
    for name in FILES:
        path=ROOT/name
        with tempfile.NamedTemporaryFile(dir=ROOT,prefix='.',suffix='.tmp',delete=False) as f:
            temp=Path(f.name)
            try:
                f.write((json.dumps(d[name],ensure_ascii=False,indent=2)+'\n').encode())
                f.flush()
                os.fsync(f.fileno())
            except Exception:
                temp.unlink(missing_ok=True)
                raise
        try:os.replace(temp,path)
        finally:temp.unlink(missing_ok=True)

def save_content(d):
    validate(d)
    old={name:(ROOT/name).read_bytes() for name in FILES}
    saved=backup()
    try:
        write_content(d)
        build()
    except Exception:
        for name,raw in old.items():(ROOT/name).write_bytes(raw)
        build()
        raise
    return saved
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'dist'),**kwargs)
    def end_headers(self):
        # Local editing always serves fresh pages, styles and scripts.
        self.send_header('Cache-Control','no-store, max-age=0')
        super().end_headers()
    def send_head(self):
        # Last-Modified has only second precision; two quick saves can differ.
        if 'If-Modified-Since' in self.headers:del self.headers['If-Modified-Since']
        return super().send_head()
    def log_message(self,*args):pass
    def video_response(self,head=False):
        route=unquote(urlsplit(self.path).path)
        name=route.removeprefix('/assets/')
        path=ROOT/'dist/assets'/name
        if (not route.startswith('/assets/') or Path(name).name!=name or '\\' in name
                or path.suffix.lower()!='.mp4' or not path.is_file() or path.is_symlink()):
            self.send_error(404);return
        size=path.stat().st_size;start=0;end=size-1
        requested=self.headers.get('Range')
        if requested:
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',requested)
            try:
                if not match or not any(match.groups()):raise ValueError()
                left,right=match.groups()
                if left:
                    start=int(left);end=min(int(right),size-1) if right else size-1
                else:
                    length=int(right)
                    if length<=0:raise ValueError()
                    start=max(0,size-length)
                if start>=size or start>end:raise ValueError()
            except ValueError:
                self.send_response(416);self.send_header('Content-Range',f'bytes */{size}')
                self.send_header('Content-Length','0');self.end_headers();return
        self.send_response(206 if requested else 200)
        self.send_header('Content-Type','video/mp4');self.send_header('Accept-Ranges','bytes')
        self.send_header('Content-Length',str(max(0,end-start+1)))
        if requested:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        if head:return
        try:
            with path.open('rb') as video:
                video.seek(start);remaining=end-start+1
                while remaining>0:
                    chunk=video.read(min(64*1024,remaining))
                    if not chunk:break
                    self.wfile.write(chunk);remaining-=len(chunk)
        except (BrokenPipeError,ConnectionResetError):pass
    def do_HEAD(self):
        if not self.allowed():return self.reply({'error':'Use the local address printed in Terminal'},403)
        if urlsplit(self.path).path.lower().endswith('.mp4'):return self.video_response(head=True)
        return super().do_HEAD()
    def allowed(self):return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'
    def reply(self,value,status=200):
        b=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b)
    def do_GET(self):
        if not self.allowed():return self.reply({'error':'Use the local address printed in Terminal'},403)
        p=urlsplit(self.path)
        if p.path.lower().endswith('.mp4'):return self.video_response()
        if p.path=='/editor/':
            if parse_qs(p.query).get('token')!=[TOKEN]:return self.reply({'error':'Open the editor link printed in Terminal'},403)
            b=(ROOT/'editor/index.html').read_text().replace('__TOKEN__',TOKEN).encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();return self.wfile.write(b)
        if p.path in ('/editor/editor.js','/editor/editor.css'):
            b=(ROOT/p.path.lstrip('/')).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type','text/javascript; charset=utf-8' if p.path.endswith('.js') else 'text/css; charset=utf-8')
            self.end_headers();return self.wfile.write(b)
        if p.path.startswith('/api/'):
            if self.headers.get('X-Editor-Token')!=TOKEN:return self.reply({'error':'Restart the editor'},403)
            with LOCK:
                if p.path=='/api/data':return self.reply(read_data())
                if p.path=='/api/images':return self.reply([image_info(p) for p in image_files()])
                if p.path=='/api/export':
                    with tempfile.TemporaryFile() as f:
                        with zipfile.ZipFile(f,'w',zipfile.ZIP_DEFLATED) as z:
                            for x in ROOT.rglob('*'):
                                rel=x.relative_to(ROOT)
                                if x.is_file() and not any(part.startswith('.') or part in ('local-backups','__pycache__') for part in rel.parts):z.write(x,'TAPAS-local/'+str(rel))
                        f.seek(0);b=f.read()
                    self.send_response(200);self.send_header('Content-Type','application/zip');self.end_headers();return self.wfile.write(b)
            return self.reply({'error':'Not found'},404)
        # Serve only the static website; never expose source, editor or backup files.
        return super().do_GET()
    def do_POST(self):
        if not self.allowed() or self.headers.get('X-Editor-Token')!=TOKEN:return self.reply({'error':'Unauthorized'},403)
        origin=self.headers.get('Origin')
        if origin and origin!=f'http://127.0.0.1:{self.server.server_port}':return self.reply({'error':'Invalid origin'},403)
        try:
            n=int(self.headers.get('Content-Length','0'))
            limit=MAX_VIDEO_UPLOAD if self.path=='/api/upload' and self.headers.get('X-Image-Type')=='mp4' else MAX_UPLOAD
            if not 0<n<=limit:raise ValueError('图片最多 20 MB，MP4 视频最多 100 MB')
            raw=self.rfile.read(n)
            with LOCK:
                if self.path=='/api/upload':
                    return self.reply(upload_image(raw,self.headers.get('X-Image-Type',''),self.headers.get('X-Image-Name','image')))
                if self.path=='/api/save':
                    d=json.loads(raw);b=save_content(d)
                    return self.reply({'message':'已保存并更新本地预览','backup':b.name})
                if self.path=='/api/undo':
                    paths=sorted((ROOT/'local-backups').glob('*.zip'),key=lambda p:p.stat().st_mtime_ns)
                    if not paths:raise ValueError('还没有可恢复的备份')
                    with zipfile.ZipFile(paths[-1]) as z:d={f:json.loads(z.read(f)) for f in FILES}
                    save_content(d);return self.reply({'message':'已恢复上一次保存前的内容；图片原文件仍保留在图片库'})
                return self.reply({'error':'Not found'},404)
        except Exception as ex:return self.reply({'error':str(ex)},400)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--no-browser',action='store_true');args=ap.parse_args()
    build();server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    url=f'http://127.0.0.1:{server.server_port}/editor/?token={TOKEN}'
    print('TAPAS 本地编辑器\n'+url+'\n关闭此窗口或按 Ctrl+C 停止。',flush=True)
    if not args.no_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
