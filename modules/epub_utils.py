import xml.etree.ElementTree as ET
import posixpath
import urllib.parse

def get_ordered_infolist(zin):
    """
    Returns an ordered list of ZipInfo objects from an EPUB zipfile `zin`.
    - `mimetype` is guaranteed to be first (if present), per EPUB spec.
    - HTML files referenced in the OPF spine follow in their reading order.
    - The remaining files are appended at the end.
    """
    infolist = zin.infolist()
    try:
        # 1. Read META-INF/container.xml
        container_xml = zin.read('META-INF/container.xml')
        root = ET.fromstring(container_xml)
        
        # Find rootfile
        rootfile = None
        for el in root.iter():
            if el.tag.endswith('rootfile'):
                rootfile = el
                break
        
        if rootfile is None or 'full-path' not in rootfile.attrib:
            return infolist
            
        opf_path = rootfile.attrib['full-path']
        opf_xml = zin.read(opf_path)
        opf_root = ET.fromstring(opf_xml)
        
        # Find all manifest items to map id -> href
        manifest_items = {}
        for el in opf_root.iter():
            if el.tag.endswith('item') and 'id' in el.attrib and 'href' in el.attrib:
                manifest_items[el.attrib['id']] = el.attrib['href']
                
        # Find spine to get the ordered reading list
        spine_hrefs = []
        for el in opf_root.iter():
            if el.tag.endswith('itemref') and 'idref' in el.attrib:
                idref = el.attrib['idref']
                if idref in manifest_items:
                    href = manifest_items[idref]
                    opf_dir = posixpath.dirname(opf_path)
                    
                    # URL decoding is often necessary in EPUB internal links
                    decoded_href = urllib.parse.unquote(href)
                    
                    if opf_dir:
                        full_path = posixpath.normpath(posixpath.join(opf_dir, decoded_href))
                    else:
                        full_path = decoded_href
                        
                    spine_hrefs.append(full_path)
                    
        # Match spine full_paths to infolist items
        info_dict = {info.filename: info for info in infolist}
        # Also try url decoded filename mapping just in case
        info_dict_decoded = {urllib.parse.unquote(info.filename): info for info in infolist}
        
        ordered_list = []
        added_files = set()
        
        # Ensure mimetype is first
        mimetype_info = info_dict.get('mimetype')
        if mimetype_info:
            ordered_list.append(mimetype_info)
            added_files.add('mimetype')
        
        # Add spine items
        for href in spine_hrefs:
            info = info_dict.get(href) or info_dict_decoded.get(href)
            if info and info.filename not in added_files:
                ordered_list.append(info)
                added_files.add(info.filename)
                
        # Append all remaining files
        for info in infolist:
            if info.filename not in added_files:
                ordered_list.append(info)
                added_files.add(info.filename)
                
        return ordered_list
        
    except Exception as e:
        # Silently fallback to original infolist on any error
        return infolist
