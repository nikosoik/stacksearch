import re
import javalang
from collections import OrderedDict
from javalang.parse import parse, parse_expression
from javalang.tree import MethodInvocation, ClassDeclaration, Import

EXCLUDE_METHODS = ['println', 'printStackTrace']

# regular expressions
SUB_PATTERN = re.compile(r'//|/\*|\*/|\*')

COMMENT_PATTERN = re.compile((
    # End of line comment
    r'(?<!:)//.*(?=\n)'
    r'|'
    # JavaDoc comment
    r'(/\*\*([^\*]|\*(?!/))*(?=\*/))'
    r'|'
    # Multi-line comment
    r'(/\*([^\*]|\*(?!/))*\*/)'
).strip())

IMPORT_PATTERN = re.compile((   
    r'^import '
    r'(com|org|java|javax)\.'
    r'([a-zA-Z_$][a-zA-Z0-9_$]*\.)+[a-zA-Z_$][a-zA-Z0-9_$]*'
).strip())

API_PATTERN = re.compile(r'((?:[a-zA-Z_$][a-zA-Z0-9_$]*\.)+[a-zA-Z_$][a-zA-Z0-9_$]*)\(')

def extract_commment_content(snippet):
    # Extracts and returns java comments (javadoc, multiline, plain) from snippet.
    comments = ''
    for match in COMMENT_PATTERN.finditer(snippet):
        comments += ' '.join(SUB_PATTERN.sub('', match.group(0)).split()) + ' '
    return comments

def extract_api_tokens_from_class(snippet):
    # Builds AST from snippet.
    # Returns all MethodInvocations and Imports.
    imports = []
    api_tokens = []
    try:
        tree = parse(snippet)
        for _, node in tree:
            if type(node) == Import:
                imports.append(node.path)
            elif type(node) == MethodInvocation and node.member not in EXCLUDE_METHODS:
                api_tokens.append(node.member)
    except Exception as err:
        pass
    return api_tokens, imports

def extract_api_tokens_from_string(snippet):
    """
    Extract api tokens and imports from the given snippet when 
    it's not wrapped in a formal class declaration.
    :param snippet: The snippet to have its api tokens extracted
    :return: List of the api tokens names
    """
    slices = re.split(r'''{|}|;|=|if \(|while \(|for \(|if |while |for ''', snippet)
    slices = [el.strip() for el in slices]
    imports = []
    api_tokens = []
    for s in slices:
        try:
            if IMPORT_PATTERN.match(s):
                imports.append(s[7:])
            else:
                node = parse_expression(s)
                if type(node) == MethodInvocation:
                    if node.member not in EXCLUDE_METHODS:
                        api_tokens.append(node.member)
                    """
                    inner = list(API_PATTERN.findall(s[node.position[1]:]))
                    for api_call in inner:
                        if 'print' not in api_call:
                            api_tokens.append(api_call)
                    """
        except Exception as err:
            pass
    return api_tokens, imports

def extract_api_info(snippet, keep_jlang_tokens=True):
    api_tokens, imports = extract_api_tokens_from_class(snippet)
    if len(api_tokens) == 0:
        api_tokens, imports = extract_api_tokens_from_string(snippet)
    api_tokens = list(OrderedDict.fromkeys(api_tokens))
    comments = extract_commment_content(snippet)
    if keep_jlang_tokens:
        return imports + api_tokens, comments
    else:
        return imports, comments