import ast
import tokenize
import io
import os
import sys

def get_docstring_ranges(source):
    """Get line ranges (1-based start_line, end_line inclusive) of all docstrings."""
    ranges = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ranges
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (node.body and isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                doc_node = node.body[0]
                s = doc_node.lineno
                e = doc_node.end_lineno
                ranges.append((s, e))
    
    return sorted(ranges)

def is_in_docstring(line_num, docstring_ranges):
    """Check if a line is within any docstring range."""
    for s, e in docstring_ranges:
        if s <= line_num <= e:
            return True
    return False

def remove_comments_and_docstrings_from_source(source):
    """Remove comments and docstrings from Python source code."""
    docstring_ranges = get_docstring_ranges(source)
    
    result_lines = []
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    
    current_line_num = 0
    current_line_content = ""
    docstring_lines_remaining = 0
    
    for tok_type, tok_string, tok_start, tok_end, tok_line in tokens:
        start_line, start_col = tok_start
        end_line, end_col = tok_end
        
        if start_line != current_line_num:
            if current_line_num > 0:
                result_lines.append(current_line_content.rstrip())
            current_line_num = start_line
            current_line_content = ""
        
        if is_in_docstring(start_line, docstring_ranges):
            continue
        
        if tok_type == tokenize.COMMENT:
            continue
        
        if tok_type == tokenize.NL:
            current_line_content += tok_string
            continue
        
        if tok_type == tokenize.NEWLINE:
            current_line_content += tok_string
            continue
        
        if tok_type == tokenize.INDENT:
            current_line_content += tok_string
            continue
        
        if tok_type == tokenize.DEDENT:
            continue
        
        if tok_type == tokenize.ENDMARKER:
            break
        
        current_line_content += tok_string
    
    if current_line_content:
        result_lines.append(current_line_content.rstrip())
    
    cleaned = "\n".join(result_lines)
    
    final_lines = []
    in_doc = False
    doc_start_marker = None
    doc_start_line = -1
    
    docstring_boundaries = set()
    for s, e in docstring_ranges:
        for ln in range(s, e + 1):
            docstring_boundaries.add(ln)
    
    lines = cleaned.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if (i + 1) in docstring_boundaries:
            if stripped.startswith(('"""', "'''")):
                if stripped.endswith(('"""', "'''")) and len(stripped) >= 6:
                    i += 1
                    continue
                else:
                    marker = stripped[:3]
                    i += 1
                    while i < len(lines):
                        nxt = lines[i]
                        if marker in nxt:
                            i += 1
                            break
                        i += 1
                    continue
            else:
                i += 1
                continue
        
        hash_pos = -1
        in_single_quote = False
        in_double_quote = False
        in_triple_single = False
        in_triple_double = False
        
        j = 0
        while j < len(line):
            ch = line[j]
            nxt = line[j+1] if j+1 < len(line) else ''
            nxt2 = line[j+2] if j+2 < len(line) else ''
            
            if in_triple_double:
                if ch == '"' and nxt == '"' and nxt2 == '"':
                    in_triple_double = False
                    j += 3
                    continue
                j += 1
                continue
            if in_triple_single:
                if ch == "'" and nxt == "'" and nxt2 == "'":
                    in_triple_single = False
                    j += 3
                    continue
                j += 1
                continue
            if in_double_quote:
                if ch == '\\':
                    j += 2
                    continue
                if ch == '"':
                    in_double_quote = False
                j += 1
                continue
            if in_single_quote:
                if ch == '\\':
                    j += 2
                    continue
                if ch == "'":
                    in_single_quote = False
                j += 1
                continue
            
            if ch == '"' and nxt == '"' and nxt2 == '"':
                in_triple_double = True
                j += 3
                continue
            if ch == "'" and nxt == "'" and nxt2 == "'":
                in_triple_single = True
                j += 3
                continue
            if ch == '"':
                in_double_quote = True
                j += 1
                continue
            if ch == "'":
                in_single_quote = True
                j += 1
                continue
            if ch == '#':
                hash_pos = j
                break
            j += 1
        
        if hash_pos != -1:
            line = line[:hash_pos].rstrip()
        
        final_lines.append(line)
        i += 1
    
    final_text = "\n".join(final_lines)
    while "\n\n\n" in final_text:
        final_text = final_text.replace("\n\n\n", "\n\n")
    return final_text

def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='latin-1') as f:
            source = f.read()
    
    if not source.strip():
        return False
    
    cleaned = remove_comments_and_docstrings_from_source(source)
    
    if cleaned != source:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        return True
    return False

def main():
    files = [
        r"repairs/models.py",
        r"repairs/views.py",
        r"repairs/forms.py",
        r"repairs/urls.py",
        r"repairs/matching.py",
        r"repairs/admin.py",
        r"repairs/apps.py",
        r"repairs/tests.py",
        r"repairs/__init__.py",
        r"repairs/management/__init__.py",
        r"repairs/management/commands/__init__.py",
        r"repairs/management/commands/seed_data.py",
        r"repairs/migrations/0001_initial.py",
        r"repairs/migrations/__init__.py",
        r"reviews/models.py",
        r"reviews/views.py",
        r"reviews/forms.py",
        r"reviews/urls.py",
        r"reviews/admin.py",
        r"reviews/apps.py",
        r"reviews/tests.py",
        r"reviews/__init__.py",
        r"reviews/migrations/0001_initial.py",
        r"reviews/migrations/__init__.py",
        r"notifications/models.py",
        r"notifications/views.py",
        r"notifications/urls.py",
        r"notifications/context_processors.py",
        r"notifications/admin.py",
        r"notifications/apps.py",
        r"notifications/tests.py",
        r"notifications/__init__.py",
        r"notifications/migrations/0001_initial.py",
        r"notifications/migrations/__init__.py",
    ]
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    modified = []
    
    for rel_path in files:
        full_path = os.path.join(base_dir, rel_path)
        if os.path.exists(full_path):
            print(f"Processing: {rel_path}...", end=" ")
            changed = process_file(full_path)
            if changed:
                print("MODIFIED")
                modified.append(rel_path)
            else:
                print("unchanged")
        else:
            print(f"MISSING: {rel_path}")
    
    print("\n=== MODIFIED FILES ===")
    for f in modified:
        print(f)
    print(f"\nTotal modified: {len(modified)}")

if __name__ == "__main__":
    main()
