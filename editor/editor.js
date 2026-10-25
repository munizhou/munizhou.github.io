'use strict';
const token=document.body.dataset.editorToken;
let data,images=[],tab=0,dirty=false,busy=false;
const status=document.querySelector('#status'),form=document.querySelector('#form'),dialog=document.querySelector('#media-dialog');
const labels={opportunities:'当前招聘机会',details_url:'详细说明链接',lead:'项目负责人',affiliation:'所属机构',email:'邮箱（直接显示）',topics:'课程主题讲义',news:'新闻',profile_sections:'个人页面重点内容',items:'条目',name:'姓名',chinese_name:'中文名',role:'身份',position:'职位 / 单位',text:'简介',biography:'详细介绍',background:'教育背景',links:'链接',label:'显示文字',url:'链接地址',image:'图片',title:'标题',short:'简称',category:'研究方向说明',question:'科学问题',summary:'简短介绍',body:'详细介绍段落',projects:'具体项目',keyword:'项目关键词',stage:'项目阶段',details:'项目详情',papers:'相关论文（编号从 0 开始）',tags:'关键词',alt:'图片替代文字（供屏幕阅读器使用）',caption:'图片说明',authors:'全部作者（每位作者一项）',year:'发表年份',journal:'期刊',volume:'卷',issue:'期',pages:'页码 / 文章编号',doi:'DOI',code:'课程编号',terms:'学期',level:'课程级别',description:'介绍',context:'机构 / 活动',profile_links:'个人链接',highlights:'首页项目卡片',area:'研究主题 ID',project:'项目 ID',art:'备用装饰配图',bio:'首页自我介绍',intro_role:'首页职位',science_title:'研究介绍标题',people:'成员',courses:'课程',other:'其他教学',outreach:'科普活动',PI:'课题组负责人',overview_visual:'Research 总览配图'};
const hidden=new Set(['provenance','author_source','source','source_width','source_height','crop']);
const tabs=['首页','Team','Research','Publications','Teaching','图片库'];
const openDetails=new Map();
let inputId=0;
const isVideo=name=>/\.mp4$/i.test(name||'');
const asset=name=>'/assets/'+encodeURIComponent(name);
const displayName=name=>name.replace(/^uploaded-[a-f0-9]{16,64}-/,'');
const sizeLabel=size=>size>=1024*1024?(size/1024/1024).toFixed(1)+' MB':Math.max(1,Math.round(size/1024))+' KB';
function el(tag,text,cls){const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x}
function button(text,fn,cls){const b=el('button',text,cls);b.type='button';b.onclick=fn;return b}
function confirmAction(message){return new Promise(resolve=>{const prompt=el('dialog'),title=el('h2','确认操作'),description=el('p',message),actions=el('div',undefined,'actions');title.id='confirm-title';prompt.setAttribute('aria-labelledby',title.id);function finish(value){prompt.close();prompt.remove();resolve(value)}actions.append(button('取消',()=>finish(false)),button('确认',()=>finish(true),'primary'));prompt.append(title,description,actions);prompt.addEventListener('cancel',e=>{e.preventDefault();finish(false)});document.body.append(prompt);prompt.showModal()})}
function change(){dirty=true;status.dataset.state='dirty';status.textContent='尚未保存：点击「保存并更新预览」，打开的本地网站预览会自动刷新。'}
function labeled(parent,text,input){const id='field-'+(++inputId);input.id=id;const label=el('label',text);label.htmlFor=id;parent.append(label,input);return input}
function textField(parent,label,value,onchange,multiline=false){const input=el(multiline?'textarea':'input');input.value=value??'';labeled(parent,label,input);input.oninput=()=>{onchange(input.value);change()};return input}
function disclosure(title,key,open=false){const d=el('details');d.dataset.key=key;d.open=openDetails.has(key)?openDetails.get(key):open;d.append(el('summary',title));return d}
async function api(path,opts={}){const res=await fetch('/api/'+path,{...opts,headers:{'X-Editor-Token':token,...opts.headers}});if(!res.ok){const d=await res.json();throw Error(d.error||'操作失败')}return res}
function originalLink(name){const a=el('a',isVideo(name)?'查看原视频 ↗':'查看原图 ↗','media-original');a.href=asset(name);a.target='_blank';a.rel='noopener';return a}
function mediaElement(name,label,css,controls=true){const media=el(isVideo(name)?'video':'img',undefined,css);if(isVideo(name)){media.controls=controls;media.muted=true;media.playsInline=true;media.preload='metadata';media.setAttribute('aria-label',label)}else{media.alt=label;media.loading='lazy'}media.src=asset(name);return media}
function imageControl(parent,value,onchange,label='图片',allowRemove=true,allowVideos=false){
 const box=el('div',undefined,'image-field');box.setAttribute('role','group');box.setAttribute('aria-label',label);
 function draw(){box.replaceChildren();if(value){const im=mediaElement(value,label,'thumb');box.append(im,el('p',displayName(value),'file-name'))}else box.append(el('small',allowVideos?'尚未选择图片或 MP4 视频':'尚未选择图片'));
 const actions=el('div',undefined,'actions');actions.append(button(value?'更换文件':'从图片库选择',()=>openLibrary({title:'选择'+label,allowVideos,onSelect:names=>{value=names[0];onchange(value);change();draw()}})));
 if(value){if(allowRemove)actions.append(button(allowVideos?'移除文件':'移除图片',()=>{value='';onchange(value);change();draw()},'delete'));actions.append(originalLink(value))}box.append(actions)}
 draw();parent.append(box);return box;
}
function imageUsage(){const uses=new Map();const add=(name,label)=>{if(!name)return;if(!uses.has(name))uses.set(name,new Set());uses.get(name).add(label)};
 const c=data['content.json'];add(c.principal_investigator.image,'Team · '+c.principal_investigator.name);for(const p of c.people)add(p.image,'Team · '+p.name);
 add('portrait.jpg','首页 · Muni Zhou');add('favicon.svg','网站图标');
 for(const a of c.areas){add(a.image,a.title+' · 主题页顶部图片');add(a.overview_visual?.image,a.title+' · 总览图');for(const p of a.projects){add(p.cover?.image,p.title+' · 封面');for(const f of p.figures||[])add(f.image,p.title+' · 详情图')}}
 for(const [key,v]of Object.entries(c.backgrounds))add(v.image,'装饰背景 · '+key);return uses;
}
function lock(value){busy=value;document.querySelectorAll('header button').forEach(b=>b.disabled=value);document.querySelector('main').inert=value;dialog.inert=value;document.querySelector('#close-media').disabled=value}
async function action(fn){if(busy)return;lock(true);try{await fn()}catch(e){status.dataset.state='error';status.textContent='未完成：'+e.message}finally{lock(false)}}
function libraryView(parent,{select,multiple=false,selected=new Set(),onSelection,allowVideos=true}={}){
 const drop=el('div',undefined,'drop-zone'),file=el('input');file.type='file';file.accept='.png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp'+(allowVideos?',.mp4,video/mp4':'');file.multiple=true;file.hidden=true;file.setAttribute('aria-label','上传媒体文件');
 const message=el('div',undefined,'library-message');message.setAttribute('role','status');
 drop.append(el('p','拖拽文件到这里，或从电脑选择文件'),button(allowVideos?'上传图片或视频':'上传图片',()=>file.click()),file,el('small',allowVideos?'PNG、JPEG、WebP（20 MB）或 MP4（100 MB）· 原文件保留，相同文件自动复用':'PNG、JPEG、WebP · 每张最多 20 MB · 保留原图，相同文件自动复用'));
 const toolbar=el('div',undefined,'library-toolbar'),search=el('input'),count=el('span');search.type='search';search.placeholder='搜索文件名或使用位置';search.setAttribute('aria-label','搜索图片');toolbar.append(search,count,button('刷新列表',async()=>{try{images=await(await api('images')).json();draw();message.textContent='已重新读取本地 assets 文件夹。未保存的编辑已保留。'}catch(e){message.textContent=e.message;message.classList.add('error')}}));
 const grid=el('div',undefined,'media-grid');parent.append(drop,message,toolbar,grid);
 function draw(){const uses=imageUsage(),query=search.value.toLocaleLowerCase().trim();const filtered=images.filter(im=>(allowVideos||!isVideo(im.name))&&(im.name+' '+[...(uses.get(im.name)||[])]).toLocaleLowerCase().includes(query));count.textContent=filtered.length+' 个文件';grid.replaceChildren();
  if(!filtered.length)grid.append(el('p',query?'没有匹配的文件。':'图片库为空，上传第一个文件。','empty-state'));
  for(const im of filtered){const card=el('div',undefined,'media-card');card.classList.toggle('selected',selected.has(im.name));const thumb=select?button('',()=>{if(multiple){selected.has(im.name)?selected.delete(im.name):selected.add(im.name);draw();onSelection?.(selected)}else select([im.name])},'media-thumb'):el('a',undefined,'media-thumb');
   if(select){thumb.setAttribute('aria-label','选择 '+displayName(im.name));if(multiple)thumb.setAttribute('aria-pressed',String(selected.has(im.name)))}else{thumb.href=asset(im.name);thumb.target='_blank';thumb.rel='noopener';thumb.setAttribute('aria-label','查看原图 '+displayName(im.name))}
   const img=mediaElement(im.name,displayName(im.name),'',false);thumb.append(img);
   const body=el('div',undefined,'media-card-body'),meta=el('span',sizeLabel(im.size),'media-meta');if(isVideo(im.name)){meta.textContent='MP4 视频 · '+sizeLabel(im.size);img.onloadedmetadata=()=>{meta.textContent='MP4 · '+img.videoWidth+' × '+img.videoHeight+' · '+Math.round(img.duration)+' 秒 · '+sizeLabel(im.size)}}else img.onload=()=>{meta.textContent=img.naturalWidth+' × '+img.naturalHeight+' · '+sizeLabel(im.size)};
   const usage=[...(uses.get(im.name)||[])];body.append(el('span',displayName(im.name),'media-name'),meta,el('span',usage.length?'使用位置：'+usage.join('；'):'尚未使用','media-usage'),originalLink(im.name));card.append(thumb,body);grid.append(card);
  }
 }
 async function upload(files){if(busy||!files.length)return;lock(true);let added=0,reused=0;const errors=[];
  try{for(const [i,f]of Array.from(files).entries()){message.classList.remove('error');message.textContent=`正在上传 ${i+1}/${files.length}：${f.name}`;
    try{let ext=({'image/png':'png','image/jpeg':'jpg','image/webp':'webp','video/mp4':'mp4'})[f.type];if(!ext){const suffix=f.name.split('.').pop().toLowerCase();ext=({'png':'png','jpg':'jpg','jpeg':'jpg','webp':'webp','mp4':'mp4'})[suffix]}if(!ext||ext==='mp4'&&!allowVideos)throw Error(allowVideos?'仅支持 PNG、JPEG、WebP 或 MP4':'此位置仅支持图片');const limit=ext==='mp4'?100:20;if(f.size>limit*1024*1024)throw Error('超过 '+limit+' MB');
     if(ext!=='mp4'){const localURL=URL.createObjectURL(f);try{const check=new Image();check.src=localURL;await check.decode()}finally{URL.revokeObjectURL(localURL)}}
     const r=await(await api('upload',{method:'POST',headers:{'X-Image-Type':ext,'X-Image-Name':encodeURIComponent(f.name)},body:f})).json();r.reused?reused++:added++;if(!images.some(im=>im.name===r.name))images.unshift(r);if(multiple)selected.add(r.name);
    }catch(e){errors.push(f.name+'：'+e.message)}
   }
   search.value='';draw();onSelection?.(selected);message.classList.toggle('error',errors.length>0);message.textContent=`已上传 ${added} 个文件，复用已有文件 ${reused} 个。`+(select?' 请选中要使用的文件。':' 可在 Research 或 Team 中选择使用。')+(errors.length?'\n未上传：'+errors.join('；'):'');
   status.textContent='图片原文件已保留在本地图片库。'+(dirty?'表单修改尚未保存。':'选择图片后请保存，才会更新网站。');
  }finally{file.value='';lock(false)}
 }
 file.onchange=()=>upload(file.files);
 for(const event of ['dragenter','dragover'])drop.addEventListener(event,e=>{e.preventDefault();drop.classList.add('dragover')});
 drop.addEventListener('dragleave',e=>{if(!drop.contains(e.relatedTarget))drop.classList.remove('dragover')});
 drop.addEventListener('drop',e=>{e.preventDefault();drop.classList.remove('dragover');upload(e.dataTransfer.files)});
 search.oninput=draw;draw();
}
async function openLibrary({title='选择图片',onSelect,multiple=false,allowVideos=false}){try{images=await(await api('images')).json()}catch(e){status.textContent='无法刷新图片库：'+e.message;return}const body=document.querySelector('#media-body'),footer=document.querySelector('#media-footer');body.replaceChildren();footer.replaceChildren();document.querySelector('#media-title').textContent=title;document.querySelector('#media-help').textContent=multiple?'可选择多个文件，分别添加说明并调整顺序。':allowVideos?'选择已有图片或 MP4，也可上传新文件。':'选择已有图片，或上传新图片。';const selected=new Set();
 const choose=names=>{onSelect(names);dialog.close()};let confirm;
 if(multiple){confirm=button('添加选中的图片（0）',()=>choose([...selected]),'primary');confirm.disabled=true;footer.append(confirm)}
 libraryView(body,{select:choose,multiple,selected,allowVideos,onSelection:()=>{confirm.textContent=`添加选中的图片（${selected.size}）`;confirm.disabled=!selected.size}});dialog.showModal();
}
function projectMedia(parent,project){
 const coverSection=el('div',undefined,'media-section');coverSection.append(el('h3','项目封面'),el('small','用于首页项目卡片和本项目详情。默认完整显示；切换为「裁切填满」后可调整位置。支持图片和 MP4 视频；视频卡片静音循环，详情页可手动播放。未选择时保留现有首页装饰配图。'));
 const settings=el('div');
 const cover=()=>project.cover||{image:'',alt:'',fit:'contain',position:{x:50,y:50}};
 const update=(key,value)=>{project.cover={...cover(),[key]:value}};
 imageControl(coverSection,cover().image,value=>{update('image',value);drawCover()},'项目封面',true,true);coverSection.append(settings);parent.append(coverSection);
 function drawCover(){settings.replaceChildren();const c=cover();if(!c.image)return;
  textField(settings,'封面替代文字',c.alt||'',v=>update('alt',v));
  const fit=el('select');for(const [value,label]of [['contain','完整显示（科学图默认）'],['cover','裁切填满（仅影响展示）']]){const opt=el('option',label);opt.value=value;fit.append(opt)}fit.value=c.fit||'contain';labeled(settings,'封面显示方式',fit);
  const preview=el('div',undefined,'cover-preview'),img=mediaElement(c.image,'项目封面效果预览','');preview.append(img);settings.append(preview);
  const controls=el('div'),ranges=el('div',undefined,'range-grid');controls.append(el('small','左右 / 上下移动取景位置。只有超出封面边框的方向会发生裁切。'),ranges);const sliders=[];
  for(const [axis,label]of [['x','水平位置'],['y','垂直位置']]){const wrap=el('div'),slider=el('input'),output=el('span');slider.type='range';slider.min=0;slider.max=100;slider.step=1;slider.value=c.position?.[axis]??50;const l=el('label',label+' '),id='field-'+(++inputId);slider.id=id;l.htmlFor=id;l.append(output);wrap.append(l,slider);ranges.append(wrap);output.textContent=slider.value+'%';sliders.push({axis,slider,output});slider.oninput=()=>{update('position',{x:50,y:50,...cover().position,[axis]:Number(slider.value)});output.textContent=slider.value+'%';paint();change()}}
  controls.append(button('恢复居中',()=>{update('position',{x:50,y:50});for(const s of sliders){s.slider.value=50;s.output.textContent='50%'}paint();change()}));settings.append(controls);
  function paint(){const state=cover();img.style.objectFit=state.fit||'contain';img.style.objectPosition=`${state.position?.x??50}% ${state.position?.y??50}%`;controls.hidden=state.fit!=='cover'}
  fit.onchange=()=>{update('fit',fit.value);paint();change()};paint();
 }
 drawCover();
 const figuresSection=el('div',undefined,'media-section');figuresSection.append(el('h3','项目详情图片 / 视频'),el('small','图片和 MP4 视频均完整显示，保留坐标轴、图例与原始比例。说明文字显示在图片下方，读者可点击查看原图。封面与详情图互相独立，可以重复使用同一张图。'));const list=el('div');figuresSection.append(list);
 function drawFigures(){list.replaceChildren();const figures=project.figures||[];if(!figures.length)list.append(el('p','还没有详情图片。','empty-state'));
  figures.forEach((figure,i)=>{const item=el('div',undefined,'figure-editor');item.append(el('h3','图片 '+(i+1)));imageControl(item,figure.image,v=>{figure.image=v},'详情图片 '+(i+1),false,true);textField(item,'图片说明 '+(i+1),figure.caption||'',v=>figure.caption=v,true);textField(item,'替代文字 '+(i+1),figure.alt||'',v=>figure.alt=v);
   const actions=el('div',undefined,'actions'),up=button('上移',()=>{[figures[i-1],figures[i]]=[figures[i],figures[i-1]];change();drawFigures()}),down=button('下移',()=>{[figures[i+1],figures[i]]=[figures[i],figures[i+1]];change();drawFigures()});up.disabled=i===0;down.disabled=i===figures.length-1;actions.append(up,down,button('移除此项',async()=>{if(await confirmAction('移除这张详情图及其说明？原文件仍保留在图片库。')){figures.splice(i,1);change();drawFigures()}},'delete'));item.append(actions);list.append(item)
  });
 }
 figuresSection.append(button('添加详情图片',()=>openLibrary({title:'添加项目详情图片 / 视频',multiple:true,allowVideos:true,onSelect:names=>{project.figures??=[];project.figures.push(...names.map(image=>({image,caption:'',alt:''})));change();drawFigures()}})));parent.append(figuresSection);drawFigures();
}
function rememberDetails(){for(const d of form.querySelectorAll('details[data-key]'))openDetails.set(d.dataset.key,d.open)}
function itemLabel(key,item){if(key==='highlights'){const area=data['content.json'].areas.find(a=>a.slug===item.area);return area?.projects.find(p=>p.slug===item.project)?.title||item.project}return item.name||item.title||item.label||item.project||'此项'}
function orderControls(items,index,path,label,indexed=true){
 const controls=el('div',undefined,'order-controls');controls.dataset.orderId=JSON.stringify([path,index]);controls.setAttribute('role','group');controls.setAttribute('aria-label','调整顺序：'+label);
 controls.append(el('span',`${index+1} / ${items.length}`,'order-position'));
 for(const [delta,text]of [[-1,'上移'],[1,'下移']]){
  const move=button(text,()=>{
   const next=index+delta;if(next<0||next>=items.length)return;
   rememberDetails();
   // Array-index paths must follow the moved records, including nested open panels.
   if(indexed){const first=path+'.'+index,second=path+'.'+next,states=[...openDetails];openDetails.clear();for(const [key,value]of states){const mapped=key===first||key.startsWith(first+'.')?second+key.slice(first.length):key===second||key.startsWith(second+'.')?first+key.slice(second.length):key;openDetails.set(mapped,value)}}
   [items[index],items[next]]=[items[next],items[index]];change();render(false);
   const target=[...form.querySelectorAll('[data-order-id]')].find(x=>x.dataset.orderId===JSON.stringify([path,next]));
   const buttons=[...(target?.querySelectorAll('button')||[])];const focus=buttons.find(b=>b.dataset.direction===String(delta)&&!b.disabled)||buttons.find(b=>!b.disabled);
   focus?.focus({preventScroll:true});target?.scrollIntoView({block:'nearest'});
  });move.dataset.direction=String(delta);move.setAttribute('aria-label',text+'：'+label);move.disabled=index+delta<0||index+delta>=items.length;controls.append(move);
 }
 return controls;
}
function emptyItem(key){const defaults={opportunities:{title:'New opportunity',description:'',url:'',details_url:''},topics:{title:'New topic',url:''},people:{name:'New member',role:'',text:'',image:''},projects:{slug:'project-'+Date.now(),title:'New project',stage:'',question:'',summary:'',details:'',papers:[],keyword:''},courses:{code:'',title:'New course',terms:'',level:'',description:''},other:{year:'',title:'New item',context:'',role:''},outreach:{year:'',title:'New outreach activity',description:'',url:''},links:{label:'',url:''},profile_links:{label:'',url:''},publications:{title:'New publication',authors:[],year:new Date().getFullYear(),journal:'',volume:'',issue:'',pages:'',url:'',doi:''},papers:0};if(key==='highlights'){const area=data['content.json'].areas.find(a=>a.projects.length);return {area:area?.slug||'',project:area?.projects[0]?.slug||'',art:Object.keys(data['content.json'].backgrounds)[0]||''}}return structuredClone(defaults[key]??'')}
function field(parent,key,value,set,path){
 if(/^areas\.[^.]+\.(caption|tags|category)$/.test(path)||/^areas\.[^.]+\.projects\.\d+\.stage$/.test(path))return;
 if(hidden.has(key)||key==='slug'||key==='text'&&path.startsWith('publications'))return;
 if(key==='image'){const topicImage=/^areas\.[^.]+\.image$/.test(path);const label=topicImage?'主题页顶部图片':labels.image;parent.append(el('label',label));if(topicImage)parent.append(el('small','这张图片作为大主题标题和介绍下方的半透明背景。未选图时使用 Research 总览配图；背景仅在显示时裁切，原文件保留。具体项目的封面仍与文字并排。'));imageControl(parent,value||'',set,label);return}
 if(Array.isArray(value)){
  const group=disclosure((labels[key]||key)+' · '+value.length,path,['people','courses','other','projects'].includes(key));
  value.forEach((v,i)=>{const row=el('div',undefined,'array-item');
   if(['projects','highlights'].includes(key))row.append(orderControls(value,i,path,itemLabel(key,v)));
   if(v!==null&&typeof v==='object'){const detail=disclosure((key==='publications'?`#${i} · `:'')+itemLabel(key,v),path+'.'+i);object(detail,v,path+'.'+i);row.append(detail)}else field(row,String(i+1),v,x=>value[i]=x,path+'.'+i);
   if(key!=='publications')row.append(button('移除',async()=>{if(await confirmAction('移除这一项？保存前可刷新编辑器放弃修改。')){value.splice(i,1);change();render()}},'delete'));group.append(row)
  });
  group.append(button(key==='publications'?'新增论文':'新增一项',()=>{let v=value.length?structuredClone(value[value.length-1]):emptyItem(key);if(v&&typeof v==='object'){if('name'in v)v.name='New member';if('title'in v)v.title='New '+(key==='publications'?'publication':'item');if('slug'in v)v.slug='project-'+Date.now()}else v=key==='papers'||typeof v==='number'?0:'';value.push(v);change();openDetails.set(path+'.'+(value.length-1),true);render()}));parent.append(group);return;
 }
 if(value!==null&&typeof value==='object'){const g=disclosure(labels[key]||key,path);object(g,value,path);parent.append(g);return}
 let input;if(key==='art'){input=el('select');for(const v of Object.keys(data['content.json'].backgrounds)){const opt=el('option',v);opt.value=v;input.append(opt)}input.value=value||''}else{input=el(typeof value==='number'?'input':typeof value==='string'&&(value.length>95||['summary','bio','text','biography','details','description'].includes(key))?'textarea':'input');input.value=value??'';if(typeof value==='number')input.type='number'}
 labeled(parent,labels[key]||key,input);input.oninput=()=>{set(typeof value==='number'?Number(input.value):input.value);change()};
}
function object(parent,o,path){const isProject='slug'in o&&'papers'in o;for(const [k,v]of Object.entries(o)){if(isProject&&['cover','figures'].includes(k))continue;field(parent,k,v,x=>o[k]=x,path+'.'+k)}if(isProject){parent.append(el('small','项目 ID：'+o.slug,'id-hint'));projectMedia(parent,o)}}
function render(remember=true){if(remember)rememberDetails();form.replaceChildren(el('h2',tabs[tab]));document.querySelectorAll('nav button').forEach((b,i)=>{b.classList.toggle('active',i===tab);b.setAttribute('aria-current',i===tab?'page':'false')});const c=data['content.json'];
 if(tab===0){form.append(el('small','展开「首页项目卡片」，使用「上移 / 下移」调整 Research highlights 的顺序。卡片优先使用项目封面。'));object(form,c.homepage,'home')}
 if(tab===1){field(form,'PI',c.principal_investigator,()=>{},'pi');field(form,'people',c.people,()=>{},'people');form.append(el('small','新增成员会复制最后一位的字段，请修改姓名、身份和介绍。'))}
 if(tab===2){form.append(el('small','用「上移 / 下移」调整主题顺序；展开主题后可调整具体项目顺序。保存后更新网站，首页 Research highlights 卡片在「首页 → 首页项目卡片」中单独排序。'));c.areas.forEach((a,i)=>{const row=el('div',undefined,'topic-item');row.append(orderControls(c.areas,i,'areas',a.title,false));const det=disclosure(a.title,'areas.'+a.slug);det.append(el('small','主题 ID：'+a.slug,'id-hint'));object(det,a,'areas.'+a.slug);row.append(det);form.append(row)})}
 if(tab===3){form.append(el('small','列表顺序是论文的固定编号（从 0 开始），网站显示时自动按年份排序。'));field(form,'publications',data['publications-source.json'],()=>{},'publications')}
 if(tab===4){field(form,'courses',data['teaching.json'].courses,()=>{},'courses');field(form,'other',data['teaching.json'].other,()=>{},'other');field(form,'outreach',data['teaching.json'].outreach??=[],()=>{},'outreach')}
 if(tab===5){form.append(el('small','统一管理网站图片和 MP4 视频。可批量上传、搜索和查看使用位置，再到 Research 或 Team 中选用。使用位置包含当前未保存的表单修改。原文件不会因移除引用或撤销而删除。'));libraryView(form)}
}
document.querySelector('#close-media').onclick=()=>{if(!busy)dialog.close()};dialog.addEventListener('cancel',e=>{if(busy)e.preventDefault()});
document.querySelector('#save').onclick=()=>action(async()=>{status.dataset.state='saving';status.textContent='正在保存并生成最新预览…';const r=await(await api('save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})).json();dirty=false;status.dataset.state='saved';document.querySelector('.preview').href='/?_preview='+Date.now();status.textContent='已保存（'+new Date().toLocaleTimeString()+'）。打开的本地预览会自动刷新；ZIP 需要重新导出。备份：'+r.backup});
document.querySelector('#undo').onclick=()=>action(async()=>{if(!await confirmAction('恢复上一次保存前的内容？当前未保存的修改会被放弃。上传的原图会保留。'))return;const r=await(await api('undo',{method:'POST',body:'{}'})).json();data=await(await api('data')).json();dirty=false;render();status.textContent=r.message});
document.querySelector('#export').onclick=()=>action(async()=>{if(dirty)throw Error('请先保存修改，再导出');const b=await(await api('export')).blob();const a=el('a');a.href=URL.createObjectURL(b);a.download='TAPAS-local-edited.zip';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);status.dataset.state='saved';status.textContent='已导出当前已保存版本与图片原文件。后续编辑不会更新已下载的 ZIP，请在保存后重新导出。'});
window.addEventListener('beforeunload',e=>{if(dirty||busy){e.preventDefault();e.returnValue=''}});
// Do not let an accidental file drop navigate away from unsaved edits.
for(const event of ['dragover','drop'])window.addEventListener(event,e=>{if(Array.from(e.dataTransfer?.types||[]).includes('Files'))e.preventDefault()});
document.querySelector('.preview').addEventListener('click',event=>{if(dirty){event.preventDefault();status.dataset.state='dirty';status.textContent='这些修改还未保存。请先点击「保存并更新预览」，再打开网站预览。'}else event.currentTarget.href='/?_preview='+Date.now()});
for(let i=0;i<tabs.length;i++)document.querySelector('#nav').append(button(tabs[i],()=>{tab=i;render()}));
(async()=>{try{[data,images]=await Promise.all([api('data').then(r=>r.json()),api('images').then(r=>r.json())]);render();status.textContent='仅在你的电脑上编辑。保存不会发布到互联网。'}catch(e){status.textContent=e.message}})();
