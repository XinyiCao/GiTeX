import os
import re
import hashlib
import argparse
import subprocess as pc
from tex2png import tex2png
from imgsize import get_image_size

# http://stackoverflow.com/questions/36391979/find-markdown-image-syntax-in-string-in-java
# match Markdown image syntax ![alt](image_link)
# group 1: `alt`; group 2 `image_link`
image_re = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

# http://stackoverflow.com/questions/17767251/how-to-ignore-escaped-character-in-regex
# negative lookahead: In general, (?<!Y)X matches an X that is not preceded by Y.
# inline math: $ .... $ but \$ escapes dollar sign
inline_re = re.compile(r'(?<!\\)\$([^\$]+)(?<!\\)\$')
# extended: match $ ... $[optional_args]
inline_re = re.compile(r'(?<!\\)\$([^\$]+)(?<!\\)\$(\[[^\]]*\])?')
# non-standard regex support for named group
inline_re = re.compile(r'(?<!\\)\$(?P<formula>[^\$]+)(?<!\\)\$(\[(?P<options>[^\]]*)\])?')

# diplay mode math: $$ .... $$ but \$ escapes dollar sign
display_re = re.compile(r'(?<!\\)\$\$([^\$]+)(?<!\\)\$\$')
# extended; match $$ ... $$[optional_args]
display_re = re.compile(r'(?<!\\)\$\$(?P<formula>[^\$]+)(?<!\\)\$\$(\[(?P<options>[^\]]*)\])?')

# match \include[...] on its own line
include_re = re.compile(r'[\s]*\\include\[(?P<options>[^\]]*)\][\s]*')

# match \begin[...] on its own line
begin_re = re.compile(r'^[\s]*\\begin\[([^\])]*)\][\s]*$')
# make [...] optional
begin_re = re.compile(r'^[\s]*\\begin(\[(?P<options>[^\]]*)\])?[\s]*$')

# match \end on its own line
end_re = re.compile(r'^[\s]*\\end[\s]*$')

# `\\` escape to match literals
escape_re = [
    # ('$$', r'\\\$\$'),
    ('$', r'\\\$'),
    (r'\\end', r'\\\\end'),
    (r'\\begin', r'\\\\begin'),
    (r'\\include', r'\\\\include')
]
escape_re = [(literal, re.compile(regex)) for literal, regex in escape_re]


def bash(cmd):
    return pc.check_output(cmd.split()).decode('utf-8').strip()


def merge_dict(d1, d2):
    dm = d1.copy()
    dm.update(d2)
    return dm


def replace(s, span, replacement):
    # replace a span (tuple) with a new substring
    assert len(span) == 2 and span[0] < span[1] and span[1] <= len(s)
    return s[:span[0]] + replacement + s[span[1]:]


def replace_n(s, spans, replacements):
    # replace all spans (list of tuples) with new substrings
    assert len(spans) == len(replacements)
    if not spans:
        return s
    new_s = s[:spans[0][0]]
    for i in range(len(spans) - 1):
        assert spans[i][1] <= spans[i+1][0]
        new_s += replacements[i] + s[spans[i][1]: spans[i+1][0]]
    return new_s + replacements[-1] + s[spans[-1][1]:]
    
    
def gen_img_code(github_url, alt, width=None, height=None):
    """
    Generate image markdown code with absolute URL link <deprecated>
    <img src="https://raw.githubusercontent.com/LinxiFan/temp/master/d500.png" 
    height="20" />
    github_path: <username>/<repo>/<branch>/<folders>/<filename>
    """
    # remove all new lines in `alt` text
    alt = alt.replace('\n', ' ')
    if height or width:
        width = 'width="{}"'.format(width) if width else ''
        height = 'height="{}"'.format(height) if height else ''
        return ('<img src="{}" alt="{}" {} {} />'
               .format(github_url, alt, width, height))
    else:
        return '![{}]({})'.format(alt, github_url)


def md5(s):
    # hash latex code into unique file name
    h = hashlib.new('MD5')
    h.update(s.encode('utf-8'))
    return h.hexdigest()


def process_image(line):
    """
    New syntax: ![alt](image_url =200x150)
    <width>x<height>
    You can omit either width or height: `=200x` or `=x150`
    """
    spans = []
    replacements = []
    for match in image_re.finditer(line):
        alt, image_url = match.groups()
        image_url = image_url.strip().rsplit('=')
        width, height = None, None
        if len(image_url) == 2:
            size_spec = image_url[1]
            width, height = size_spec.split('x')
        image_url = image_url[0].strip()
        if image_url.startswith('www.'):
            image_url = 'http://' + image_url
        spans.append(match.span())
        replacements.append(gen_img_code(image_url, alt, width, height))
    return replace_n(line, spans, replacements)


def get_height(png_file, dpi, math_mode):
    dpi = int(dpi)
    # inline image needs to be resized for better github rendering
    _, height = get_image_size(png_file)
    if math_mode == 'display':
        scale = 1.2
    elif math_mode == 'inline':
        scale = 1.0
    else:
        scale = 1.1
    shrink = dpi / 100.
    return int(height / shrink * scale)


def run_latex(image_folder, formula, math_mode, **kwargs):
    width, height = None, None
    if 'width' in kwargs:
        width = kwargs.pop('width')
    if 'height' in kwargs:
        height = kwargs.pop('height')
    redraw = kwargs.pop('redraw')
    
    # differentiate display/inline math mode hash, and different config's hash
    md5hash = md5(formula + ('$' if math_mode=='display' else ' ') 
                  + str(sorted(kwargs.items())))
    png_file = os.path.join(image_folder, 'tex_' + md5hash + '.png')
    options = {'formula': formula,
               'output_file': png_file,
               'math_mode': math_mode}
    options.update(kwargs)
    if redraw or not os.path.exists(png_file):
        tex2png(**options)
    assert os.path.exists(png_file), \
        'formula `{}` latex generation failure: {}'.format(formula, png_file)
    
    img_code = gen_img_code(png_file, formula, 
                            width=width,
                            height=height if height 
                                else get_height(png_file, options['dpi'], math_mode))
    return png_file, img_code


def parse_options(options_str):
    if not options_str:
        return {}
    try:
        return dict(map(str.strip, arg.split('='))
                    for arg in options_str.split(',') if '=' in arg)
    except:
        print('arg string format error:', options_str)
        raise


def process_latex(line, math_mode, image_folder, **cmdline_options):
    spans = []
    replacements = []
    
    if math_mode == 'display':
        latex_re = display_re
    elif math_mode == 'inline':
        latex_re = inline_re
    
    for match in latex_re.finditer(line):
        spans.append(match.span())
        formula, options = match.group('formula', 'options')
        options = parse_options(options)
        options = merge_dict(cmdline_options, options)
        png_file, img_code = run_latex(image_folder, formula, math_mode, **options)
        replacements.append(img_code)
    return replace_n(line, spans, replacements)


def process_escapes(line):
    # escaped `\$` will be translated to a dollar sign literal
    for literal, regex in escape_re:
        line = regex.sub(literal, line)
    return line


def translate(src_md, output_md, image_folder, **cmdline_options):
    output_md = open(output_md, 'w')
    src = open(src_md)
    line = 'none'
    
    while line:
        line = src.readline()
        # \begin \end syntax
        begin_stmt = begin_re.match(line)
        if begin_stmt:
            # extra configs to tex2png()
            options = begin_stmt.group('options')
            options = parse_options(options)
            formula = ''
            while line:
                line = src.readline()
                if end_re.match(line):
                    break
                else:
                    formula += line
            if not line:
                raise Exception(r'\begin[] statement has no \end')
            if formula:
                # user can override math mode, defaults to `none`
                math_mode = options.pop('math_mode') if 'math_mode' in options else 'none'
                options = merge_dict(cmdline_options, options)
                png_file, img_code = run_latex(image_folder, formula, math_mode, **options)
                print(img_code, end='', file=output_md)
            # skip the rest of processing
            continue
        
        include_stmt = include_re.match(line)
        if include_stmt:
            options = include_stmt.group('options')
            # \include[file_path, arg1=xx, arg2=...]
            if ',' in options:
                latex_src, options = options.split(',', 1)
            else:
                latex_src, options = options, ''
            assert os.path.exists(latex_src), \
                '\\include {} source file not found.'.format(latex_src)
            formula = open(latex_src).read()
            options = parse_options(options)
            # print(formula, options)
            math_mode = options.pop('math_mode') if 'math_mode' in options else 'none'
            options = merge_dict(cmdline_options, options)
            png_file, img_code = run_latex(image_folder, formula, math_mode, **options)
            print(img_code, end='', file=output_md)
            continue
        
        # check for images to implement the new resize syntax
        line = process_image(line)
        # display math mode $$...$$
        line = process_latex(line, 'display', image_folder, **cmdline_options)
        # inline mode $...$
        line = process_latex(line, 'inline', image_folder, **cmdline_options)
        # replace escapes (e.g. \$ \\include) to literals
        line = process_escapes(line)
        print(line, end='', file=output_md)

    src.close()
    output_md.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('src_md', help='Source markdown file')
    parser.add_argument('output_md', help='Output markdown file')

    parser.add_argument('-i', '--image-folder', default='',
                        help='Folder for the generated latex images, '
                        'must be RELATIVE PATH with respect to your github dir.')
    parser.add_argument('-r', '--redraw', action='store_true',
                        help='force all LaTeX formulas to redraw')
    parser.add_argument('-d', '--dpi', type=int, default=200,
                        help='default global DPI for generated images')

    args = parser.parse_args()
    folder = args.image_folder
    if folder and not os.path.exists(folder):
        os.mkdir(folder)
        print('Created new folder for generated latex images: {}'.format(folder))
    
    translate(**vars(args))