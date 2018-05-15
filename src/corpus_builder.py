#!/usr/bin/env python

import os
import pickle
import sqlite3
import pandas as pd

from code_parser.codeparser import CodeParser
from post_classifier.classifier import PostClassifier
from post_classifier.utils import (list_to_disk, load_number_list,
                                   load_text_list, remove_rows)
from post_classifier.vectorizer import Vectorizer
from preprocessing.text_eval import eval_text
from preprocessing.utils import process_corpus

## Question query default settings
score_threshold = -3
ans_count_threshold = 1

## Database Queries
INIT_QUESTION_QUERY = '''SELECT Body, Id FROM questions
    WHERE AnswerCount>={ans_count} AND Score>={score} ORDER BY Id ASC'''
INIT_ANSWER_QUERY = '''SELECT Body, Id FROM answers
    WHERE ParentId IN {id_list} ORDER BY ParentId ASC'''
INIT_COMMENT_QUERY = '''SELECT Text AS Body, Id FROM comments
    WHERE PostId IN {id_list} ORDER BY PostId ASC'''

FINAL_QUESTION_QUERY = '''SELECT Id, Title, Tags, Score FROM questions
    WHERE Id IN {id_list} ORDER BY Id ASC'''
FINAL_ANSWER_QUERY = '''SELECT Id, ParentId, Score FROM answers
    WHERE Id IN {id_list} ORDER BY ParentId ASC'''
FINAL_COMMENT_QUERY = '''SELECT Id, PostId FROM comments
    WHERE Id IN {id_list} ORDER BY PostId ASC'''


class CorpusBuilder:
    def __init__(self,
                 classifier_path,
                 vectorizer_dict_path,
                 database_path,
                 export_dir,
                 text_eval_fn,
                 qparams=None):

        self.classifier = PostClassifier(classifier_path)
        self.vectorizer = Vectorizer(dictionary_path=vectorizer_dict_path)
        self.db_conn = sqlite3.connect(database_path)
        self.text_eval_fn = text_eval_fn

        if qparams:
            self.qparams = qparams

        ## Create paths
        self.export_dir = export_dir
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        self.init_dfs = {
            'q': os.path.join(export_dir, 'init_q_posts'),
            'a': os.path.join(export_dir, 'init_a_posts'),
            'c': os.path.join(export_dir, 'init_c_posts')
        }
        self.final_dfs = {
            'q': os.path.join(export_dir, 'final_q_posts'),
            'a': os.path.join(export_dir, 'final_a_posts'),
            'c': os.path.join(export_dir, 'final_c_posts')
        }

    def _retrieve_db_data(self, query, post_type, eval_posts=True):
        c = self.db_conn.cursor()
        c.execute(query)
        cols = [d[0] for d in c.description]
        output_dict = {key: [] for key in cols}

        if eval_posts:
            codeparser = CodeParser(
                index_path=os.path.join(self.export_dir, 'api_index'),
                extract_sequence=True,
                keep_imports=False,
                keep_comments=True,
                keep_literals=True,
                keep_unknown_method_calls=False)
            ## Format posts and discard low quality posts (excess punctuation)
            for idx, row in enumerate(c):
                print('\rpost:', idx, end='')
                body = row[0]
                if post_type == 'com':  # replace quote char from comments
                    body = body.replace('`', ' ')
                eval_res = self.text_eval_fn(body, codeparser)
                if eval_res != -1:
                    output_dict[cols[0]].append(eval_res)
                    for ii, val in enumerate(row[1:], start=1):
                        output_dict[cols[ii]].append(val)
            codeparser.close()
        else:
            for idx, row in enumerate(c):
                print('\rpost:', idx, end='')
                for ii, val in enumerate(row):
                    output_dict[cols[ii]].append(val)
        print()
        return output_dict

    def _filter_posts(self, posts, post_ids, post_type):
        ## Load lists from disk if given a path
        if isinstance(posts, str):
            posts = load_text_list(posts)
        if isinstance(post_ids, str):
            post_ids = load_text_list(post_ids)

        ## Create dump paths
        predictions_path = self.init_dfs[post_type] + '_predictions'

        ## Vectorize posts and get classifier predictions
        vectorized_doc = self.vectorizer.vectorize_list(posts)
        with open(predictions_path, 'a') as pred_out:
            for batch in self.classifier.feed_data(vectorized_doc):
                self.classifier.save_predictions(
                    pred_out, self.classifier.make_prediction(batch))

        ## Filter out 'unclean' posts using the predictions
        labels = load_number_list(predictions_path, mode='bool')
        df = pd.DataFrame(
            data={'Body': remove_rows(posts, labels)},
            index=remove_rows(post_ids, labels))

        if post_type == 'q':
            self.qid_list = list(df.index)
        else:
            self.ansid_list = list(df.index)

        # Save dataframe to disk
        df.to_pickle(self.init_dfs[post_type])

    def _build_initial_dataframe(self, query, post_type):
        db_data = self._retrieve_db_data(query, post_type)
        with open('temp_file_' + post_type, 'wb') as out:  ## safety save
            pickle.dump(out, db_data)
        if post_type != 'c':  # skip classifier stage for comments
            self._filter_posts(db_data['Body'], db_data['Id'], post_type)
        elif post_type == 'c':
            pd.DataFrame(
                data={'Body': db_data['Body']},
                index=db_data['Id']).to_pickle(self.init_dfs['c'])

    def _build_final_dataframe(self, query, post_type):
        def validate_data(original_ids, data_ids):
            if len(original_ids) != len(data_ids):
                raise ValueError('Validation failed. Ids mismatch.')
            for idx, _id in enumerate(original_ids):
                if _id != data_ids[idx]:
                    raise ValueError('Validation failed. Ids mismatch.')

        init_df = pd.read_pickle(self.init_dfs[post_type])
        df_index = list(init_df.index)
        df_dict = {'Body': list(init_df['Body'])}
        del init_df
        db_data = self._retrieve_db_data(query, post_type, False)
        validate_data(df_index, db_data['Id']) # sanity check
        del db_data['Id']
        df_dict.update(db_data)
        final_df = pd.DataFrame(data=df_dict, index=df_index)
        final_df.to_pickle(self.final_dfs[post_type])

    def build_initial_dataframes(self):
        query = INIT_QUESTION_QUERY.format(
            ans_count=ans_count_threshold, score=score_threshold)
        if self.qparams:
            query = INIT_QUESTION_QUERY.format(**self.qparams)
        self._build_initial_dataframe(query, 'q')

        query = INIT_ANSWER_QUERY.format(id_list=str(tuple(self.qid_list)))
        self._build_initial_dataframe(query, 'a')

        query = INIT_COMMENT_QUERY.format(
            id_list=str(tuple(self.qid_list + self.ansid_list)))
        self._build_initial_dataframe(query, 'c')

    def build_final_dataframes(self):
        query = FINAL_QUESTION_QUERY.format(str(tuple(self.qid_list)))
        self._build_final_dataframe(query, 'q')
        query = FINAL_ANSWER_QUERY.format(str(tuple(self.ansid_list)))
        self._build_final_dataframe(query, 'a')
        query = FINAL_COMMENT_QUERY.format(
            str(tuple(self.qid_list + self.ansid_list)))
        self._build_final_dataframe(query, 'c')

    def build_corpus(self, process=True):  ## TODO: include_comments=False,
        text_list = []
        qdf = pd.read_pickle(self.final_dfs['q'])
        qids = list(qdf.index)
        qposts = list(qdf['Body'])
        qtitles = list(qdf['Title'])
        del qdf  # free memory

        ansdf = pd.read_pickle(self.final_dfs['a'])
        for idx, qid in enumerate(qids):
            text_list.append(qtitles[idx])
            text_list.append(qposts[idx])
            text_list.extend(list(ansdf.loc[ansdf['ParentId'] == qid, 'Body']))

        corpus_path = os.path.join(self.export_dir, 'init_corpus')
        list_to_disk(corpus_path, text_list)

        if process:
            final_corpus_path = os.path.join(self.export_dir, 'final_corpus')
            process_corpus(corpus_path, final_corpus_path, True)


def main(classifier_path,
         vectorizer_dict_path,
         database_path,
         export_dir,
         text_eval_fn,
         qparams=None):

    corpus_builder = CorpusBuilder(classifier_path, vectorizer_dict_path,
                                   database_path, export_dir, text_eval_fn,
                                   qparams)
    corpus_builder.build_initial_dataframes()
    corpus_builder.build_final_dataframes()
    corpus_builder.build_corpus()


if __name__ == '__main__':
    main('classifier/models/c-lstm_v1.0.hdf5',
         'classifier/data/token_dictionary.json', 'database/javaposts.db',
         'data', eval_text)
