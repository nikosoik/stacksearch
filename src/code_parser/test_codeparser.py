#!/usr/bin/env python

import os
from codeparser import CodeParser

testfiles = []
for filename in os.listdir("tests"):
    if filename.startswith("test"):
        testfiles.append(os.path.join('tests', filename))

## Test CodeParsing
parser = CodeParser(
    extract_sequence=False,
    keep_imports=False,
    keep_comments=False,
    keep_literals=False)

for test in testfiles:
    with open(test, 'r') as _in:
        code_snippet = _in.read()

    parsed_code = parser.parse_code(code_snippet)
    print(parsed_code)

parser.close()

## Test SequenceExtraction
parser = CodeParser(
    index_path='TEST_INDEX',
    extract_sequence=True,
    keep_imports=True,
    keep_comments=True,
    keep_literals=True,
    keep_unknown_method_calls=True)

for test in testfiles:
    with open(test, 'r') as _in:
        code_snippet = _in.read()

    sequence = parser.tokenize_sequence(code_snippet, True)
    print(sequence)

parser.close()
