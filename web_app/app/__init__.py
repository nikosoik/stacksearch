from flask import Flask

app = Flask(__name__)

import pyastyle
from app import routes
from pygments import highlight
from pygments.lexers import JavaLexer
from pygments.formatters import HtmlFormatter

def format_code(text):
    fcode = pyastyle.format(text, "--style=java --delete-empty-lines")
    html_string = highlight(fcode, JavaLexer(), HtmlFormatter(style='friendly'))
    return html_string

print(__name__)
app.run('0.0.0.0', 5080, debug=False)
