import os
import shutil
import argparse
import tempfile
import subprocess as pc

class attrdict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def get_binary(program, checkmsg=''):
    binary = shutil.which(program)
    if checkmsg and not binary:
        raise Exception('Required program {} not found. {}'
                        .format(program, checkmsg))
    return binary


def gen_latex_file(temp_dir, formula, packages, math_mode):
    # math_mode: 'inline', 'display', 'headless', or 'none'
    if math_mode == 'inline':
        delimiter = '$'
    elif math_mode == 'display':
        delimiter = '$$'
    else:
        delimiter = '\n'
    packages = 'amsmath,amssymb,' + packages # ams pkgs will always be included
    with tempfile.NamedTemporaryFile(suffix='.tex', 
                                     delete=False,
                                     mode='w',
                                     dir=temp_dir) as temp_tex:
        if math_mode == 'headless':
            codestr = formula
        else:
            codestr = (r"\documentclass[12pt]{{article}}"
                       r"\usepackage{{{_packages}}}\pagestyle{{empty}}"
                       r"\begin{{document}}{_delimiter}"
                       r"{_formula}"
                       r"{_delimiter}\end{{document}}"
                      .format(_packages=packages, 
                              _formula=formula,
                              _delimiter=delimiter))
        print(codestr, end='', file=temp_tex)
    # print(pc.check_output(['cat', temp_tex.name]))
    return temp_tex


def run_latex(temp_dir, temp_tex):
    try:
        pc.check_output(['latex',
                         '-halt-on-error', 
                         '-output-directory={}'.format(temp_dir), 
                         temp_tex.name])
    except pc.CalledProcessError as exc:                                                                                                   
        try:
            print('\nTEX SOURCE:')
            print(pc.check_output(['cat', temp_tex.name]).decode('utf-8'),'\n')
        except: pass
        print('LaTeX ERROR!!!\n', 
              'Clean up temp dir', temp_dir, '\n',
              '-'*50, '\n', 
              exc.output.decode('utf-8'),
              '-'*50) # exc.returncode
        print('Clean up temp dir', temp_dir)
        shutil.rmtree(temp_dir)
        raise


def run_dvipng(temp_dir, temp_tex, output_file, dpi, foreground, background):
    temp_dvi = os.path.splitext(temp_tex.name)[0] + '.dvi'
    assert os.path.exists(temp_dvi), \
        "LaTeX generated DVI file {} doesn't exist".format(temp_dvi)
    try:
        pc.check_output(['dvipng', 
                         '-D', str(dpi),
                         '-fg', foreground,
                         '-bg', background,
                         '-o', output_file,
                         '-q', '--strict', '-T', 'tight',
                         temp_dvi])
    except pc.CalledProcessError as exc:                                                                                                   
        print('dvipng ERROR!!!\n', 
              'Clean up temp dir', temp_dir, '\n',
              '-'*50, '\n', 
              exc.output.decode('utf-8'),
              '-'*50) # exc.returncode
        shutil.rmtree(temp_dir)
        raise


def run_optipng(output_file):
    assert os.path.exists(output_file), \
        "Output png file {} doesn't exist".format(output_file)
    try:
        optipng = get_binary('optipng') 
        if not optipng:
            print('optipng not found, skip optimization. ')
            return
        pc.check_output([bin, '-zc1-9', '-zm1-9', '-zs0-3', '-f0-5', output_file])
    except pc.CalledProcessError as exc:                                                                                                   
        print('optipng ERROR!!!\n', 
              '-'*50, '\n', 
              exc.output.decode('utf-8'),
              '-'*50) # exc.returncode
        raise


def rgb_arg(rgb_str):
    # must convert to rgb <float 0.0-1.0>*3
    rgbs = rgb_str.strip().split()
    assert len(rgbs) == 4, 'rgb value string must be: rgb <R> <G> <B>'
    if all(map(str.isdigit, rgbs[1:])): # all int values
        # convert to 256 scale
        rgb_values = [float(x) / 255.0 for x in rgbs[1:]]
        return '{} {:.4f} {:.4f} {:.4f}'.format(rgbs[0], *rgb_values)
    else:
        return rgb_str


def tex2png(formula,
            output_file,
            math_mode='inline',
            dpi=300,
            packages='',
            foreground='rgb 0.0 0.0 0.0',
            background='rgb 1.0 1.0 1.0',
            optimize=False):
    # check required binaries
    get_binary('latex', 'Install MacTeX: http://www.tug.org/mactex/')
    get_binary('dvipng', 'Install MacTeX: http://www.tug.org/mactex/')
    
    # make a temporary directory
    temp_dir = tempfile.mkdtemp('gitex')
    temp_tex = gen_latex_file(temp_dir, formula, packages, math_mode)
    run_latex(temp_dir, temp_tex)
    run_dvipng(temp_dir, temp_tex, output_file, dpi, 
               foreground=rgb_arg(foreground), 
               background=rgb_arg(background))
    if optimize and not optimize == 'False': # handle string version
        run_optipng(output_file)
    # clean up
    shutil.rmtree(temp_dir)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('formula', help='LaTeX formula text')
    parser.add_argument('output_file', help='output png file')
    parser.add_argument('-m', '--math-mode', default='inline',
                        help='LaTeX math mode: [inline, display, headless, none]')
    parser.add_argument('-d', '--dpi', type=int, default=300,
                        help='Output resolution in DPI')
    parser.add_argument('-p', '--packages', default='amsmath,amssymb',
                        help='Comma seperated list of LaTeX package names additional to '
                        'amsmath,amssymb, which are always included.')
    parser.add_argument('-fg', '--foreground', default='rgb 0.0 0.0 0.0',
                        help='Set the foreground color')
    parser.add_argument('-bg', '--background', default='rgb 1.0 1.0 1.0',
                        help='Set the backgroud color')
    parser.add_argument('-O', '--optimize', action='store_true',
                        help='Optimize output image using `optipng`')

    args = parser.parse_args()
    tex2png(**vars(args))