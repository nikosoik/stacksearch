#!/usr/bin/env python

import os
import argparse

from wordvec_model.utils import print_linked_posts
from wordvec_model.tfidf_model import TfIdfSearch
from wordvec_model.fasttext_model import FastTextSearch

# versions
ft_version = 'v0.1.2'
tfidf_version = 'v0.1'

## Paths
# Models
tfidf_model = 'wordvec_model/tfidf_archive/tfidf_' + tfidf_version + '.pkl'
fasttext_model = 'wordvec_model/fasttext_archive/ft_' + ft_version + '.bin'

# Indexes
fasttext_index = 'wordvec_model/index/ft_' + ft_version + '_post_index.pkl'
tfidf_index = os.path.realpath(
    'wordvec_model/index/tfidf_' + tfidf_version + '_post_index.pkl')

# WordVec Index
fasttext_wordvec_index = 'wordvec_model/index/ft_' + ft_version + '_wordvec_index.pkl'

# Metadata
metadata_path = os.path.realpath('wordvec_model/index/metadata.json')

# API Dict
api_dict = os.path.realpath('data/api_dict.pkl')


## Demo Functions
def fasttext_demo(api_labels=True):
    ft = None
    index_keys = ['BodyVectors', 'TitleVectors']

    if api_labels:
        ft = FastTextSearch(
            model_path=fasttext_model,
            index_path=fasttext_index,
            index_keys=index_keys,
            metadata_path=metadata_path,
            wordvec_index_path=fasttext_wordvec_index,
            api_dict_path=api_dict)
    else:
        ft = FastTextSearch(
            model_path=fasttext_model,
            index_path=fasttext_index,
            index_keys=index_keys,
            metadata_path=metadata_path)

    ft.search(postid_fn=print_linked_posts, api_labels=True)


def tfidf_demo():
    index_keys = ['BodyVectors', 'TitleVectors']
    tfidf = TfIdfSearch(
        model_path=tfidf_model,
        index_path=tfidf_index,
        index_keys=index_keys,
        metadata_path=metadata_path)

    tfidf.search(postid_fn=print_linked_posts)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='javahunt demo script')
    model_options = parser.add_mutually_exclusive_group()
    model_options.add_argument(
        '--fasttext', '-f', action='store_true', help='fastText demo')
    model_options.add_argument(
        '--tfidf', '-t', action='store_true', help='tf-idf demo')
    #model_options.add_argument('--hybrid', '-h', action='store_true', help='hybrid demo')
    args = parser.parse_args()

    if args.fasttext:
        print('fastText model')
        fasttext_demo()
    elif args.tfidf:
        print('Tf-Idf model')
        tfidf_demo()
    else:
        parser.error('--fasttext or --tfidf option required')
