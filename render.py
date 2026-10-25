"""Generate the static research-group website from editable content records."""
from pathlib import Path
from html import escape
from xml.sax.saxutils import escape as xml_escape
import json
import re
import hashlib
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'dist'
SITE_URL = 'https://munizhou.github.io'
data = json.loads((ROOT / 'content.json').read_text())
paper_records = json.loads((ROOT / 'publications-source.json').read_text())
# Keep the established published-paper indices stable for project references.
papers = [p for p in paper_records if p.get('status') != 'submitted'] + [p for p in paper_records if p.get('status') == 'submitted']
areas = data['areas']
RESEARCH_HOME = '/research/'
teaching_data = json.loads((ROOT / 'teaching.json').read_text())
# A single revision identifies a completed build across every local preview tab.
# It changes for content, layout, or asset changes, but not for an identical save.
preview_inputs = [json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
                  for value in (data, papers, teaching_data)]
preview_inputs += [path.read_bytes() for path in (ROOT/'render.py', OUT/'assets/site.css', OUT/'assets/site.js')]
PREVIEW_VERSION = hashlib.sha256(b'\0'.join(preview_inputs)).hexdigest()[:24]
SCHOLAR = 'https://scholar.google.com/citations?hl=en&oi=ao&user=swzwbYMAAAAJ'
e = escape

PERSON_ID = f'{SITE_URL}/#muni-zhou'
WEBSITE_ID = f'{SITE_URL}/#website'

def canonical_url(path):
    return f'{SITE_URL}/{path.strip("/")}/' if path.strip('/') else f'{SITE_URL}/'

def structured_data(path):
    if path not in ('', 'team/muni-zhou'):
        return ''
    person = {
        '@type': 'Person',
        '@id': PERSON_ID,
        'name': 'Muni Zhou',
        'alternateName': ['周慕霓', '慕尼周'],
        'url': f'{SITE_URL}/',
        'image': f'{SITE_URL}/assets/portrait.jpg',
        'jobTitle': 'Assistant Professor of Physics and Astronomy',
        'affiliation': {
            '@type': 'CollegeOrUniversity',
            'name': 'Dartmouth College',
            'url': 'https://home.dartmouth.edu/'
        },
        'sameAs': [
            SCHOLAR,
            'https://orcid.org/0000-0003-0709-7848',
            'https://physics.dartmouth.edu/people/muni-zhou'
        ]
    }
    graph = [person]
    if path == '':
        graph.insert(0, {
            '@type': 'WebSite',
            '@id': WEBSITE_ID,
            'url': f'{SITE_URL}/',
            'name': 'TAPAS Group',
            'alternateName': ['TAPAS', 'Muni Zhou Research Group'],
            'publisher': {'@id': PERSON_ID}
        })
        graph.insert(0, {
            '@type': 'ProfilePage',
            '@id': f'{SITE_URL}/#profile-page',
            'url': f'{SITE_URL}/',
            'name': 'Muni Zhou | TAPAS Group',
            'mainEntity': {'@id': PERSON_ID},
            'isPartOf': {'@id': WEBSITE_ID}
        })
    else:
        graph.insert(0, {
            '@type': 'ProfilePage',
            '@id': f'{canonical_url(path)}#profile-page',
            'url': canonical_url(path),
            'name': 'Muni Zhou',
            'mainEntity': {'@id': PERSON_ID}
        })
    payload = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return f'<script type="application/ld+json">{payload}</script>'

def link(url, text, css='text-link'):
    return f'<a class="{css}" href="{e(url, quote=True)}">{text}<span aria-hidden="true">↗</span></a>'

def area_link(area, text='Explore this research area'):
    return f'<a class="text-link" href="/research/{area["slug"]}/">{text}<span aria-hidden="true">↗</span></a>'

def nav(active):
    items = [('Home', '/'), ('Research', RESEARCH_HOME), ('Team', '/team/'), ('Publications', '/publications/'), ('Teaching', '/teaching/')]
    links = ''.join(f'<a href="{url}"'+(' aria-current="page"' if name == active else '')+f'>{name}</a>' for name,url in items)
    return f'''<a class="skip" href="#main">Skip to content</a>
    <header class="site-header"><div class="wrap header-inner">
    <a class="brand" href="/" aria-label="TAPAS Group home"><span class="brand-mark" aria-hidden="true">T</span><span><span class="brand-title">TAPAS Group</span><span class="brand-sub">Dartmouth College</span></span></a>
    <button class="menu-toggle" aria-expanded="false" aria-controls="main-nav">Menu</button>
    <nav class="nav" id="main-nav" aria-label="Main navigation">{links}</nav></div></header>'''

def page(path, title, active, body, description):
    dest = OUT / path / 'index.html'
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = body.replace('href="/research/"', f'href="{RESEARCH_HOME}"')
    sidebar = ''
    if active == 'Research':
        theme_items = ''.join(f'<a href="/research/{e(area["slug"],quote=True)}/"'+(' aria-current="page"' if path == 'research/'+area['slug'] else '')+f'>{e(area.get("short") or area["title"])}</a>' for area in areas)
        overview_current = ' aria-current="page"' if path == 'research' else ''
        sidebar = f'<aside class="research-sidebar"><nav aria-label="Research themes"><h2><a class="research-sidebar-home" href="{RESEARCH_HOME}"{overview_current}>Research themes</a></h2>{theme_items}</nav></aside>'
    canonical = canonical_url(path)
    schema = structured_data(path)
    dest.write_text(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · TAPAS Group</title><meta name="description" content="{e(description, quote=True)}"><link rel="canonical" href="{e(canonical, quote=True)}"><meta name="theme-color" content="#006448"><meta name="tapas-preview-revision" content="{PREVIEW_VERSION}"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/site.css?v={PREVIEW_VERSION}"><script src="/assets/site.js?v={PREVIEW_VERSION}" defer></script>{schema}</head>
<body>{nav(active)}<div class="wrap site-layout{' research-shell' if sidebar else ''}">{sidebar}<main id="main" class="site-content">{body}</main></div></body></html>''')

def pub(index, show_year=True):
    p = papers[index]
    title = p['title'].strip()
    authors = ', '.join(p['authors'])
    volume = p.get('volume','')
    if p.get('issue'):volume += '('+p['issue']+')'
    journal_details = ', '.join(x for x in [volume,p.get('pages','')] if x)
    metadata = e(p['journal']) + (', '+e(journal_details) if journal_details else '') + f" ({p['year']})."
    year_html = f'<div class="pub-year">{p["year"]}</div>' if show_year else ''
    css = 'publication' if show_year else 'publication no-year'
    if p.get('url'):
        title_html = f'<a href="{e(p["url"],quote=True)}" target="_blank" rel="noopener noreferrer">{e(title)}</a>'
        arrow = f'<a class="arrow" href="{e(p["url"],quote=True)}" target="_blank" rel="noopener noreferrer" aria-label="Read {e(title,quote=True)} in a new tab">↗</a>'
    else:
        title_html = e(title)
        arrow = '<span class="arrow" aria-hidden="true"></span>'
    return f'<article class="{css}" data-paper-index="{index}">{year_html}<div><h3>{title_html}</h3><p class="pub-authors">{e(authors)}</p><p class="pub-venue">{metadata}</p></div>{arrow}</article>'

def keyword_links(area, css='project-keywords'):
    return '<div class="'+css+'">'+''.join('<a href="/research/'+area['slug']+'/#'+x['slug']+'">'+e(x['keyword'])+'</a>' for x in area['projects'])+'</div>'

def tags(project):
    return '<div class="tags">'+''.join(f'<span class="tag">{e(t)}</span>' for t in project['tags'])+'</div>'

def visual(project, cls='project-visual'):
    if project.get('image'):
        return f'<figure class="{cls}"><img src="{asset_url(project["image"])}" alt="{e(project.get("alt",""),quote=True)}" loading="lazy"></figure>'
    return f'<div class="{cls} project-text-only"><span>{e(project["category"])}</span><strong>{project_prose(project["question"])}</strong></div>'

def asset_url(name):
    return '/assets/'+quote(name,safe='')

def cover_image(project,controls=False):
    cover=project.get('cover') or {}
    if not cover.get('image'):return ''
    fit='cover' if cover.get('fit')=='cover' else 'contain'
    position=cover.get('position') or {}
    x=max(0,min(100,float(position.get('x',50))))
    y=max(0,min(100,float(position.get('y',50))))
    if Path(cover['image']).suffix.lower()=='.mp4':
        playback='controls' if controls else 'autoplay data-cover-loop'
        return f'<video class="project-cover-image" src="{asset_url(cover["image"])}" aria-label="{e(cover.get("alt") or project["title"],quote=True)}" {playback} muted loop playsinline preload="metadata" style="object-fit:{fit};object-position:{x:g}% {y:g}%"></video>'
    return f'<img class="project-cover-image" src="{asset_url(cover["image"])}" alt="{e(cover.get("alt") or project["title"],quote=True)}" loading="lazy" decoding="async" style="object-fit:{fit};object-position:{x:g}% {y:g}%">'

def science_figure(figure,cls='project-figure'):
    url=asset_url(figure['image'])
    caption=f'<figcaption>{e(figure["caption"])}</figcaption>' if figure.get('caption') else ''
    if Path(figure['image']).suffix.lower()=='.mp4':
        return f'<figure class="{cls}"><video src="{url}" controls playsinline preload="metadata" aria-label="{e(figure.get("alt") or figure.get("caption") or "Research video",quote=True)}"></video>{caption}</figure>'
    return f'<figure class="{cls}"><a class="figure-original" href="{url}" target="_blank" rel="noopener" aria-label="Open original image"><img src="{url}" alt="{e(figure.get("alt",""),quote=True)}" loading="lazy" decoding="async"></a>{caption}</figure>'

def background_art(kind):
    art = data['backgrounds'][kind]
    x, y, side = art['crop']
    styles = f'width:{100 * art["source_width"] / side:.6f}%;left:{-100 * x / side:.6f}%;top:{-100 * y / side:.6f}%;'
    return f'<div class="science-art" aria-hidden="true"><div class="science-crop"><img src="/assets/{e(art["image"], quote=True)}" alt="" loading="lazy" decoding="async" style="{styles}"></div></div>'

def intro(label,title,text,css=""):
    return f'<div class="page-heading {css}">{background_art(data["page_backgrounds"][label])}<div class="wrap"><div class="page-intro"><h1>{title}</h1><p>{text}</p></div></div></div>'

profile_links = ''.join(link(item['url'], e(item['label'])) for item in data['homepage']['profile_links'])

def highlight_card(item):
    area = next(a for a in areas if a['slug'] == item['area'])
    project = next(p for p in area['projects'] if p['slug'] == item['project'])
    url = f'/research/{area["slug"]}/#{project["slug"]}'
    highlight_project = project
    if project.get('highlight_cover'):
        highlight_project = {**project, 'cover': project['highlight_cover']}
    artwork=cover_image(highlight_project) or background_art(item['art'])
    credit = highlight_project.get('cover', {}).get('credit_short', '')
    credit_html = f'<span class="highlight-image-credit">{e(credit)}</span>' if credit else ''
    highlight_title=project.get('highlight_title') or project['title']
    return f'''<a class="highlight-card" href="{url}"><div class="highlight-image">{artwork}{credit_html}</div><div class="highlight-copy"><h3>{e(highlight_title)}</h3></div></a>'''

highlights = ''.join(highlight_card(item) for item in data['homepage']['highlights'])

opportunity_items = ''.join(f'<li><a href="{e(item.get("details_url") or item["url"], quote=True)}">{e(item["title"])}</a>: {e(item["description"])} <a href="{e(item["url"], quote=True)}">Apply</a></li>' for item in data['homepage'].get('opportunities', []))
opportunities = f'<section class="join-opportunities" aria-labelledby="opportunities-title"><h3 id="opportunities-title">Some job opportunities:</h3><ul>{opportunity_items}</ul></section>' if opportunity_items else ''


international_opportunities = """<section class="international-opportunities" aria-labelledby="international-title"><h3 id="international-title">International</h3><ul>
<li><a href="https://schmidtsciencefellows.org/selection/">Schmidt Science Fellows</a>: supports recent PhD graduates making an interdisciplinary shift, such as bringing mathematics or computing expertise into plasma physics.</li>
<li><a href="https://marie-sklodowska-curie-actions.ec.europa.eu/actions/postdoctoral-fellowships">Marie Skłodowska-Curie Global Postdoctoral Fellowships</a>: for researchers in Europe to spend one to two years outside Europe (for example, at Dartmouth), followed by a year back in Europe.</li>
</ul></section>"""

home_bio = data['homepage']['bio']
if isinstance(home_bio, str):
    home_bio = [home_bio]
home_bio_html = ''.join(f'<p class="home-bio">{e(paragraph)}</p>' for paragraph in home_bio)

home = f''' 
<section class="home-masthead">{background_art("density")}<div class="wrap home-masthead-grid"><h1 class="home-group-name">TAPAS</h1><p class="home-group-meaning">Turbulence And Plasmas<br><em>Across Scales</em></p></div></section>
<section class="home-intro"><div class="wrap home-intro-grid"><img class="home-portrait" src="/assets/portrait.jpg" alt="Muni Zhou" loading="lazy"><div><h2 class="home-name">Muni Zhou<span class="home-chinese-name">周慕霓</span></h2><p class="home-role">{e(data["homepage"]["intro_role"])}</p>{home_bio_html}<div class="actions home-profile-links">{profile_links}</div></div></div></section>
<section class="home-research">{background_art("flow")}<div class="wrap"><div class="home-science-intro"><h2>{e(data["homepage"]["science_title"])}</h2><p class="home-research-description">Using theory and numerical simulations, we study how plasmas generate magnetic fields and transfer energy across scales. We ask how <a href="/research/magnetogenesis/">cosmic magnetic fields originate and grow</a>, how <a href="/research/kinetic-turbulence/">turbulence heats the solar wind</a>, and how <a href="/research/reconnection/">magnetic reconnection reshapes turbulent plasmas</a>. We also explore how <a href="/research/radiative-turbulence/">radiation interacts with relativistic turbulence</a> and what controls <a href="/research/fusion/">energetic-particle transport in fusion plasmas</a>.</p><div class="actions"><a class="text-link" href="/research/">Explore our research <span aria-hidden="true">↗</span></a><a class="text-link" href="/team/">Meet our team <span aria-hidden="true">→</span></a></div></div></div></section>
<section class="section home-highlights" id="research-highlights"><div class="wrap"><div class="section-head"><h2>Research highlights</h2><a class="text-link" href="/research/">All research <span aria-hidden="true">↗</span></a></div><div class="highlights-grid">{highlights}</div></div></section>
<section class="section band home-join" id="join-us"><div class="wrap"><h2>Interested in joining us?</h2><p>We welcome prospective graduate students and postdoctoral researchers interested in plasma astrophysics, fusion, and basic plasma physics. Contact Muni Zhou: <a class="text-link" href="mailto:muni.zhou@dartmouth.edu">muni.zhou@dartmouth.edu</a></p>{opportunities}{international_opportunities}</div></section>
'''
page('', 'Plasma turbulence at Dartmouth', 'Home', home, 'TAPAS — Turbulence And Plasmas Across Scales. Muni Zhou’s group at Dartmouth studies plasma turbulence, cosmic magnetism, reconnection, and particle energization.')

def research_overview_card(area):
    image = {'image': area['overview_image']} if area.get('overview_image') else (area if area.get('image') else area.get('overview_visual', {}))
    artwork = f'<img src="{asset_url(image["image"])}" alt="{e(area.get("alt", ""), quote=True)}" loading="lazy" decoding="async">' if image.get('image') else ''
    projects = ''.join(f'<span>{e(project["keyword"])}</span>' for project in area['projects'])
    url = f'/research/{area["slug"]}/'
    return f'''<a class="research-overview-card research-overview-{e(area['slug'], quote=True)}" href="{url}" aria-label="Explore {e(area['title'], quote=True)}"><span class="research-overview-art">{artwork}</span><span class="research-overview-copy"><span class="research-overview-title">{e(area['title'])}</span><span class="research-overview-question">{e(area['question'])}</span><span class="research-overview-projects"><strong>Projects</strong>{projects}</span><span class="research-overview-arrow" aria-hidden="true">↗</span></span></a>'''

research_overview = f'''<section class="research-overview" aria-label="Research themes overview"><div class="research-overview-grid">{''.join(research_overview_card(area) for area in areas)}</div></section>'''
page('research', 'Research', 'Research', research_overview, 'Explore the TAPAS Group’s research themes in plasma physics, turbulence, magnetic fields, reconnection, radiation, and fusion.')

def person_anchor(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

# Link names in project prose while keeping all other content escaped.
project_member_names = {}
for member in [data['principal_investigator'], *data['people']]:
    member_url = member.get('external_profile_url') or '/team/' + person_anchor(member['name']) + '/'
    for name in [member['name'], member.get('chinese_name', '')]:
        if name:
            project_member_names[name] = member_url
project_member_pattern = re.compile(r'(?<!\w)(' + '|'.join(re.escape(name) for name in sorted(project_member_names, key=len, reverse=True)) + r')(?!\w)')

def project_prose(text):
    parts = []
    end = 0
    for match in project_member_pattern.finditer(text):
        parts.append(e(text[end:match.start()]))
        parts.append(f'<a class="person-link" href="{project_member_names[match.group()]}">{e(match.group())}</a>')
        end = match.end()
    parts.append(e(text[end:]))
    return ''.join(parts)

def project_entry(project, index):
    lead = project.get('lead', {})
    lead_html = ''
    if lead.get('name'):
        lead_name = project_prose(lead['name'])
        if lead.get('url', '').startswith(('https://', 'http://')) or (lead.get('url', '').startswith('/') and not lead.get('url', '').startswith('//')):
            lead_name = f'<a class="person-link" href="{e(lead["url"], quote=True)}">{e(lead["name"])}</a>'
        lead_prefix = e(lead.get('prefix', ''))
        affiliation = f' at {e(lead["affiliation"])}' if lead.get('affiliation') else ''
        lead_html = f'<p class="project-question">Led by {lead_prefix}{lead_name}{affiliation}</p>'
    publications = ''
    if project['papers']:
        publications = '<div class="project-bibliography"><p class="bibliography-label">Related publications</p>'+''.join(pub(i,False) for i in project['papers'])+'</div>'
    manuscripts = project.get('manuscripts', [])
    if manuscripts:
        manuscript_items = ''.join(
            '<article class="publication no-year manuscript-in-progress"><div>'
            f'<h3>{e(item["title"])}</h3>'
            f'<p class="pub-authors">{e(", ".join(item.get("authors", [])))}</p>'
            f'<p class="pub-venue">{e(item.get("status", "In preparation"))}</p>'
            '</div></article>'
            for item in manuscripts
        )
        publications += '<div class="project-bibliography project-manuscripts"><p class="bibliography-label">Related manuscript in progress</p>'+manuscript_items+'</div>'
    presentations = project.get('presentations', [])
    if presentations:
        presentation_items = ''.join(
            '<article class="publication no-year related-presentation"><div>'
            f'<h3>{e(item["title"])}</h3>'
            f'<p class="pub-authors">{e(", ".join(item.get("authors", [])))}</p>'
            f'<p class="pub-venue">{e(item.get("venue", ""))}</p>'
            '</div></article>'
            for item in presentations
        )
        publications += '<div class="project-bibliography project-presentations"><p class="bibliography-label">Related presentation</p>'+presentation_items+'</div>'
    cover=cover_image(project,controls=True)
    if cover:
        url=asset_url(project['cover']['image'])
        cover_class='project-cover'+(' cover-contained' if project['cover'].get('fit','contain')=='contain' else '')
        caption=''
        if project['cover'].get('caption'):
            caption_text=e(project['cover']['caption'])
            caption_url=project['cover'].get('caption_url','')
            caption_text=f'<a href="{e(caption_url,quote=True)}" target="_blank" rel="noopener">{caption_text}</a>' if caption_url else caption_text
            caption=f'<figcaption>{caption_text}</figcaption>'
        if Path(project['cover']['image']).suffix.lower()=='.mp4':
            cover=f'<figure class="{cover_class}"><div class="project-cover-video">{cover}</div>{caption}</figure>'
        else:
            cover=f'<figure class="{cover_class}"><a href="{url}" target="_blank" rel="noopener" aria-label="Open original cover image">{cover}</a>{caption}</figure>'
    figures=''.join(science_figure(figure) for figure in project.get('figures',[]) if figure.get('image'))
    gallery=f'<div class="project-figures">{figures}</div>' if figures else ''
    question_html = f'<p class="project-question">{project_prose(project["question"])}</p>' if project.get('question') else ''
    summary_html = f'<p>{project_prose(project["summary"])}</p>' if project.get('summary') else ''
    detail_items = project.get('details', [])
    if isinstance(detail_items, str):
        detail_items = [detail_items] if detail_items else []
    details_html = ''.join(f'<p>{project_prose(item)}</p>' for item in detail_items)
    collaboration = project.get('collaboration', {})
    collaboration_html = ''
    if collaboration.get('name'):
        collaborator_name = e(collaboration['name'])
        if collaboration.get('url', '').startswith(('https://', 'http://')):
            collaborator_name = f'<a class="person-link" href="{e(collaboration["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{collaborator_name}</a>'
        collaboration_html = f'<p class="project-collaboration">In collaboration with {collaborator_name}.</p>'
    inline_references = publications if project.get('inline_references') else ''
    trailing_references = '' if project.get('inline_references') else publications
    return f'''<section class="research-project" id="{project['slug']}" aria-labelledby="{project['slug']}-title"><div class="project-writing"><h2 id="{project['slug']}-title">{e(project['title'])}</h2><div class="project-body{' has-cover' if cover else ''}"><div class="project-summary">{cover}{lead_html}{question_html}{summary_html}{details_html}{collaboration_html}{inline_references}</div></div>{gallery}{trailing_references}</div></section>'''

for p in areas:
    image = p if p.get('image') else p.get('overview_visual', {})
    figure = f'<div class="theme-banner-art" aria-hidden="true"><img src="{asset_url(image["image"])}" alt="" decoding="async"></div>' if image.get('image') else ''
    entries = ''.join(project_entry(x,i+1) for i,x in enumerate(p['projects']))
    paragraphs = p.get('body') or [p.get('summary', '')]
    topic_text = ''.join('<p>'+e(s)+'</p>' for s in paragraphs if s.strip())
    body = f'''<div class="wrap"><section class="theme-intro theme-banner theme-{e(p['slug'],quote=True)}{' with-image' if figure else ''}" aria-labelledby="theme-title"><div class="theme-writing"><h1 id="theme-title">{e(p['title'])}</h1><p class="theme-question">{e(p['question'])}</p>{topic_text}<nav class="theme-project-nav" aria-label="Projects in {e(p['title'],quote=True)}"><h2>Projects</h2>{keyword_links(p)}</nav></div>{figure}</section><div class="area-projects">{entries}</div></div>'''
    page('research/'+p['slug'],p['title'],'Research',body,p['summary'])

def person(p):
    parts = p['name'].split()
    initials = e(parts[0][0] + (parts[-1][0] if len(parts) > 1 else ''))
    name = e(p['name'])
    if p.get('url'):
        name = f'<a href="{e(p["url"], quote=True)}">{name}</a>'
    if p.get('chinese_name'):
        name += f' <span class="chinese">{e(p["chinese_name"])}</span>'
    portrait = f'<img src="/assets/{e(p["image"], quote=True)}" alt="{e(p["name"], quote=True)}" loading="lazy">' if p.get('image') else f'<span class="team-monogram" aria-hidden="true">{initials}</span>'
    photo_class = '' if p.get('image') else ' team-photo-initials'
    role = f'<p class="team-role">{e(p["role"])}</p>' if p.get('role') else ''
    position = f'<p class="team-position">{e(p["position"])}</p>' if p.get('position') else ''
    biography = f'<p class="team-biography">{e(p["biography"])}</p>' if p.get('biography') else ''
    background = ''
    if p.get('background'):
        entries = p['background'] if isinstance(p['background'], list) else [p['background']]
        background = '<div class="team-background"><h3>Education</h3><ul>'+''.join(f'<li>{e(entry)}</li>' for entry in entries)+'</ul></div>'
    email = p.get('email') or next((item['url'][7:].split('?')[0] for item in p.get('links', []) if item['url'].lower().startswith('mailto:')), '')
    links = ''.join(link(item['url'], e(item['label'])) for item in p.get('links', []) if not item['url'].lower().startswith('mailto:'))
    contacts = f'<div class="team-links">{links}</div>' if links else ''
    if email:
        contacts = f'<p class="member-email"><strong>Email:</strong> {e(email)}</p>' + contacts
    news_items = ''.join(f'<li><a href="{e(item["url"], quote=True)}">{e(item["title"])}</a></li>' for item in p.get('news', []))
    news = f'<div class="member-news"><h3>News</h3><ul>{news_items}</ul></div>' if news_items else ''
    is_muni_profile = p.get('name') == 'Muni Zhou'
    cv_sections = [
        section for section in p.get('profile_sections', [])
        if section.get('title') and section.get('items')
    ]
    def render_cv_sections(sections, extra_class=''):
        section_html = ''.join(
            '<section class="member-cv-section"><h2>'+e(section['title'])+'</h2><ul>'+
            ''.join('<li>'+e(item)+'</li>' for item in section.get('items', []))+
            '</ul></section>'
            for section in sections
        )
        class_name = 'member-cv-sections' + (f' {extra_class}' if extra_class else '')
        return f'<div class="{class_name}">{section_html}</div>' if section_html else ''

    profile_sections = render_cv_sections(cv_sections)
    profile = f'<a class="text-link" href="{e(p["url"],quote=True)}">Profile ↗</a>' if p.get('url') else ''
    display_name = e(p['name']) + (f' <span class="chinese">{e(p["chinese_name"])}</span>' if p.get('chinese_name') else '')
    slug = person_anchor(p['name'])
    external_profile_url = p.get('external_profile_url', '')
    bio_content = (f'<p>{e(p["text"])}</p>' if p.get('text') else '') + biography
    bio_section = f'<div class="member-profile-bio">{bio_content}</div>' if bio_content else ''
    if is_muni_profile:
        profile_intro_sections = render_cv_sections(cv_sections[:2], 'member-cv-intro')
        profile_remaining_sections = render_cv_sections(cv_sections[2:], 'member-cv-main')
        profile_body = f'''<article class="member-profile member-profile-cv"><a class="member-back" href="/team/#{slug}">← Team</a><div class="member-profile-layout"><div class="member-profile-copy"><h1>{display_name}</h1>{profile_intro_sections}</div><div class="member-profile-photo member-portrait{photo_class}">{portrait}</div></div>{profile_remaining_sections}</article>'''
    elif not external_profile_url:
        profile_body = f'''<article class="member-profile"><a class="member-back" href="/team/#{slug}">← Team</a><div class="member-profile-layout"><div class="member-profile-copy"><h1>{display_name}</h1>{role}{position}{bio_section}{background}{contacts}{news}{profile}</div><div class="member-profile-photo member-portrait{photo_class}">{portrait}</div></div>{profile_sections}</article>'''
    if not external_profile_url:
        page('team/'+slug, p['name'], 'Team', profile_body, p.get('text',''))
    card_url = external_profile_url or f'/team/{slug}/'
    return f'''<article class="member-card" id="{slug}"><a class="member-profile-link" href="{e(card_url, quote=True)}"><span class="member-portrait{photo_class}">{portrait}</span><span class="member-name">{display_name}</span><span class="member-role">{e(p.get('role',''))}</span></a></article>'''


# Match the reference's surname ordering, including the principal investigator.
team_members = sorted([data['principal_investigator'], *data['people']], key=lambda p: (p['name'].split()[-1].casefold(), p['name'].casefold()))
team = f'''<div class="team-directory"><header class="team-directory-heading"><h1>Team</h1></header><section aria-label="Team members"><div class="member-grid">{''.join(person(p) for p in team_members)}</div></section></div>'''
page('team','Team','Team',team,'Meet Muni Zhou and the TAPAS plasma physics research team at Dartmouth College.')

for old_route in ['collaborations','research/particle-transport']:
    dest=OUT/old_route/'index.html'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Research · TAPAS Group</title><meta http-equiv="refresh" content="0;url=/research/"><link rel="stylesheet" href="/assets/site.css"></head><body><main class="wrap section"><h1>Research</h1><p><a class="text-link" href="/research/">Explore research projects ↗</a></p></main></body></html>')

submitted_indices = [i for i, paper in enumerate(papers) if paper.get('status') == 'submitted']
published_indices = [i for i, paper in enumerate(papers) if paper.get('status') != 'submitted']
submitted_list = ''.join(pub(i,False) for i in sorted(submitted_indices, key=lambda i: papers[i]['year'], reverse=True))
publication_list = ''.join(pub(i,False) for i in sorted(published_indices, key=lambda i: papers[i]['year'], reverse=True))
publications_heading = '<div class="page-heading publications-heading"><div class="wrap"><div class="page-intro"><h1>Research in print.</h1></div></div></div>'
submitted_section = f'<section class="publication-section"><h2 class="publication-section-title">Submitted</h2><div class="publication-list">{submitted_list}</div></section>' if submitted_list else ''
published_section = f'<section class="publication-section"><h2 class="publication-section-title">Published</h2><div class="publication-list">{publication_list}</div></section>'
publications = publications_heading+f'<div class="wrap">{submitted_section}{published_section}</div>'
page('publications','Publications','Publications',publications,'Publications on magnetogenesis, plasma turbulence, reconnection, radiative relativistic plasmas, and fusion physics.')

def course_notes(course):
    topics = course.get('topics', [])
    if not topics: return ''
    items = ''.join(f'<li><a href="{e(t["url"],quote=True)}" target="_blank" rel="noopener">{e(t["title"])}</a></li>' for t in topics)
    return '<div class="course-notes"><h4>Course notes</h4><ol>'+items+'</ol></div>'

def course_entry(c):
    level = f' <span class="course-level">{e(c["level"])}</span>' if c.get('level') else ''
    code_note = f' <span class="course-code-note">{e(c["code_note"])}</span>' if c.get('code_note') else ''
    term = f'<p class="course-term">{e(c["terms"])}</p>' if c.get('terms', '').strip() else ''
    description = f'<p>{e(c["description"])}</p>' if c.get('description', '').strip() else ''
    return f'<article class="course"><div class="course-code">{e(c["code"])}{code_note}</div><div><h3>{e(c["title"])}{level}</h3>{term}{description}{course_notes(c)}</div></article>'

courses=''.join(course_entry(c) for c in teaching_data['courses'])
other=''.join(f'<article class="teaching-other"><div class="course-code">{e(c["year"])}</div><div><h3>{e(c["title"])}</h3><p>{e(c["context"])}</p><p class="course-term">{e(c["role"])}</p></div></article>' for c in teaching_data['other'])

def outreach_entry(c):
    images = ''.join(f'<img src="/assets/{e(image["image"], quote=True)}" alt="{e(image.get("alt", ""), quote=True)}" loading="lazy" decoding="async">' for image in c.get('images', []))
    gallery = f'<div class="outreach-gallery">{images}</div>' if images else ''
    return f'<article class="outreach-feature"><h3><a href="{e(c["url"], quote=True)}">{e(c["title"])}</a></h3><p>{e(c["description"])}</p>{gallery}</article>'

outreach=''.join(outreach_entry(c) for c in teaching_data.get('outreach', []))
outreach_section=f'<section class="teaching-section"><div class="section-head"><h2>Outreach</h2></div>{outreach}</section>' if outreach else ''
teaching=f'<div class="wrap teaching-content"><section class="teaching-section"><div class="section-head"><h2>Dartmouth College Courses</h2></div>{courses}</section><section class="teaching-section other-teaching-section"><div class="section-head"><h2>Summer School Teaching</h2></div><div class="other-teaching-grid">{other}</div></section>{outreach_section}</div>'
page('teaching','Teaching','Teaching',teaching,'Courses and lectures taught by Muni Zhou at Dartmouth College, PPPL, Swarthmore College, and MIT.')

(OUT/'404.html').write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Page not found · TAPAS Group</title><meta name="robots" content="noindex"><link rel="stylesheet" href="/assets/site.css"></head><body>'''+nav('')+'<main id="main" class="wrap section"><div class="eyebrow">404</div><h1>Page not found.</h1><p>The page may have moved. Explore our research or return to the home page.</p><div class="actions"><a class="button" href="/">Home</a><a class="text-link" href="/research/">Research ↗</a></div></main>'+'<script src="/assets/site.js" defer></script></body></html>')

# Publish a simple inventory of canonical pages for search engines. Redirect-only
# routes are intentionally omitted so that their destination remains authoritative.
redirect_routes = {'collaborations', 'research/particle-transport'}
sitemap_urls = []
for index_file in sorted(OUT.rglob('index.html')):
    relative = index_file.parent.relative_to(OUT).as_posix()
    if relative == '.':
        relative = ''
    if relative in redirect_routes:
        continue
    sitemap_urls.append(canonical_url(relative))
sitemap_entries = ''.join(f'<url><loc>{xml_escape(url)}</loc></url>' for url in sitemap_urls)
(OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+sitemap_entries+'</urlset>\n')
(OUT/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n')
# Publish the revision last, so previews never refresh into an unfinished build.
revision_file = OUT/'assets/preview-version.json'
pending_revision = revision_file.with_name('.preview-version.tmp')
pending_revision.write_text(json.dumps({'format':'tapas-local-preview-v1','revision':PREVIEW_VERSION})+'\n')
pending_revision.replace(revision_file)
print(f'Generated {len(list(OUT.rglob("index.html")))} pages and a 404 page.')
