import re
import string
import warnings
from bs4 import BeautifulSoup

# Suppress BeautifulSoup warnings
warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

# regular expressions
split_regex = r""" |!|"|\#|\$|%|&|'|\(|\)|\*|\+|,|-|\.|/|:|;|<|=|>|\?|@|\[|\\|\]|\^|_|`|{|}|~"""
SPLIT_PATTERN = re.compile(split_regex)
SEP_PATTERN = re.compile(r'(=|-|\+|\*|#|_){4,}')

line_quality_threshold = 1.6


def eval_text(text, codeparser):
    text = format_post(text, codeparser)
    return eval_line(text)


def eval_line(text):
    text_len = len(text)
    if text_len > 1000:
        if line_quality(text) >= line_quality_threshold:
            return text
    else:
        return text
    return -1


def line_quality(text):
    punc = 0
    for c in text:
        if c in string.punctuation:
            punc += 1
    if punc == 0:
        punc = 1
    words = len(list(filter(None, SPLIT_PATTERN.split(text))))
    quality = words/punc
    return quality


def format_post(post, codeparser, tag_param='pre'):
    soup = BeautifulSoup(post, 'lxml')
    for tag in soup.find_all(tag_param):
        tag.string = codeparser.tokenize_sequence(
            tag.getText(), unique_tokens=True)
    return strip_whitespace(strip_separators(soup.getText()))


def strip_separators(text):
    return SEP_PATTERN.sub(' ', text)


def strip_whitespace(text):
    text_out = text.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
    return ' '.join(text_out.split())
