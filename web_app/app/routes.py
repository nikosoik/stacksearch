import json

from app import app
from flask import render_template, request, jsonify, make_response

from bs4 import BeautifulSoup
import time

import pyastyle
from pygments import highlight
from pygments.lexers import JavaLexer
from pygments.formatters import HtmlFormatter

def format_code(text):
    fcode = pyastyle.format(text, "--style=java --delete-empty-lines")
    html_string = highlight(fcode, JavaLexer(), HtmlFormatter(style='friendly'))
    return html_string

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@app.route('/load_model', methods=['GET'])
def load_model():
    model_type = request.args.get('model_type', 'hybrid', type=str)
    print(model_type)
    time.sleep(2)
    return jsonify(success=True, model=model_type)


@app.route('/search', methods=['POST'])
def search():
    with open('/run/media/ncode/Data/stacksearch/web_app/app/test_posts.json', 'r') as f:
        snippets = json.load(f)
    snippets = [snippets['1'], snippets['2']]
    snippets = [format_code(s) for s in snippets]
    snippets_html = []
    for ii, s in enumerate(snippets):
        soup = BeautifulSoup(s, 'lxml')
        pre = soup.find('pre')
        if ii == 0:
            pre['class'] = 'active-code'
        snippets_html.append(pre)
    num = 2
    tags = ['csvreader', 'linux', 'tostring']

    results = {'snippets_html': snippets_html, 'tags': tags, 'num': num}
    json_data = request.get_json(force=True)
    print(json_data)
    return jsonify({'data': render_template('results.html', results=results)})
