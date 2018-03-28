#!/usr/bin/env python

import os
import sys
import json
import pickle
import sqlite3
import numpy as np
import pandas as pd
from fastText import load_model as load_ft_model

from preprocessing.preprocessing import process_corpus
from wordvec_model.tfidf_utils import load_model as load_tfidf_model
from wordvec_model.tfidf_utils import build_doc_vectors as build_tfidf_vecs
from wordvec_model.fastText_utils import build_wordvec_index
from wordvec_model.fastText_utils import build_doc_vectors as build_ft_vecs


def load_text_list(filename):
    text_list = []
    with open(filename, 'r') as f:
        for line in f:
            text_list.append(line.strip())
    return text_list

def dump_text_list(filename, text_list):
    with open(filename, 'w') as out:
        for line in text_list:
            out.write(' '.join(line.split()) + '\n')

def fetch_qids(src_database_path, query):
    qids = []
    db_conn = sqlite3.connect(src_database_path)
    c = db_conn.cursor()
    c.execute(query)
    for row in c:
        qids.append(row[0])
    return qids

def build_index_dataset(src_question_dataframe, qids):
    index_ids = []
    index_dataset = {'Title': [], 'Tags': [], 'Body': []}
    qdf = pd.read_pickle(src_question_dataframe)
    for index, row in qdf.iterrows():
        if index in qids:
            index_ids.append(index)
            index_dataset['Tags'].append(row['Tags'])
            index_dataset['Body'].append(row['Body'])
            index_dataset['Title'].append(row['Title'])
    return index_ids, index_dataset

def build_search_index(model_path, index_dataset, mode):
    def tags_to_text_list(tags):
        tag_text_list = []
        for row in list(tags):
            tag_text_list.append(' '.join([tag for tag in row if tag != 'java']))
        if len(tag_text_list) == 0:
            tag_text_list.append('unk')
        return tag_text_list

    if mode == 'ft':
        ft_model = load_ft_model(model_path)
        index_out = {'BodyVectors': None, 'TitleVectors': None, 'TagVectors': None}
        index_out['BodyVectors'] = build_ft_vecs(ft_model, list(index_dataset['Body']))
        index_out['TitleVectors'] = build_ft_vecs(ft_model, list(index_dataset['Title']))
        index_out['TagVectors'] = build_ft_vecs(
            ft_model, tags_to_text_list(index_dataset['Tags']))
        return index_out
    elif mode == 'tfidf':
        tfidf_model = load_tfidf_model(model_path)
        index_out = {'BodyVectors': None, 'TitleVectors': None, 'TagVectors': None}
        index_out['BodyVectors'] = build_tfidf_vecs(tfidf_model, list(index_dataset['Body']))
        index_out['TitleVectors'] = build_tfidf_vecs(tfidf_model, list(index_dataset['Title']))
        index_out['TagVectors'] = build_tfidf_vecs(
            tfidf_model, tags_to_text_list(index_dataset['Tags']))
        return index_out
    else:
        raise ValueError('Unknown model type {}.'.format(mode))

def build_metadata_index(src_database_path, qids, query, export_path):
    def split_tags(str_in):
        tag_list = str_in[1:-1].replace('><', ' ').split()
        return tag_list

    metadata_list = []
    db_conn = sqlite3.connect(src_database_path)
    c = db_conn.cursor()
    c.execute(query.format(id_list=str(tuple(qids))))
    for row in c:
        str_out = {
                    'PostId': row[0],
                    'Score': row[3],
                    'Title': row[1],
                    'Tags': split_tags(row[2])
        }
        metadata_list.append(str_out)
    with open(export_path, 'w') as out:
        json.dump(metadata_list, out, indent=2)

def main(temp_dir, index_export_dir, src_database_path, src_question_dataframe, 
            tfidf_model_path, fasttext_model_path, index_qids_query, metadata_query):
    # Paths
    ft_wordvec_file = fasttext_model_path[:-4] + '.vec'
    ft_wordvec_index = os.path.join(
        index_export_dir, 
        os.path.basename(fasttext_model_path)[:-4] + '_wordvec_index.pkl')
    ft_postvec_index = os.path.join(
        index_export_dir, 
        os.path.basename(fasttext_model_path)[:-4] + '_post_index.pkl')
    tfidf_doc_vec_index = os.path.join(
        index_export_dir, 
        os.path.basename(tfidf_model_path)[:-4] + '_post_index.pkl')
    metadata = os.path.join(index_export_dir, 'metadata.json')
    bodies_corpus = os.path.join(temp_dir, 'bodies')
    titles_corpus = os.path.join(temp_dir, 'titles')
    processed_bodies_corpus = os.path.join(temp_dir, 'processed_bodies')
    processed_titles_corpus = os.path.join(temp_dir, 'processed_titles')
    norm_processed_bodies_corpus = processed_bodies_corpus + '_norm'
    norm_processed_titles_corpus = processed_titles_corpus + '_norm'
    dataframe_export_path = os.path.join(index_export_dir, 'data', 'index_dataset.pkl')

    # Create folders that don't exist
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    if not os.path.exists(os.path.dirname(dataframe_export_path)):
        os.makedirs(os.path.dirname(dataframe_export_path))

    # Build unprocessed index dataset and metadata index
    print('Building search index dataset and metadata lookup...')
    index_ids, index_dataset = build_index_dataset(
        src_question_dataframe, 
        frozenset(fetch_qids(src_database_path, index_qids_query)))
    build_metadata_index(src_database_path, index_ids, metadata_query, metadata)
    
    # Dump question bodies & titles to disk and process them
    print('Processing body & title corpora...')
    dump_text_list(bodies_corpus, index_dataset['Body'])
    process_corpus(bodies_corpus, processed_bodies_corpus, del_stack_trace=True)
    dump_text_list(titles_corpus, index_dataset['Title'])
    process_corpus(titles_corpus, processed_titles_corpus, del_stack_trace=False)
    
    # Load processed bodies & titles from disk
    index_dataset['Body'] = load_text_list(norm_processed_bodies_corpus)
    index_dataset['Title'] = load_text_list(norm_processed_titles_corpus)
    
    print(len(index_ids), len(index_dataset['Body']), len(index_dataset['Title']))
    # Output dataframe to export folder
    pd.DataFrame(index_dataset, index=index_ids).to_pickle(dataframe_export_path)
    index_ids = None
    
    # Build and serialize fastText search index / build wordvec index for query labeling
    print('Building search index and wordvec index...')
    with open(ft_postvec_index, 'wb') as out:
        pickle.dump(build_search_index(fasttext_model_path, index_dataset, 'ft'), out)
    build_wordvec_index(ft_wordvec_file, ft_wordvec_index)
    
    # Build and serialize tfidf search index
    with open(tfidf_doc_vec_index, 'wb') as out:
        pickle.dump(build_search_index(tfidf_model_path, index_dataset, 'tfidf'), out)


if __name__ == '__main__':
    params_path = sys.argv[1]
    with open(params_path, 'r') as f:
        params = json.load(f)
    main(**params)
