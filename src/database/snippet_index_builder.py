#!/usr/bin/env python

import os
import sys
import sqlite3
import pandas as pd
from bs4 import BeautifulSoup
from collections import OrderedDict

file_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(file_path)
sys.path.append('..')
from api_extractor.api_extractor import APIExtractor

## Stack Overflow Attribution
so_attr = 'Code extracted from Stack Overflow'
user_attr = '\nUser: https://stackoverflow.com/users/'
post_attr = '\nPost: https://stackoverflow.com/questions/'

## Query
QID_INDEX = 0
ANSID_INDEX = 1
BODY_INDEX = 2
USERID_INDEX = 3
SCORE_INDEX = 4
ans_query = 'SELECT ParentId, Id, Body, OwnerUserId, Score FROM answers ORDER BY Score DESC'

def extract_snippets(row, api_extractor, tag_name='code'):
    snippet_list = []
    snippet_count = 0
    soup = BeautifulSoup(row[BODY_INDEX], 'lxml')
    for tag_html in soup.find_all(tag_name):
        tag_text = tag_html.getText()
        api_tokens, literals = api_extractor.extract_api_tokens(tag_text)
        if len(api_tokens) > 0:
            snippet_count += 1
            snippet_list.append(tag_text)
    if snippet_count > 0:
        attr = ''.join([so_attr, post_attr, str(row[ANSID_INDEX]), 
            user_attr, str(row[USERID_INDEX])]) 
        snippet_str = ''.join([attr, '\n##Score {}\n'.format(row[SCORE_INDEX]), 
            '<sdelim>'.join(snippet_list)])
        return snippet_count, snippet_str
    return 0, ''

def build_snippet_index(db_path):
    question_dict = OrderedDict()
    api_extractor = APIExtractor()
    java_db = sqlite3.connect(db_path)
    c = java_db.cursor()
    c.execute('SELECT COUNT(*) FROM answers')
    max_rows = c.fetchone()[0]
    c.execute(ans_query)
    for idx, row in enumerate(c):
        print('\rrow:', idx, '/', max_rows, end='')
        qid = row[0]
        snippet_count, snippet_str = extract_snippets(row, api_extractor)
        if qid not in question_dict:
            question_dict[qid] = {'SnippetCount': snippet_count, 'Snippets': snippet_str}
        else:
            if snippet_count > 0:
                prev_dict = question_dict[qid]
                new_count = prev_dict['SnippetCount'] + snippet_count
                new_str = '<pdelim>'.join([prev_dict['Snippets'], snippet_str])
                question_dict[qid] = {'SnippetCount': new_count, 'Snippets': new_str}
    api_extractor.close()
    return OrderedDict(sorted(question_dict.items()))

def insert_new_values(db_path):
    java_db = sqlite3.connect(db_path)
    c = java_db.cursor()

def main(db_path, export_path):
    snippet_df = pd.DataFrame.from_dict(build_snippet_index(db_path), orient='index')
    snippet_df.to_pickle(export_path)

if __name__ == '__main__':
    main('javaposts.db', 'snippet_index.pkl')
