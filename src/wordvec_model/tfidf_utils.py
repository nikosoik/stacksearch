import os
import sys
import json
import pickle
import argparse
import numpy as np
import pandas as pd
from scipy import sparse
from tabulate import tabulate
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

file_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(file_path)

## StackOverflow Base URL
base_url = 'https://stackoverflow.com/questions/'

# every token consists of two or more non whitespace characters
TOKEN_RE = r'\S\S+'

def load_text_list(filename):
    """Returns a list of strings."""
    text_list = []
    with open(filename, 'r') as f:
        for line in f:
            text_list.append(line.strip())
    return text_list

def load_metadata(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def load_model(model_path):
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    return model

def load_model_n_vectors(model_path, vec_path):
    """Utility function that loads the tf-idf model and train vectors
    """
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    vecs = sparse.load_npz(vec_path)
    return model, vecs

def train_tfidf_model(post_list, model_export_path, vec_export_path):
    tfidf = TfidfVectorizer(token_pattern=TOKEN_RE, preprocessor=None, 
                        tokenizer=None, stop_words='english', smooth_idf=True)
    tfidf_matrix = tfidf.fit_transform(post_list)
    sparse.save_npz(vec_export_path, tfidf_matrix)
    with open(model_export_path, 'wb') as out:
        pickle.dump(tfidf, out)
    return tfidf

def build_doc_vectors(model, doc, export_path=None):
    """Calculates sentence vectors using the provided pre-trained tf-idf model
    """
    vec_matrix = None
    if isinstance(doc, str):
        if os.path.exists(doc):
            doc = load_text_list(doc)
            vec_matrix = model.transform(doc)
        else:
            raise ValueError('Provided document path  {} doesn\'t exist.'.format(doc))
    elif isinstance(doc, list):
        vec_matrix = model.transform(doc)
    else:
        raise ValueError('Invalid "doc" variable type {}.'.format(str(type(doc))))
    if export_path:
        sparse.save_npz(export_path, vec_matrix)
        print('\ntfidf doc vectors saved in', os.path.realpath(export_path))
    return vec_matrix

def topn_similar(cossims, k):
    """Sorts the given vector in asc order and returns the indices of the 
    first k elements.
    """
    return np.argsort(cossims)[:k]

def ranking(model, query, index, title_weight, k=20):
    """Calculates the cosine similarities between the query vector and each
    document vector and returns the k most similar post ids.
    """
    cossims = None
    query_vec = model.transform([query.lower().strip()])
    if title_weight:
        cossims = (-cosine_similarity(query_vec, index['BodyVectors'])[0] 
            -cosine_similarity(query_vec, index['TitleVectors'])[0])/2
    else:
        cossims = -cosine_similarity(query_vec, index['BodyVectors'])[0]
    indices = topn_similar(cossims, k)
    sim_values = [-cossims[i] for i in indices]
    return indices, sim_values

def metadata_frame(metadata, indices, sim_values):
    postids = [metadata[i]['PostId'] for i in indices]
    df_dict = {
        'Title': [metadata[i]['Title'] for i in indices],
        'PostId': postids,
        'Sim': [round(s, 4) for s in sim_values],
        'Link': [(base_url + str(_id)) for _id in postids]
    }
    return pd.DataFrame(df_dict)

def query_posts(model_path, index_path, metadata, title_weight=True, 
                                            num_results=20, custom_fn=None):
    if isinstance(metadata, str):
        if os.path.exists(metadata):
            metadata = load_metadata(metadata)
        else:
            raise ValueError('Provided document path  {} doesn\'t exist.'.format(doc))
    with open(index_path, 'rb') as f:
        tfidf_index = pickle.load(f)
    tfidf = load_model(model_path)
    while(True):
        query = input('Query? ')
        if query == 'exit':
            break
        indices, sim_values = ranking(tfidf, query, tfidf_index, 
            title_weight, num_results)
        meta_df = metadata_frame(metadata, indices, sim_values)
        str_out = tabulate(meta_df, showindex=False, headers=meta_df.columns)
        print(str_out, end='\n\n')
        if custom_fn is not None:
            custom_fn(list(df['PostId']))
