import os
import json
import time

from wordvec_models.fasttext_model import FastTextSearch
from wordvec_models.tfidf_model import TfIdfSearch
from wordvec_models.hybrid_model import HybridSearch

from web_app import app
from flask import render_template, request, jsonify, make_response, Markup

from bs4 import BeautifulSoup

import pyastyle
from pygments import highlight
from pygments.lexers import JavaLexer
from pygments.formatters import HtmlFormatter

## Script directory
POST_HEADER = """
/** 
 * StackOverflow Post {}
 * Answer {}
 * Answer Score: {}
 */
 """

## Default Index Keys
# Valid keys depend on the index_builder output
# Possible keys could include BodyV, TitleV, TagV
index_keys = ['BodyV', 'TitleV']

## PATHS
FT_MODEL = "wordvec_models/fasttext_archive/ft_v0.6.1.bin"
FT_INDEX = "wordvec_models/index/ft_v0.6.1_post_index.pkl"
TFIDF_MODEL = "wordvec_models/tfidf_archive/tfidf_v0.3.pkl"
TFIDF_INDEX = "wordvec_models/index/tfidf_v0.3_post_index.pkl"
METADATA = "wordvec_models/index/extended_metadata.pkl"

## GLOBALS
model = None


def format_snippets(df):
    snippets = []
    for ii, row in enumerate(df.iterrows()):
        header = POST_HEADER.format(row[1].Link, row[1].sdict["anslink"],
                                    row[1].sdict["score"])
        s = format_code(header + row[1].sdict["snippet"])
        soup = BeautifulSoup(s, 'lxml')
        pre = soup.find('pre')
        if ii == 0:
            pre['id'] = 'cs1'
            pre['class'] = 'code-snippet active-cs'
        else:
            pre['id'] = 'cs' + str(ii + 1)
            pre['class'] = 'code-snippet'
        snippets.append(Markup(pre))

    return snippets


def format_code(text):
    fcode = pyastyle.format(text, "--style=java --delete-empty-lines")
    html_string = highlight(fcode, JavaLexer(),
                            HtmlFormatter(style='friendly'))
    return html_string


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    return render_template('base.html')


@app.route('/check_status', methods=['GET'])
def check_status():
    global model
    model_name = model.name if model else "No"
    model_select = model.name if model else "hybrid"
    return jsonify(model=model_name, model_select=model_select)


@app.route('/load_model', methods=['GET'])
def load_model():
    global model
    model_type = request.args.get('model_type', 'hybrid', type=str)
    if model_type == 'fasttext':
        model = FastTextSearch(model_path=FT_MODEL,
                               index_path=FT_INDEX,
                               index_keys=index_keys,
                               metadata_path=METADATA)
    elif model_type == 'tf-idf':
        model = TfIdfSearch(model_path=TFIDF_MODEL,
                            index_path=TFIDF_INDEX,
                            index_keys=index_keys,
                            metadata_path=METADATA)
    elif model_type == 'hybrid':
        model = HybridSearch(ft_model_path=FT_MODEL,
                             ft_index_path=FT_INDEX,
                             tfidf_model_path=TFIDF_MODEL,
                             tfidf_index_path=TFIDF_INDEX,
                             index_keys=index_keys,
                             metadata_path=METADATA)
    return jsonify(success=True, model=model_type)


@app.route('/search', methods=['POST'])
def search():
    global model
    json_data = request.get_json(force=True)
    mt_df, top_tags = model.search(query=json_data['query'],
                                   tags=json_data['tags'],
                                   num_results=10)
    snippets_html = format_snippets(mt_df)
    pagination = list(range(2, len(snippets_html) + 1))
    return jsonify({
        'data':
        render_template('results.html',
                        results=snippets_html,
                        tags=top_tags,
                        pagination=pagination)
    })
