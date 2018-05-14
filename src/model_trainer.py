#!/usr/bin/env python

import os
import sys
import argparse
import subprocess
from wordvec_model.tfidf_utils import load_text_list, train_tfidf_model

fastText_params = {}


def train_fasttext_model(params):
    pass


def main(corpus_path, export_dir, model_type, params_path=None):
    if model_type == 'ft':
        assert params_path
        train_fasttext_model(corpus_path, params_path)
    elif model_type == 'tfidf':
        model_path = os.path.join(export_dir, 'tfidf_v0.2.pkl')
        train_matrix_path = os.path.join(export_dir,
                                         'tfidf_train_matrix_v0.2.pkl')
        train_tfidf_model(
            load_text_list(corpus_path), model_path, train_matrix_path)
    else:
        raise ValueError('Model type "{}" not recognized.'.format(model_type))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
