import os
import re
import hashlib
import argparse
from tex2png import tex2png
from imgsize import get_image_size

# http://stackoverflow.com/questions/36391979/find-markdown-image-syntax-in-string-in-java
# match Markdown image syntax ![alt](image_link)
# group 1: `alt`; group 2 `image_link`
image_re = re.compile(r'!\[([^\])]*)\]\(([^)]+)\)')

# http://stackoverflow.com/questions/17767251/how-to-ignore-escaped-character-in-regex
# negative lookahead: In general, (?<!Y)X matches an X that is not preceded by Y.
# inline math: $ .... $ but \$ escapes dollar sign
single_re = re.compile(r'(?<!\\)\$([^\$]+)(?<!\\)\$')

# diplay mode math: $$ .... $$ but \$ escapes dollar sign
double_re = re.compile(r'(?<!\\)\$\$([^\$]+)(?<!\\)\$\$')

# match literal dollar
dollar_re = re.compile(r'\\\$')


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
    
    
def gen_github_link(github_path, alt, height=None):
    """
    Generate image markdown code with absolute URL link
    <img src="https://raw.githubusercontent.com/LinxiFan/temp/master/d500.png" 
    height="20" />
    
    github_path: <username>/<repo>/<branch>/<folders>/<filename>
    """
    if height:
        return ('<img src="https://raw.githubusercontent.com/{}" alt="{}" '
               'height="{}" />'
               .format(github_path, alt, height))
    else:
        return ('![{}](https://raw.githubusercontent.com/{})'
                .format(alt, github_path))


def md5(s):
    # hash latex code into unique file name
    h = hashlib.new('MD5')
    h.update(s.encode('utf-8'))
    return h.hexdigest()


def process_image(line, github_root):
    "Convert relative-path image links to absolute"
    spans = []
    replacements = []
    for match in image_re.finditer(line):
        alt, image_link = match.groups()
        image_link = image_link.strip()
        if image_link.startswith('/'):
            github_path = github_root + image_link
            spans.append(match.span())
            replacements.append(gen_github_link(github_path, alt))
    return replace_n(line, spans, replacements)


def get_height(formula, display_math):
    # the inline image needs to be resized for better github rendering
    if display_math:
        return 


def process_latex(line, display_math, github_root, image_folder=''):
    if image_folder:
        image_folder += '/'
    spans = []
    replacements = []
    formula_image_pairs = set() # (formula, latex-images-to-be-generated) tuple
    
    if display_math:
        latex_re = double_re
    else:
        latex_re = single_re
    
    for match in latex_re.finditer(line):
        spans.append(match.span())
        formula_with_dollar, formula = match.group(0), match.group(1)
        png_file = image_folder + md5(formula_with_dollar) + '.png'
        github_path = github_root + '/' + png_file
        formula_image_pairs.add((formula, png_file))
        replacements.append(gen_github_link(github_path, formula, height=18))
    return replace_n(line, spans, replacements), formula_image_pairs, display_math


def process_dollar(line):
    # escaped `\$` will be translated to a dollar sign literal
    return dollar_re.sub('$', line)


def translate(src_md, output_md, github_root, image_folder):
    output_md = open(output_md, 'w')
    formula_image_tuples = set()
    for line in open(src_md):
        # check for images first, replace relative paths that start with `/`
        line = process_image(line, github_root)
        # display math mode $$...$$
        line, pairs = process_latex(line, double_re, github_root, image_folder)
        formula_image_tuples.update([pair + (True,) for pair in pairs]) # display math
        # inline mode $...$
        line, pairs = process_latex(line, single_re, github_root, image_folder)
        formula_image_tuples.update([pair + (False,) for pair in pairs]) # display math
        # replace `\$` to literal `$`
        line = process_dollar(line)
        print(line, end='', file=output_md)
    output_md.close()
    # generate all the formula images
    for formula, img_file, display_math in formula_image_tuples:
        tex2png(**{'formula': formula,
                   'output_file': img_file,
                   'display_math': display_math,
                   'dpi': 300})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('github_root', 
                        help='<username>/<repo>/<branch>')
    parser.add_argument('src_md', help='Source markdown file')
    parser.add_argument('output_md', help='Output markdown file')

    parser.add_argument('-d', '--image-folder', default='',
                        help='Folder for the generated latex images, '
                        'must be RELATIVE PATH with respect to your github dir.')

    args = parser.parse_args()
    translate(**vars(args))
