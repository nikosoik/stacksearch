#!/usr/bin/env python

import os
import argparse
from wordvec_model.fastText_utils import FastTextSearch
from wordvec_model.postlink_eval import print_linked_posts
from wordvec_model.tfidf_utils import query_posts as tfidf_search

# versions
ft_version = 'v0.1.2'
tfidf_version = 'v0.1'

## Paths
# Models
tfidf_model = 'wordvec_model/tfidf_archive/tfidf_' + tfidf_version + '.pkl'
fasttext_model = 'wordvec_model/fasttext_archive/ft_' + ft_version + '.bin'

# Indexes
fasttext_index = 'wordvec_model/index/ft_' + ft_version + '_post_index.pkl'
tfidf_index = os.path.realpath('wordvec_model/index/tfidf_' + tfidf_version + '_post_index.pkl')

# WordVec Index
fasttext_wordvec_index = 'wordvec_model/index/ft_' + ft_version + '_wordvec_index.pkl'

# Metadata
metadata_path = os.path.realpath('wordvec_model/index/metadata.json')

# API Dict
api_dict = os.path.realpath('data/api_dict.pkl')

## Functions
def fasttext_demo(title_weight=True):
    index_keys = ['BodyVectors', 'TitleVectors']
    ft = FastTextSearch(fasttext_model, fasttext_index, index_keys, metadata_path)
    ft.search(custom_fn=print_linked_posts)

def tfidf_demo():
    tfidf_search(tfidf_model, tfidf_index, metadata_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='javahunt demo script')
    model_options = parser.add_mutually_exclusive_group()
    model_options.add_argument('--fasttext', '-f', action='store_true', help='fastText demo')
    model_options.add_argument('--tfidf', '-t', action='store_true', help='tf-idf demo')
    args = parser.parse_args()

    if args.fasttext:
        print('fastText model')
        fasttext_demo()
    elif args.tfidf:
        print('Tf-Idf model')
        tfidf_demo()
    else:
        parser.error('--fasttext or --tfidf option required')
