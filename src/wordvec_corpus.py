#!/usr/bin/env python

import os
import sqlite3
import pandas as pd

from preprocessing.text_eval import eval_text
from api_extractor.api_extractor import APIExtractor
from post_classifier.classifier import PostClassifier
from post_classifier.vectorize import Vectorizer, load_dict
from post_classifier.utilities import load_text_list, load_number_list, remove_rows, list_to_disk

from preprocessing.preprocessing import process_corpus

# query settings
score_threshold = -3
ans_count_threshold = 1

QUESTION_QUERY = '''SELECT Id, Body, Title, Tags FROM questions 
        WHERE AnswerCount>={ans_count} 
        AND Score>={score} ORDER BY Id ASC'''
q1 = QUESTION_QUERY.format(ans_count=ans_count_threshold, score=score_threshold)

ANSWER_QUERY = '''SELECT Id, Body, ParentId FROM answers
        WHERE ParentId IN {id_list} ORDER BY ParentId ASC'''
COMMENT_QUERY = '''SELECT Id, Text FROM comments
        WHERE PostId IN {id_list} ORDER BY PostId ASC'''
        
class DBPostCleaner:
    def __init__(self, classifier_path, dictionary_path, database_path, text_eval_fn):
        self.clsfr = PostClassifier(classifier_path)
        self.vectorizer = Vectorizer(load_dict(dictionary_path))
        self.db_conn = sqlite3.connect(database_path)
        self.eval_text = text_eval_fn
    
    def filter_list(self, posts, predictions):
        """
        Using a label list of booleans filter out posts
        """
        labels = predictions
        if isinstance(predictions, str):
            labels = load_number_list(predictions, mode='bool')
        if isinstance(posts, str):
            posts = load_text_list(posts)
        return remove_rows(posts, labels)

    def clsfr_clean(self, posts, post_ids, export_dir, identifier):
        dump_path = os.path.join(export_dir, identifier)
        pred_path = dump_path + '_predictions'
        if isinstance(posts, str):
            posts = load_text_list(posts)
            post_ids = load_text_list(post_ids)
        vectorized_doc = self.vectorizer.vectorize_list(posts)
        with open(pred_path, 'a') as pred_out:
            for batch in self.clsfr.feed_data(vectorized_doc):
                self.clsfr.save_predictions(pred_out, self.clsfr.make_prediction(batch))
        labels = load_number_list(pred_path, mode='bool')
        df = pd.DataFrame(remove_rows(posts, labels), index=remove_rows(post_ids, labels))
        df.to_pickle(dump_path + '.pkl')

    def get_posts(self, query, api_index_path, identifier):
        api_ex = APIExtractor(index_path=api_index_path)
        c = self.db_conn.cursor()
        c.execute(query)
        posts, ids, parentIds = ([] for i in range(3))
        # Formating posts and discarding low quality posts (lots of punctuation etc.)
        for idx, row in enumerate(c):
            print('\rpost:', idx, end='')
            post = ''
            if identifier == 'q':
                post = row[2] + ' ' + row[1] # title + body
            else:
                post = row[1].replace('`', '') # replace quote char from comments
            eval_res = self.eval_text(post, api_ex)
            if eval_res != -1:
                posts.append(eval_res)
                ids.append(row[0])
                if identifier == 'ans':
                    parentIds.append(row[2])
        print()
        api_ex.close()
        return posts, ids, parentIds

def retrieve_posts(pcleaner, query, export_dir, identifier):
    dpath = os.path.join(export_dir, identifier)
    api_index_path = os.path.join(export_dir, 'api_index')
    posts, ids, parentIds = pcleaner.get_posts(query, api_index_path, identifier)
    list_to_disk(dpath, posts)
    list_to_disk(dpath + '_ids', ids)
    if identifier == 'ans':
        list_to_disk(dpath + '_parentIds', parentIds)

def main(classifier_path, dictionary_path, database_path, export_dir):
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    # Paths
    qdump_path = os.path.join(export_dir, 'q')
    clean_q_path = qdump_path + '_clean'
    adump_path = os.path.join(export_dir, 'ans')
    clean_ans_path = adump_path + '_clean'
    # DBPostCleaner
    pcleaner = DBPostCleaner(classifier_path, dictionary_path, database_path, eval_text)
    # Questions Retrieval
    # Questions 1st and 2nd pass
    retrieve_posts(pcleaner, q1, export_dir, 'q')
    pcleaner.clsfr_clean(qdump_path, qdump_path + '_ids', export_dir, 'q')

    # Answers Retrieval
    qid_list = str(tuple(load_text_list(clean_q_path + '_ids')))
    q2 = ANSWER_QUERY.format(id_list=qid_list)
    qid_list = None
    # Answers 1st ans 2nd pass
    retrieve_posts(pcleaner, q2, export_dir, 'ans')
    pcleaner.clsfr_clean(adump_path, adump_path + '_ids', export_dir, 'ans')
    
    # Comment Retrieval / Just 1st pass
    postid_list = str(tuple(load_text_list(clean_q_path + '_ids') + 
                            load_text_list(clean_ans_path + '_ids')))
    q3 = COMMENT_QUERY.format(id_list=postid_list)
    retrieve_posts(pcleaner, q3, export_dir, 'com')

if __name__ == '__main__':
    clsfr_path = 'classifier/models/c-lstm_v1.0.hdf5'
    dict_path = 'classifier/data/token_dictionary.json'
    db_path = 'database/javaposts.db'
    export_folder = 'data'
    db_corpus = os.path.join(export_folder, 'corpus')
    '''
    main(clsfr_path, dict_path, db_path, export_folder)
    '''
    # tokenize and normalize corpus (prepare for word vector training)
    corpus_export_dir = 'wordvec_model/train_data'
    if not os.path.exists(corpus_export_dir):
        os.makedirs(corpus_export_dir)
    process_corpus(db_corpus, os.path.join(corpus_export_dir, 'corpus'))
