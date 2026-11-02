import zipfile
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ['script', 'style']:
            self.skip = True

    def handle_endtag(self, tag):
        if tag in ['script', 'style']:
            self.skip = False
        elif tag in ['p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']:
            self.result.append('\n')

    def handle_data(self, data):
        if not self.skip:
            self.result.append(data)

    def get_text(self):
        text = "".join(self.result)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

def extract_text_from_html(html_content):
    parser = HTMLTextExtractor()
    try:
        parser.feed(html_content)
        return parser.get_text()
    except:
        return ""

def parse_epub(epub_file):
    chapters = {}
    try:
        with zipfile.ZipFile(epub_file, 'r') as z:
            container_xml = z.read('META-INF/container.xml')
            root = ET.fromstring(container_xml)
            opf_path = root.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile').attrib['full-path']
            
            opf_dir = '/'.join(opf_path.split('/')[:-1])
            if opf_dir: opf_dir += '/'
            
            opf_xml = z.read(opf_path)
            opf_root = ET.fromstring(opf_xml)
            
            manifest = {}
            for item in opf_root.findall('.//{http://www.idpf.org/2007/opf}item'):
                manifest[item.attrib['id']] = item.attrib['href']
                
            spine_ids = []
            for itemref in opf_root.findall('.//{http://www.idpf.org/2007/opf}itemref'):
                spine_ids.append(itemref.attrib['idref'])
                
            titles = {}
            ncx_id = None
            for k, v in manifest.items():
                if v.endswith('.ncx'):
                    ncx_id = k
                    break
                    
            if ncx_id:
                ncx_path = opf_dir + manifest[ncx_id]
                try:
                    ncx_xml = z.read(ncx_path)
                    ncx_root = ET.fromstring(ncx_xml)
                    for navpoint in ncx_root.findall('.//{http://www.daisy.org/z3986/2005/ncx/}navPoint'):
                        label = navpoint.find('.//{http://www.daisy.org/z3986/2005/ncx/}text').text
                        content_src = navpoint.find('.//{http://www.daisy.org/z3986/2005/ncx/}content').attrib['src'].split('#')[0]
                        titles[content_src] = label
                except:
                    pass

            chapter_num = 1
            for spine_id in spine_ids:
                if spine_id not in manifest:
                    continue
                file_href = manifest[spine_id]
                file_path = opf_dir + file_href
                
                try:
                    html_content = z.read(file_path).decode('utf-8')
                    text = extract_text_from_html(html_content)
                    
                    if not text.strip():
                        continue
                        
                    title = titles.get(file_href, f"Chapter {chapter_num}")
                    if title in chapters:
                        title = f"{title} ({chapter_num})"
                        
                    chapters[title] = text
                    chapter_num += 1
                except:
                    continue
    except Exception as e:
        return {"Error": f"Error reading EPUB: {e}"}
        
    return chapters

def chunk_text(text, chunk_size=4000):
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for p in paragraphs:
        if len(current_chunk) + len(p) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = p
        else:
            current_chunk += p + "\n\n"
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks