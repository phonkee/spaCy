# coding: utf8
from __future__ import unicode_literals, print_function
import os
import io
import json
import re
import os.path
import pathlib
import sys

import six
import textwrap

from .attrs import TAG, HEAD, DEP, ENT_IOB, ENT_TYPE

try:
    basestring
except NameError:
    basestring = str


LANGUAGES = {}
_data_path = pathlib.Path(__file__).parent / 'data'


def set_lang_class(name, cls):
    global LANGUAGES
    LANGUAGES[name] = cls


def get_lang_class(name):
    lang = re.split('[^a-zA-Z0-9]', name, 1)[0]
    if lang not in LANGUAGES:
        raise RuntimeError('Language not supported: %s' % lang)
    return LANGUAGES[lang]


def get_data_path(require_exists=True):
    if not require_exists:
        return _data_path
    else:
        return _data_path if _data_path.exists() else None


def set_data_path(path):
    global _data_path
    if isinstance(path, basestring):
        path = pathlib.Path(path)
    _data_path = path


def or_(val1, val2):
    if val1 is not None:
        return val1
    elif callable(val2):
        return val2()
    else:
        return val2


def match_best_version(target_name, target_version, path):
    path = path if not isinstance(path, basestring) else pathlib.Path(path)
    if path is None or not path.exists():
        return None
    matches = []
    for data_name in path.iterdir():
        name, version = split_data_name(data_name.parts[-1])
        if name == target_name and constraint_match(target_version, version):
            matches.append((tuple(float(v) for v in version.split('.')), data_name))
    if matches:
        return pathlib.Path(max(matches)[1])
    else:
        return None


def split_data_name(name):
    return name.split('-', 1) if '-' in name else (name, '')


def constraint_match(constraint_string, version):
    # From http://github.com/spacy-io/sputnik
    if not constraint_string:
        return True

    constraints = [c.strip() for c in constraint_string.split(',') if c.strip()]

    for c in constraints:
        if not re.match(r'[><=][=]?\d+(\.\d+)*', c):
            raise ValueError('invalid constraint: %s' % c)

    return all(semver.match(version, c) for c in constraints)


def read_regex(path):
    path = path if not isinstance(path, basestring) else pathlib.Path(path)
    with path.open() as file_:
        entries = file_.read().split('\n')
    expression = '|'.join(['^' + re.escape(piece) for piece in entries if piece.strip()])
    return re.compile(expression)


def compile_prefix_regex(entries):
    if '(' in entries:
        # Handle deprecated data
        expression = '|'.join(['^' + re.escape(piece) for piece in entries if piece.strip()])
        return re.compile(expression)
    else:
        expression = '|'.join(['^' + piece for piece in entries if piece.strip()])
        return re.compile(expression)


def compile_suffix_regex(entries):
    expression = '|'.join([piece + '$' for piece in entries if piece.strip()])
    return re.compile(expression)


def compile_infix_regex(entries):
    expression = '|'.join([piece for piece in entries if piece.strip()])
    return re.compile(expression)


def normalize_slice(length, start, stop, step=None):
    if not (step is None or step == 1):
        raise ValueError("Stepped slices not supported in Span objects."
                         "Try: list(tokens)[start:stop:step] instead.")
    if start is None:
       start = 0
    elif start < 0:
       start += length
    start = min(length, max(0, start))

    if stop is None:
       stop = length
    elif stop < 0:
       stop += length
    stop = min(length, max(start, stop))

    assert 0 <= start <= stop <= length
    return start, stop


def utf8open(loc, mode='r'):
    return io.open(loc, mode, encoding='utf8')


def check_renamed_kwargs(renamed, kwargs):
    for old, new in renamed.items():
        if old in kwargs:
            raise TypeError("Keyword argument %s now renamed to %s" % (old, new))


def parse_package_meta(package_path, package, on_error=False):
    location = os.path.join(str(package_path), package, 'meta.json')
    if not os.path.isfile(location) and on_error:
        on_error()
    else:
        with io.open(location, encoding='utf8') as f:
            meta = json.load(f)
            return meta
    return False


def print_msg(*text, **kwargs):
    """Print formatted message. Each positional argument is rendered as newline-
    separated paragraph. If kwarg 'title' exist, title is printed above the text
    and highlighted (using ANSI escape sequences manually to avoid unnecessary
    dependency)."""

    message = '\n\n'.join([_wrap_text(t) for t in text])
    tpl_msg = '\n{msg}\n'
    tpl_title = '\n\033[93m{msg}\033[0m'

    if 'title' in kwargs and kwargs['title']:
        title = _wrap_text(kwargs['title'])
        print(tpl_title.format(msg=title))
    print(tpl_msg.format(msg=message))


def _wrap_text(text):
    """Wrap text at given width using textwrap module. Indent should consist of
    spaces. Its length is deducted from wrap width to ensure exact wrapping."""

    wrap_max = 80
    indent = '    '
    wrap_width = wrap_max - len(indent)
    return textwrap.fill(text, width=wrap_width, initial_indent=indent,
                               subsequent_indent=indent, break_long_words=False,
                               break_on_hyphens=False)


def sys_exit(*messages, **kwargs):
    """Performs SystemExit. For modules used from the command line, like
    download and link. To print message, use the same arguments as for
    print_msg()."""

    if messages:
        print_msg(*messages, **kwargs)
    sys.exit(0)
