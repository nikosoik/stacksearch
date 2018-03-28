import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
import scipy.spatial.distance
from tabulate import tabulate
from fastText import load_model
from sklearn.feature_extraction.text import TfidfVectorizer

file_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(file_path)

## StackOverflow Base URL
base_url = 'https://stackoverflow.com/questions/'

## Error Strings
cw_sum_error = '"custom_weights" array elements must have a sum of 1.'
cw_num_el_error = '"custom_weights" array must be of length {}.'
cw_type_error = '"custom_weights" variable must be of type ndarray.'

doc_path_error = 'Provided document path doesn\'t exist.'
doc_type_error = 'Invalid "doc" variable type {}. Expected str(path) or list.'

class TfidfWeightedVectorizer:
    """

    """

    def __init__(self, wordvec_index, wordweight_index=None):
        self.wordvec_index = wordvec_index
        self.wordweight_index = wordweight_index
        self.dim = len(wordvec_index.values[0])
        self.defaultdict_val = None

    def fit(self, documents):
        """
        Calculates the word-vector weights by fitting a TfidfVectorizer
        on a given iterable of documents.
        """
        # spliting strings on space considering the input docs 
        # are already tokenized and the tokens space seperated
        tfidf = TfidfVectorizer(analyzer=lambda x: x.split())
        tfidf.fit(documents)
        # if a word was never seen - it must be at least as infrequent
        # as any of the known words - so the default idf is the max of 
        # known idf's
        idf_vector = tfidf.idf_
        vocab = tfidf.vocabulary_.items()
        self.defaultdict_val = max(idf_vector)
        self.wordweight_index = dict([(w, idf_vector[i]) for w, i in vocab])
        
    def transform(self, documents):
        """
        Transforms an iterable of documents into a document-vector matrix.
        """
        doc_vecs = np.zeros([len(documents), self.dim])
        for idx, doc in enumerate(documents):
            #print('\rcalculating vector for line #', idx, end='')
            doc_vecs[idx] = np.mean([np.array(self.wordvec_index.loc[w]) * 
                self.wordweight_index.get(w, self.defaultdict_val) 
                for w in doc.split() if w in self.wordvec_index.index] or 
                [np.zeros(self.dim)], axis=0)
        return doc_vecs

class FastTextSearch:
    def __init__(self, model_path, index_path, index_keys, 
                        metadata_path, wordvec_index_path=None, api_dict_path=None):
        self.model = load_model(model_path)
        print('FastText model {} loaded.'.format(os.path.basename(model_path)))

        self.index = self.read_pickle(index_path)
        for key in list(self.index.keys()):
            if key not in index_keys:
                del self.index[key]
        
        self.num_index_keys = len(self.index)
        self.index_size = len(next (iter (self.index.values())))
        print('Index keys used:', ', '.join(self.index.keys()), end='\n\n')
        
        self.metadata = self.read_json(metadata_path)
        self.wv_index = None
        self.api_dict = None
        if api_dict_path:
            self.api_dict = self.read_pickle(api_dict_path)

    def read_pickle(self, filepath):
        with open(filepath, 'rb') as _in:
            return pickle.load(_in)

    def read_json(self, filepath):
        with open(filepath, 'rb') as f:
            return json.load(f)

    def infer_vector(self, text):
        return self.model.get_sentence_vector(text.lower().strip())
        
    def get_cossims(self, vector, matrix, batch_calc=True, batch_size=100000):
        """Given a query vector, compute the cosine similarities between said vector
        and each row of the provided matrix of document vectors.

        Args:
            batch_calc: Reduces memory usage by calculating similarities in batches.
            batch_size: The size of each batch used when batch_calc is True.

        Returns:
            A numpy array containing the values of the cosine similarities.
        """

        def batch_cossims(vector, matrix, batch_size=100000):
            mat_len = len(matrix)
            if mat_len > batch_size:
                n_batches = round(mat_len/batch_size)
                matrix = np.array_split(matrix, n_batches)
            for batch in matrix:
                    yield scipy.spatial.distance.cdist(
                        vector, batch, 'cosine').reshape(-1)
        
        vector = vector.reshape(1, -1)
        if batch_calc:
            istart = 0
            cossims = np.zeros(len(matrix), dtype=matrix.dtype)
            for batch_vec in batch_cossims(vector, matrix, batch_size):
                cossims[istart:(istart + len(batch_vec))] = batch_vec
                istart = istart + len(batch_vec)
            return cossims
        else:
            return scipy.spatial.distance.cdist(vector, matrix, 'cosine').reshape(-1)

    def get_labels(self, query_vec, search_depth=1400, max_n=10):
        """Return the most similar labels to the given query vector.
        Calculates all cosine similarities between each word vector and the query 
        vector and returns the most similar word-labels found in the given api dictionary.
        """
        sims = self.get_cossims(query_vec, self.wv_index.values, batch_calc=False)
        indices = np.argsort(sims)[:search_depth]
        index_vals = list(self.wv_index.index[indices])
        labels = [val for val in index_vals if val in self.api_dict]
        return labels[:max_n]

    def ranking(self, query_vec, num_results, custom_weights=None):
        sims = np.zeros([self.index_size], dtype='float32')
        if custom_weights:
            for idx, index_matrix in enumerate(self.index.values()):
                sims += self.get_cossims(query_vec, index_matrix) * custom_weights[idx]
        else:
            for index_matrix in self.index.values():
                sims += self.get_cossims(query_vec, index_matrix)
            sims = sims / self.num_index_keys
        indices = np.argsort(sims)[:num_results]
        sim_values = [(1 - sims[i]) for i in indices]
        return indices, sim_values

    def metadata_frame(self, indices, sim_values):
        postids = [self.metadata[i]['PostId'] for i in indices]
        df_dict = {
            'Title': [self.metadata[i]['Title'] for i in indices],
            'PostId': postids,
            'Sim': [round(s, 4) for s in sim_values],
            'Link': [(base_url + str(_id)) for _id in postids]
        }
        return pd.DataFrame(df_dict)

    def search(self, num_results=20, custom_weights=None, 
                                            api_labels=False, custom_fn=None):
        def check_custom_weights(custom_weights):
            if isinstance(custom_weights, np.ndarray):
                if len(custom_weights) == self.num_index_keys:
                    if custom_weights.sum() == 1:
                        return custom_weights
                    else:
                        raise ValueError(cw_sum_error)
                else:
                    raise ValueError(cw_num_el_error.format(self.num_index_keys))
            else:
                raise TypeError(cw_type_error)

        if custom_weights:
            custom_weights = check_custom_weights(custom_weights)
        while(True):
            query = input('Query? ')
            if query == 'exit':
                break
            query_vec = self.infer_vector(query)
            indices, sim_values = self.ranking(query_vec, num_results, custom_weights)
            meta_df = self.metadata_frame(indices, sim_values)
            str_out = tabulate(meta_df, showindex=False, headers=meta_df.columns)
            if self.api_dict and api_labels:
                print(self.get_labels(query_vec), end='\n\n')
            print(str_out, end='\n\n')
            if custom_fn is not None:
                custom_fn(list(meta_df['PostId']))

def build_doc_vectors(model, doc, export_path=None):
    """
    Expected input is a preprocessed document.
    Calculates sentence vectors using the built-in fastText function which
    averages the word-vector norms of all the words in the given sentence.
    """
    vector_matrix = []
    if isinstance(doc, str):
        if os.path.exists(doc):
            with open(doc, 'r') as doc_file:
                for idx, line in enumerate(doc_file):
                    print('\rcalculating vector for line #', idx, end='')
                    vector_matrix.append(model.get_sentence_vector(str(line.strip())))
        else:
            raise ValueError(doc_path_error)
    elif isinstance(doc, list):
        for idx, line in enumerate(doc):
            print('\rcalculating vector for line #', idx, end='')
            vector_matrix.append(model.get_sentence_vector(str(line.strip())))
        print()
    else:
        raise TypeError(doc_type_error.format(type(doc)))
    vector_matrix = np.array(vector_matrix)
    if export_path:
        np.save(export_path, vector_matrix)
        print('\nfasttext doc vectors saved in', os.path.realpath(export_path))
    return vector_matrix

def build_wordvec_index(vec_filename, export_path):
    """Given a fastText vector file, output word vectors into a DataFrame where
    key: word token (string), value: word vector (numpy array).
    NOTE: First row in a fastText vector file holds the number of tokens and 
    vector length.
    """
    with open(vec_filename, 'r') as vec_file:
        dimensions = [int(dim) for dim in vec_file.readline().split()]
        print('\nwordvec matrix dimensions:', dimensions)
        vec_matrix = np.zeros(dimensions, dtype='float32')
        index_tokens = []
        for idx, row in enumerate(vec_file):
            token, vector = row.split(' ', 1)
            vec_matrix[idx] = np.fromstring(vector, sep=' ')
            index_tokens.append(token)
    pd.DataFrame(data=vec_matrix, index=index_tokens).to_pickle(export_path)
    print('wordvec index saved in', os.path.realpath(export_path))
