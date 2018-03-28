#!/usr/bin/env python

import re
import json
import numpy as np
from keras.preprocessing.text import Tokenizer

# RegEx patterns
ERRLINE_RE = re.compile(r':\d*\)')
keepPunct_RE = r'|\||\&|\#|\@|\~|\_|\'|\"|\=|\\|\/|\-|\:|\;|\*|\.|\$|\(|\)|\[|\]|\{|\}'
TOKEN_PATTERN = re.compile(r'(?u)\b\w\w+\b' + keepPunct_RE)

# Lambda functions
tokenize = lambda line: TOKEN_PATTERN.findall(line)
errline = lambda line: ERRLINE_RE.sub(':_xerrx_)', line)

# Out Of Vocabulary default token value
#oov = 11999

class Vectorizer:
    def __init__(self, dictionary):
        self.oov = 11999
        self.token_dict = dictionary
    
    def vectorize_doc(self, doc_path):
        # encode post tokens using the provided dictionary
        enc_doc = []
        with open(doc_path, 'r') as f:
            for line in f:
                enc_doc.append(self.vectorize_string(line))
        return enc_doc

    def vectorize_list(self, doc_list):
        enc_doc = []
        for line in doc_list:
            enc_doc.append(self.vectorize_string(line))
        return enc_doc
        
    def vectorize_string(self, string):
        string = ' '.join(tokenize(errline(string.strip().lower())))
        return np.array([self.token_dict.get(t, self.oov) for t in string.split()])

def build_dict(labeled_posts_path):
    token = Tokenizer(filters='')
    posts = []
    with open(labeled_posts_path, 'r') as f:
        for line in f:
            posts.append(' '.join(tokenize(errline(line.strip().lower()))))
    # fit tokenizer on posts and create token index
    token.fit_on_texts(posts)
    token_dict = token.word_index
    return token_dict

def list_to_ndarray(filename):
    llist = []
    with open(raw_folder + filename, 'r') as f:
        for line in f:
            llist.append(int(line))
    np.save(vec_folder + filename + '.npy', llist)

def save_dict(output_path, dictionary):
    with open(output_path, 'w') as out:
        json.dump(dictionary, out, indent=2)

def load_dict(dict_path):
    with open(dict_path, 'r') as _in:
        return json.load(_in)

if __name__ == '__main__':
    # build token dictionary on the selected and labeled posts
    token_dict = build_dict('training_data/raw_data/labeled_posts')
    save_dict('data/token_dictionary.json', token_dict)
