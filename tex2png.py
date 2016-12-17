import os
import shutil
import argparse
import tempfile
import subprocess as pc


def get_binary(program, check=True):
    binary = shutil.which(program)
    if check and not binary:
        raise Exception('Required program {} not found'.format(program))
    return binary


def gen_latex_file(args, temp_dir):
    # generate temporary latex file with the formula code
    delimiter = '$$' if args.display_math else '$'
    # comma separated
    package_spec = r''
    pkgs = args.packages.split(',')
    for pkg in pkgs:
        if not pkg: break
        package_spec += r'\usepackage{{{}}}'.format(pkg)
    with tempfile.NamedTemporaryFile(suffix='.tex', 
                                     delete=False,
                                     mode='w',
                                     dir=temp_dir) as temp_tex:
        print(r"\documentclass[12pt]{{article}}{_packages}\pagestyle{{empty}}"
              r"\begin{{document}}{_delimiter}"
              r"{_formula}"
              r"{_delimiter}\end{{document}}"
              .format(_packages=package_spec, 
                      _formula=args.formula,
                      _delimiter=delimiter),
              end='', file=temp_tex)
    return temp_tex


def run_latex(temp_tex, temp_dir):
    try:
        pc.check_output([get_binary('latex'), 
                         '-halt-on-error', 
                         '-output-directory={}'.format(temp_dir), 
                         temp_tex.name])
    except pc.CalledProcessError as exc:                                                                                                   
        print('LaTeX ERROR!!!\n', 
              'Clean up temp dir', temp_dir, '\n',
              '-'*50, '\n', 
              exc.output.decode('utf-8'),
              '-'*50) # exc.returncode
        print('Clean up temp dir', temp_dir)
        shutil.rmtree(temp_dir)
        raise


def run_dvipng(args, temp_tex, temp_dir):
    temp_dvi = os.path.splitext(temp_tex.name)[0] + '.dvi'
    assert os.path.exists(temp_dvi), \
        "LaTeX generated DVI file {} doesn't exist".format(temp_dvi)
    try:
        pc.check_output([get_binary('dvipng'), 
                         '-D', str(args.dpi),
                         '-fg', args.foreground,
                         '-bg', args.backgroud,
                         '-o', args.output_file,
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


def run_optipng(args):
    if not args.optimize: 
        return
    assert os.path.exists(args.output_file), \
        "Output png file {} doesn't exist".format(args.output_file)
    try:
        optipng = get_binary('optipng', check=False) 
        if not optipng:
            print('optipng not found, skip optimization. ')
            return
        pc.check_output([bin, '-zc1-9', '-zm1-9', '-zs0-3', '-f0-5', 
                         args.output_file])
    except pc.CalledProcessError as exc:                                                                                                   
        print('optipng ERROR!!!\n', 
              '-'*50, '\n', 
              exc.output.decode('utf-8'),
              '-'*50) # exc.returncode
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('formula', help='LaTeX formula text')
    parser.add_argument('output_file', help='output png file')
    parser.add_argument('-m', '--display-math', action='store_true', 
                        help='LaTeX math display mode')
    parser.add_argument('-d', '--dpi', type=int, default=300,
                        help='Output resolution in DPI')
    parser.add_argument('-p', '--packages', default='',
                        help='Comma seperated list of LaTeX package names')
    parser.add_argument('-fg', '--foreground', default='Black',
                        help='Set the foreground color')
    parser.add_argument('-bg', '--backgroud', default='White',
                        help='Set the backgroud color')
    parser.add_argument('-O', '--optimize', action='store_true',
                        help='Optimize output image using `optipng`')

    args = parser.parse_args()
    
    # make a temporary directory
    temp_dir = tempfile.mkdtemp('gitex')
    print(temp_dir)
    temp_tex = gen_latex_file(args, temp_dir)
    run_latex(temp_tex, temp_dir)
    run_dvipng(args, temp_tex, temp_dir)
    run_optipng(args)
    
    shutil.rmtree(temp_dir)