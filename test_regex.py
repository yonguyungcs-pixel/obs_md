import re

def fix_image_paths(md_content, base_path_str):
    # Fix paths that got wrapped or use backslashes
    import urllib.parse
    base_path_str = base_path_str.replace('\\', '/')
    def replacer(match):
        raw_path = match.group(1)
        # Remove newlines that pandoc might have inserted due to wrapping
        clean_path = raw_path.replace('\n', '').replace('\r', '')
        # Convert backslashes to forward slashes
        clean_path = clean_path.replace('\\', '/')
        # If the path is absolute and starts with the base_path_str, make it relative
        if clean_path.startswith(base_path_str):
            rel_path = clean_path[len(base_path_str):].lstrip('/')
            # URL encode the path so Obsidian handles spaces correctly
            # We must encode spaces as %20
            parts = rel_path.split('/')
            encoded_parts = [urllib.parse.quote(p) for p in parts]
            return "[](" + "/".join(encoded_parts) + ")"
        
        return match.group(0)

    # Match markdown image links ![](path)
    pattern = re.compile(r'\[\]\(([^)]+)\)')
    return pattern.sub(replacer, md_content)

test_md = '''
![](D:\\tools\\bicv_obsidian\\3G125\\MD_SFS\\00_PLE\\00_OLD\\T55-G1(项目暂停)\\assets\\自定义按键功能_A55项目车机&仪表功能需求表
v5/media/image1.png)
'''
print(fix_image_paths(test_md, "D:/tools/bicv_obsidian/3G125/MD_SFS/00_PLE/00_OLD/T55-G1(项目暂停)"))
