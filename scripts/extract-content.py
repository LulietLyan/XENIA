#!/usr/bin/env python3
"""Build XENIA's static article data from the supplied, unmodified DOCX files.

Uses Python's standard library plus Pillow. Run from the project root:
    python3 scripts/extract-content.py

Only visible document content is exported. Document properties, revision history,
Word compatibility fallbacks, and executable attachments are never published.
"""
from __future__ import annotations

import html
import json
import math
import posixpath
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'v': 'urn:schemas-microsoft-com:vml',
}


def q(prefix, name):
    return '{' + NS[prefix] + '}' + name


ARTICLES = [
    dict(pattern='办公室*', slug='oh-my-boss', title='《Oh my boss》：双人合作闯关音游', shortTitle='Oh my boss', category='项目实践', summary='PC 双人合作音游，使用 Unity 开发。2025 年腾讯 IE 校招生培训项目 Minigame 第二名。', coverImage='image5.png', coverCrop=(1287, 353, 1688, 598), tags=['Unity', '双人合作', '节奏闯关'], year='2025'),
    dict(pattern='洞察燕云*', slug='where-winds-meet', title='《燕云十六声》开放世界分析', shortTitle='燕云十六声：开放世界分析', category='玩法研究', summary='分析内容密度、场景叙事、探索自由度与地图引导，讨论玩家持续游玩的原因。', coverImage='image3.png', coverCrop=(2717, 1348, 3223, 1670), tags=['开放世界', '玩家体验', '探索设计']),
    dict(pattern='《只狼》*', slug='sekiro', title='《只狼》：苇名弦一郎关卡分析', shortTitle='只狼：苇名弦一郎关卡分析', category='玩法研究', summary='分析苇名城的地形、敌人配置和弦一郎战斗设计，讨论沉浸感与代入感。', coverImage='image22.png', coverCrop=(15, 6, 1418, 617), tags=['关卡设计', '战斗节奏', '心流体验']),
    dict(pattern='《王国之泪》*', slug='tears-of-the-kingdom', title='《王国之泪》四种能力分析', shortTitle='王国之泪：四种能力分析', category='玩法研究', summary='分析究极手、余料建造、通天术、倒转乾坤，以及它们在战斗、关卡和探索中的应用。', coverImage='image13.png', coverCrop=(15, 13, 950, 443), tags=['系统设计', '涌现玩法', '开放世界']),
    dict(pattern='从用户心理*', slug='justice-mobile', title='《逆水寒》手游外观商业化分析', shortTitle='逆水寒手游：外观商业化分析', category='商业化洞察', summary='按用户需求拆解外观付费，分析展示场景、奖励机制与社区内容对消费意愿的影响。', coverImage='image37.png', tags=['用户心理', '外观商业化', 'MMORPG']),
    dict(pattern='金铲铲*', slug='golden-spatula', title='《金铲铲之战》商业化设计拆解', shortTitle='金铲铲之战：商业化设计', category='商业化洞察', summary='梳理小小英雄、棋盘的价值分层与获取方式，分析付费路径，并提出面向中等付费玩家的设计方案。', coverImage='image31.png', tags=['用户分层', '付费系统', '商业化设计']),
    dict(pattern='《七界*', slug='seven-realms', title='《七界梦谭》二测社区监测', shortTitle='七界梦谭：二测社区监测', category='社区研究', summary='整理二测前后的多平台声量、情感分布和玩家反馈，分析社区口碑与运营沟通。', coverImage='image24.png', coverCrop=(45, 145, 868, 672), tags=['社区监测', '舆情分析', '发行观察'], year='2026'),
    dict(pattern='个人游戏*', slug='gaming-journey', title='个人游戏经历', shortTitle='游戏经历与社区创作', category='关于我', summary='十年游戏经历，主要游玩开放世界、MMORPG 和内容向游戏。记录游戏战绩、体验与社区创作。', coverImage='image17.png', coverCrop=(350, 100, 1380, 860), tags=['游戏经历', '社区创作', '玩家视角']),
]

# Payment receipts are unrelated to the public portfolio. Keep the source
# documents intact, but never export these screenshots or leave stale copies.
EXCLUDED_MEDIA = {'gaming-journey': {'image21.png', 'image23.png', 'image26.png'}}

# These are crops of supplied project screenshots, never generated artwork.
GALLERY_CROPS = {
    'oh-my-boss': [
        ('image5.png', (1287, 353, 1688, 598), '面对 BOSS：游戏剧情画面'),
        ('image4.png', (530, 297, 946, 578), '美术组：节拍与色块关卡'),
        ('image4.png', (986, 287, 1340, 998), '策划组：双人合作机关与办公室关卡'),
    ],
}

SLIDES = {
    'oh-my-boss': [
        ('产品简介', '一款面向 PC 的 Unity 双人 2D 音游，以合作、节奏、闯关和竞速为核心体验。玩家作为实习生进入一家发生异变的游戏公司，在不同部门轮岗闯关，最终面对办公室中的 BOSS。'),
        ('设计思路', '两名玩家需要在限定时间内合作闯过不同主题、不同难度的关卡。移动、攻击、拾取和使用道具、控制机关，都需要跟随音乐节奏。玩法结合节奏战斗、分工协作与办公室幻想。'),
        ('核心体验与成长路径', '玩家从熟悉基础操作与节拍开始，逐步完成双人合作首通，最后通过竞速和反复练习挑战更优路线。美术组、运营组、策划组对应不同主题关卡。'),
        ('关卡设计', '设计板展示关卡布局、路线与机关组合，记录双人协作和节拍操作如何落实到具体空间。'),
        ('BOSS 战设计', '设计板通过阶段划分梳理 BOSS 战的机制组合与体验递进，让玩家在最终关卡运用此前习得的操作。'),
    ],
    'where-winds-meet': [
        ('为什么让玩家「上头」', '从内容量、沉浸感、自由度和探索欲四个角度，梳理《燕云十六声》的开放世界体验。'),
        ('内容量：量大管饱，密度合理', '观察开放世界中的内容分布与密度，以及不同内容如何支撑持续游玩。'),
        ('沉浸感：历史与江湖氛围', '从历史背景、环境与世界表现出发，讨论玩家对江湖世界的代入感。'),
        ('沉浸感：场景与故事细节', '结合具体场景与故事细节，继续分析世界观如何转化为可感知的游玩体验。'),
        ('自由度：多路径达成目标', '以多种路径和解法为切入点，观察开放式探索如何给玩家保留选择空间。'),
        ('探索欲：好奇心与引导机制', '梳理环境线索与引导方式，分析游戏如何唤起好奇心并鼓励玩家继续探索。'),
    ],
}


def clean_tree(element):
    """Word stores a second copy of shapes for older viewers; choose once."""
    for child in list(element):
        if child.tag == q('mc', 'AlternateContent'):
            selected = child.find('mc:Choice', NS)
            if selected is None:
                selected = child.find('mc:Fallback', NS)
            index = list(element).index(child)
            element.remove(child)
            if selected is not None:
                for sub in list(selected):
                    element.insert(index, sub)
                    index += 1
                    clean_tree(sub)
        elif child.tag == q('w', 'del'):
            element.remove(child)
        else:
            clean_tree(child)


def safe_url(value):
    try:
        parts = urlsplit(value)
        return parts.scheme in ('https', 'http') and bool(parts.netloc) and not parts.username
    except ValueError:
        return False


class Exporter:
    def __init__(self, source, meta):
        self.source, self.meta = source, meta
        self.zip = ZipFile(source)
        self.doc = ET.fromstring(self.zip.read('word/document.xml'))
        clean_tree(self.doc)
        self.rels = {r.attrib['Id']: r.attrib for r in ET.fromstring(self.zip.read('word/_rels/document.xml.rels'))}
        self.styles = {}
        for style in ET.fromstring(self.zip.read('word/styles.xml')):
            name = style.find('w:name', NS)
            if name is not None:
                self.styles[style.get(q('w', 'styleId'))] = name.get(q('w', 'val'), '')
        self.image_map, self.images, self.links = {}, [], set()
        self.image_count = 0
        self.headings = []
        self.seen_title = False
        self.current_heading = meta['shortTitle']
        self.media_dir = ROOT / 'public' / 'media' / meta['slug']
        self.media_dir.mkdir(parents=True, exist_ok=True)
        for excluded in EXCLUDED_MEDIA.get(meta['slug'], set()):
            for suffix in ('.webp', '.gif', Path(excluded).suffix):
                (self.media_dir / (Path(excluded).stem + suffix)).unlink(missing_ok=True)

    def media(self, target):
        target = posixpath.normpath(posixpath.join('word', target))
        if target in self.image_map:
            return self.image_map[target]
        raw = self.zip.read(target)
        im = Image.open(BytesIO(raw))
        stem = Path(target).stem
        width, height = im.size
        if getattr(im, 'is_animated', False):
            filename = stem + '.gif'
            (self.media_dir / filename).write_bytes(raw)
        else:
            filename = stem + '.webp'
            im = ImageOps.exif_transpose(im)
            im.convert('RGBA' if 'A' in im.getbands() else 'RGB').save(self.media_dir / filename, 'WEBP', quality=92, method=6)
        relative = f'media/{self.meta["slug"]}/{filename}'
        self.image_map[target] = (relative, width, height)
        if relative not in self.images:
            self.images.append(relative)
        return relative, width, height

    def anchor(self, url, text):
        if not safe_url(url):
            return text
        # This is an ephemeral development preview, not a durable public source.
        if urlsplit(url).netloc.endswith('.myide.io'):
            return '交叉分析看板（原稿临时链接）'
        self.links.add(url)
        return f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{text}</a>'

    def run(self, run):
        parts = []
        for node in run:
            if node.tag == q('w', 't'):
                parts.append(html.escape(node.text or ''))
            elif node.tag in (q('w', 'br'), q('w', 'cr')):
                parts.append('<br>')
            elif node.tag == q('w', 'tab'):
                parts.append(' ')
            elif node.tag in (q('w', 'drawing'), q('w', 'pict')):
                textboxes = node.findall('.//w:txbxContent', NS)
                if textboxes:
                    parts.extend(self.blocks(box) for box in textboxes)
                else:
                    refs = [n.get(q('r', 'embed')) for n in node.findall('.//a:blip', NS)]
                    refs += [n.get(q('r', 'id')) for n in node.findall('.//v:imagedata', NS)]
                    for rid in dict.fromkeys(refs):
                        if rid and rid in self.rels:
                            rel = self.rels[rid]
                            if Path(rel['Target']).name in EXCLUDED_MEDIA.get(self.meta['slug'], set()):
                                continue
                            if rel.get('TargetMode') != 'External':
                                path, width, height = self.media(rel['Target'])
                                self.image_count += 1
                                alt = f'{self.current_heading} · 图 {self.image_count}'
                                parts.append(f'<figure><a href="__BASE__{path}" target="_blank" rel="noopener" aria-label="查看原图：{html.escape(alt, quote=True)}"><img src="__BASE__{path}" alt="{html.escape(alt, quote=True)}" width="{width}" height="{height}" loading="lazy" decoding="async"></a></figure>')
        value = ''.join(parts)
        if '<figure>' not in value and '<p>' not in value:
            props = run.find('w:rPr', NS)
            if props is not None:
                bold = props.find('w:b', NS)
                italic = props.find('w:i', NS)
                if bold is not None and bold.get(q('w', 'val'), '1') not in ('0', 'false'):
                    value = '<strong>' + value + '</strong>' if value else ''
                if italic is not None and italic.get(q('w', 'val'), '1') not in ('0', 'false'):
                    value = '<em>' + value + '</em>' if value else ''
        return value

    def inline(self, element):
        parts, field = [], None
        for child in element:
            if child.tag == q('w', 'r'):
                boundary = child.find('w:fldChar', NS)
                if boundary is not None:
                    kind = boundary.get(q('w', 'fldCharType'))
                    if kind == 'begin':
                        field = {'instruction': '', 'parts': []}
                    elif kind == 'end' and field is not None:
                        display = ''.join(field['parts'])
                        match = re.search(r'HYPERLINK\s+(?:"([^"]+)"|(\S+))', field['instruction'])
                        parts.append(self.anchor(next(v for v in match.groups() if v), display) if match else display)
                        field = None
                    continue
                instruction = child.find('w:instrText', NS)
                if instruction is not None:
                    if field is not None:
                        field['instruction'] += instruction.text or ''
                    continue
                rendered = self.run(child)
            elif child.tag == q('w', 'hyperlink'):
                rel = self.rels.get(child.get(q('r', 'id')), {})
                rendered = self.anchor(rel.get('Target', ''), self.inline(child))
            elif child.tag == q('w', 'fldSimple'):
                instruction = child.get(q('w', 'instr'), '')
                match = re.search(r'HYPERLINK\s+(?:"([^"]+)"|(\S+))', instruction)
                rendered = self.inline(child)
                if match:
                    rendered = self.anchor(next(v for v in match.groups() if v), rendered)
            elif child.tag in (q('w', 'sdt'), q('w', 'sdtContent'), q('w', 'ins')):
                rendered = self.inline(child)
            else:
                continue
            (field['parts'] if field is not None else parts).append(rendered)
        if field is not None:
            parts.extend(field['parts'])
        return ''.join(parts)

    def paragraph(self, paragraph):
        text = ''.join(t.text or '' for t in paragraph.findall('.//w:t', NS)).strip()
        style_id = paragraph.find('w:pPr/w:pStyle', NS)
        style = self.styles.get(style_id.get(q('w', 'val')), '') if style_id is not None else ''
        if not self.seen_title and (style.lower() == 'title' or text in (self.source.stem, self.meta['title'])):
            self.seen_title = True
            return ''
        if self.meta['slug'] == 'seven-realms' and text in ('《七界梦谭》二测', '社区全平台监控报告'):
            return ''
        if text in ('OhMyBoss-Win-本地_内网.zip', '一、游戏作品：', '三、游戏设计思路：', '——'):
            return ''
        heading = re.search(r'heading\s+(\d+)', style, re.I)
        if heading:
            self.current_heading = text
        content = self.inline(paragraph).strip()
        if not content or content == '<br>':
            return ''
        if heading and text:
            level = min(4, max(2, int(heading.group(1)) + 1))
            anchor = f'section-{len(self.headings) + 1}'
            self.headings.append({'id': anchor, 'title': text, 'level': level})
            return f'<h{level} id="{anchor}">{content}</h{level}>'
        if '<figure>' in content or content.startswith(('<p>', '<h', '<ul', '<div')):
            # Images in these source docs are independent paragraphs. Any mixed
            # content is split so block elements never sit inside a <p>.
            pieces = re.split(r'(<figure>.*?</figure>)', content, flags=re.S)
            return ''.join(part if part.startswith(('<figure>', '<p>', '<h', '<div', '<ul')) else f'<p>{part}</p>' for part in pieces if part)
        if paragraph.find('w:pPr/w:numPr', NS) is not None or re.match(r'^[●•]\s*', text):
            return '<ul><li>' + re.sub(r'^(<strong>)?[●•]\s*', r'\1', content) + '</li></ul>'
        return '<p>' + content + '</p>'

    def table(self, element):
        rows, active_merges = [], {}
        for row_index, row in enumerate(element.findall('w:tr', NS)):
            cells, column = [], 0
            for cell in row.findall('w:tc', NS):
                span_node = cell.find('w:tcPr/w:gridSpan', NS)
                span = int(span_node.get(q('w', 'val'), '1')) if span_node is not None else 1
                merge = cell.find('w:tcPr/w:vMerge', NS)
                if merge is not None and merge.get(q('w', 'val')) != 'restart' and column in active_merges:
                    active_merges[column]['rowspan'] += 1
                else:
                    data = {'html': self.blocks(cell), 'colspan': span, 'rowspan': 1, 'tag': 'th' if row_index == 0 else 'td'}
                    cells.append(data)
                    if merge is not None:
                        active_merges[column] = data
                    else:
                        active_merges.pop(column, None)
                column += span
            rows.append(cells)
        output = '<div class="table-scroll" tabindex="0" role="region" aria-label="可横向滚动的数据表"><table><tbody>'
        for row in rows:
            output += '<tr>'
            for cell in row:
                attrs = (' scope="col"' if cell['tag'] == 'th' else '')
                attrs += ''.join(f' {name}="{cell[name]}"' for name in ('colspan', 'rowspan') if cell[name] > 1)
                output += f'<{cell["tag"]}{attrs}>{cell["html"]}</{cell["tag"]}>'
            output += '</tr>'
        return output + '</tbody></table></div>'

    def blocks(self, element):
        output = []
        for child in element:
            if child.tag == q('w', 'p'):
                output.append(self.paragraph(child))
            elif child.tag == q('w', 'tbl'):
                output.append(self.table(child))
            elif child.tag in (q('w', 'sdt'), q('w', 'sdtContent')):
                output.append(self.blocks(child))
        return '\n'.join(filter(None, output))

    def export(self):
        body = self.blocks(self.doc.find('w:body', NS))
        body = re.sub(r'</ul>\s*<ul>', '', body)
        if self.meta['slug'] in SLIDES:
            figures = re.findall(r'<figure>.*?</figure>', body, flags=re.S)
            sections = SLIDES[self.meta['slug']]
            assert len(figures) == len(sections), (self.source.name, len(figures))
            body = ''
            self.headings = []
            for index, ((title, description), figure) in enumerate(zip(sections, figures)):
                anchor = f'section-{index+1}'
                self.headings.append({'id': anchor, 'title': title, 'level': 2})
                figure = re.sub(r'alt="[^"]*"', f'alt="{html.escape(title)}：原始设计板"', figure)
                body += f'<h2 id="{anchor}">{title}</h2><p>{description}</p>{figure}\n'
            if self.meta['slug'] == 'oh-my-boss':
                body = '<p class="article-callout">2025 年腾讯 IE 校招生培训项目 · Minigame 第二名</p>\n' + body
        # URL-like visible text is left as authored; only genuine hyperlink
        # fields become clickable, preventing accidental invented references.
        cover_source = self.zip.read('word/media/' + self.meta['coverImage'])
        cover = ImageOps.exif_transpose(Image.open(BytesIO(cover_source))).convert('RGB')
        if self.meta.get('coverCrop'):
            cover = cover.crop(self.meta['coverCrop'])
        cover.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        cover.save(self.media_dir / 'cover.webp', 'WEBP', quality=90, method=6)
        gallery = []
        for index, (source_name, bounds, alt) in enumerate(GALLERY_CROPS.get(self.meta['slug'], [])):
            source_image = Image.open(BytesIO(self.zip.read('word/media/' + source_name))).convert('RGB')
            source_image.crop(bounds).save(self.media_dir / f'gallery-{index+1}.webp', 'WEBP', quality=94, method=6)
            gallery.append({'src': f'media/{self.meta["slug"]}/gallery-{index+1}.webp', 'alt': alt})
        visible_chars = len(re.sub('<[^>]+>', '', body))
        article = {k: v for k, v in self.meta.items() if k not in ('pattern', 'coverImage', 'coverCrop')}
        article.update(cover=f'media/{self.meta["slug"]}/cover.webp', readingMinutes=max(4, math.ceil(visible_chars / 450 + len(self.images) * .08)), html=body, sourceFile=self.source.name, images=self.images, headings=self.headings, externalLinks=sorted(self.links))
        if gallery:
            article['gallery'] = gallery
        self.zip.close()
        return article


def main():
    articles = []
    for meta in ARTICLES:
        matches = list((ROOT / 'resource').glob(meta['pattern'] + '.docx'))
        assert len(matches) == 1, (meta['pattern'], matches)
        article = Exporter(matches[0], meta).export()
        articles.append(article)
        print(f'{article["slug"]}: {len(article["images"])} images, {len(article["html"])} HTML chars, {len(article["externalLinks"])} links')
    target = ROOT / 'src' / 'data' / 'portfolio.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(articles, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
