import os
import re
import hashlib
import argparse
import shutil
import subprocess as pc
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


def get_height(png_file, display_math):
    # inline image needs to be resized for better github rendering
    _, height = get_image_size(png_file)
    scale = 1.2 if display_math else 1.0
    return int(height / 3.0 * scale)


def process_latex(line, display_math, github_root, image_folder=''):
    if image_folder:
        image_folder += '/'
    spans = []
    replacements = []
    latex_files = set() # {latex-images-to-be-generated}
    
    if display_math:
        latex_re = double_re
    else:
        latex_re = single_re
    
    for match in latex_re.finditer(line):
        spans.append(match.span())
        formula_with_dollar, formula = match.group(0), match.group(1)
        png_file = image_folder + md5(formula_with_dollar) + '.png'
        github_path = github_root + '/' + png_file
        if not png_file in latex_files: # avoid regeneration
            latex_files.add(png_file)
            tex2png(**{'formula': formula,
                       'output_file': png_file,
                       'display_math': display_math,
                       'dpi': 300})
            assert os.path.exists(png_file)

        replacements.append(gen_github_link(github_path, formula, 
                                    height=get_height(png_file, display_math)))
    return replace_n(line, spans, replacements)


def process_dollar(line):
    # escaped `\$` will be translated to a dollar sign literal
    return dollar_re.sub('$', line)


def remove_ext(name):
    return os.path.splitext(name)[0]

def bash(cmd):
    return pc.check_output(cmd.split()).decode('utf-8').strip()

def get_github_info(remote='origin'):
    try:
        git_remotes = bash('git remote -v')
        git_current_branch = bash('git rev-parse --abbrev-ref HEAD')
    except pc.CalledProcessError as exc:                                                                                                   
        print('git ERROR!!!\n', 
              '-'*50, '\n', 
              exc.output.decode('utf-8'),
              '-'*50) # exc.returncode
        raise

    git_remotes = git_remotes.split('\n')
    for info in git_remotes:
        # typically looks like:
        # bakkdoor  https://github.com/bakkdoor/grit (fetch)
        # bakkdoor  https://github.com/bakkdoor/grit (push)
        # koke      git://github.com/koke/grit.git (fetch)
        # koke      git://github.com/koke/grit.git (push)
        # origin    git@github.com:mojombo/grit.git (fetch)
        # origin    git@github.com:mojombo/grit.git (push)
        info = info.strip().split()
        assert len(info) == 3 and info[-1] in ['(fetch)', '(push)'], \
            'bad git remote format {}'.format(info)
        if info[0] == remote:
            url = info[1]
            # hardcoded parse
            if url.startswith('git@'):
                account, repo = url.split('/')
                account = account.split(':')[-1]
            else:
                # take the last two items
                *_, account, repo = url.split('/')
            repo = remove_ext(repo)
            return (account, repo, git_current_branch)
    raise Exception('remote {} not found in the current git repo.'.format(remote))


def translate(src_md, output_md, remote, image_folder):
    github_root = '/'.join(get_github_info(remote))
    print('Detected github root:', github_root)
    
    output_md = open(output_md, 'w')
    for line in open(src_md):
        # check for images first, replace relative paths that start with `/`
        line = process_image(line, github_root)
        # display math mode $$...$$
        line = process_latex(line, True, github_root, image_folder)
        # inline mode $...$
        line = process_latex(line, False, github_root, image_folder)
        # replace `\$` to literal `$`
        line = process_dollar(line)
        print(line, end='', file=output_md)
    output_md.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('src_md', help='Source markdown file')
    parser.add_argument('output_md', help='Output markdown file')

    parser.add_argument('-d', '--image-folder', default='',
                        help='Folder for the generated latex images, '
                        'must be RELATIVE PATH with respect to your github dir.')
    parser.add_argument('-r', '--remote', default='origin',
                        help='Github remote to push')

    args = parser.parse_args()
    folder = args.image_folder
    if folder and not os.path.exists(folder):
        os.mkdir(folder)
        print('Created new folder for generated latex images: {}'.format(folder))
    
    translate(**vars(args))