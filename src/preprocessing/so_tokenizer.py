import re
import spacy
import string
import unicodedata
from spacy import util
from spacy.tokens import Token
from spacy.tokenizer import Tokenizer
from spacy.symbols import ORTH, LEMMA, NORM

# https://github.com/explosion/spaCy/blob/master/spacy/lang/tokenizer_exceptions.py
# removed the section regarding query parameters because it caused problems when
# tokenizing api calls
URL_PATTERN = (
    r"^"
    # in order to support the prefix tokenization (see prefix test cases in test_urls).
    r"(?=[\w])"
    # protocol identifier
    r"(?:(?:https?|ftp|mailto)://)?"
    # user:pass authentication
    r"(?:\S+(?::\S*)?@)?"
    r"(?:"
    # IP address exclusion
    # private & local networks
    r"(?!(?:10|127)(?:\.\d{1,3}){3})"
    r"(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})"
    r"(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})"
    # IP address dotted notation octets
    # excludes loopback network 0.0.0.0
    # excludes reserved space >= 224.0.0.0
    # excludes network & broadcast addresses
    # (first & last IP address of each class)
    # MH: Do we really need this? Seems excessive, and seems to have caused
    # Issue #957
    r"(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])"
    r"(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}"
    r"(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))"
    r"|"
    # host name
    r"(?:(?:[a-z0-9\-]*)?[a-z0-9]+)"
    # domain name
    r"(?:\.(?:[a-z0-9\-])*[a-z0-9]+)*"
    # TLD identifier
    r"(?:\.(?:[a-z]{2,}))"
    r")"
    # port number
    r"(?::\d{2,5})?"
    # resource path
    r"(?:/\S*)?"
    # query parameters
    #r"\??(:?\S*)?" commented out because it interferes with the api protection regex
    # in order to support the suffix tokenization (see suffix test cases in test_urls),
    r"(?<=[\w/])"
    r"$"
).strip()

API_PATTERN = (
    # package.method invocation
    r'([a-zA-Z_$][a-zA-Z0-9_$]*\.)+[a-zA-Z_$][a-zA-Z0-9_$]*(\(\))?$'
    r'|'
    # direct method invocation
    r'[a-zA-Z_$][a-zA-Z0-9_$]*\(\)$'
    r'|'
    # programming operators
    r'==|!=|>=|<=|&&|\|\|'
    r'|'
    r'\.[Nn][Ee][Tt]$|[Cc]#$|[Cc]\+\+$' #.net, c#, c++
).strip()

BASIC_URL = r'(?:(?:https?|ftp|mailto|file)://)\S*'
# combined regex of API_PATTERN & URL_PATTERN that protects matched tokens from spliting
_protect = re.compile(API_PATTERN + r'|' + URL_PATTERN + r'|' + BASIC_URL)

# regex for api and method invocations based on the Java guidelines for identifiers
_api_invoc = [
    r'([a-zA-Z_$][a-zA-Z0-9_$]*\.)+[a-zA-Z_$][a-zA-Z0-9_$]*(\(\))?',
    r'[a-zA-Z_$][a-zA-Z0-9_$]*\(\)',
    #r'[a-zA-Z_$][a-zA-Z0-9_$]{3,}<[^>]*>'
]

# regex matching hashtags
_hashtags = [r'#[a-zA-Z0-9_]+']

# var regex
_var = [r'\d+%$']

def so_tokenizer(nlp):
    # add '\.|-|~' and remove '#' (default prefixes list)
    _prefixes = list(nlp.Defaults.prefixes) + [r'^\.|^~|^-(?=\S)']
    del _prefixes[22]
    # add '\.' and remove '#' (default suffixes list)
    # add _api_calls regex
    _suffixes = list(nlp.Defaults.suffixes) + _api_invoc + _var + [r'\.$']
    del _suffixes[18]
    # add '\(|\[' to split nested api calls, arrays etc (default infixes list)
    # add _hashtags regex
    _infixes = list(nlp.Defaults.infixes) + _hashtags + [r'\(|\)|\[|\]|\{|\}|<|>|,|=|\+|-|:|;|\'|\"|\/|&|\?']
    # setup each regex using native spaCy util functions
    prefix_re = util.compile_prefix_regex(_prefixes)
    suffix_re = util.compile_suffix_regex(_suffixes)
    infix_re = util.compile_infix_regex(_infixes)
    _tokenizer_exceptions = nlp.Defaults.tokenizer_exceptions
    return Tokenizer(nlp.vocab,
                     _tokenizer_exceptions,
                     prefix_search=prefix_re.search,
                     suffix_search=suffix_re.search,
                     infix_finditer=infix_re.finditer,
                     token_match=_protect.match)

def add_custom_properties(nlp):
    # weird error when normalizing 'a' gives 'gonna'
    special_case = [{ORTH: u'a', NORM: u'a'}]
    nlp.tokenizer.add_special_case(u'a', special_case)
    special_case = [{ORTH: u'is', NORM: u'is'}]
    nlp.tokenizer.add_special_case(u"'s", special_case) 
    special_case = [{ORTH: u'am', NORM: u'am'}]
    nlp.tokenizer.add_special_case(u"am", special_case)
    # custom token attribute for symbols token._.is_symbol returns True if its a unicode symbol
    is_symbol_getter = lambda token: (len(token) == 1 and unicodedata.category(token.text).startswith('S'))
    Token.set_extension('is_symbol', getter=is_symbol_getter)


if __name__ == '__main__':
    nlp = spacy.load('en', disable=['tagger', 'parser', 'ner'])
    nlp.tokenizer = so_tokenizer(nlp)
    add_custom_properties(nlp)

    #test_overload = u'''1001101.1101111.1110010.1100101.1100010.1100001.1110010.1101110.1100101.100000.1101111.1110010.100000'''
    test_punct = u'''18:12:54 AM cv).model c)+comf a)x I am trying to v3.4 1.2.3 2.9898 100% 5 @role='listbox']div role="listbox" [role="listbox"]div 0,0,100,200 .='stackoverflow -output- first# j# j++ -hi hello- :try this:a a:this I've had numerous object's attribute I didn't isn't I've got this can't ca 0-first 'hello and a leprechaun who'd do that... com.rabbitmq:amqp-client org.codehaus.mojo:exec-maven-plugin:1.2.1:exec http://myjasperserverurl/jasperserver/rest_v2/reports/TestDir/TestReport.pdf?j_username=xxx&j_password=xxx&PARAMETER1=9734&PARAMETER2=0&PARAMETER3=815G21. this.org(needs(split.o())) end'''
    test_apis = u'''String.replaceAll("\\<(.*?)\\>", ""); Java/C#'s C++'s C#, ,C# ,C#. variable': all=in_go[3] all:i[n =int& &ew arrrya.List<String> ]List ->List-> array[1, 4, 5] array[2] arr[4 arr[ arr{ :asd -123 ~123 -asdf >arrow org.apache.javalang one.two.three(String) one.two(one.two(toString())) one.two() getMaxSize(), ,getMinSize() split. equals() :) -_- (javadoc) .(be reflexive). .o.equals(null) equals(null) equals(not null) https://hello-world.com/q?:st/url.html https://spacy.io/ http://try.com/this/ if(time && 0){do this;} #hello invalid#hashtag#seq @jvx @Warning at 20:21 test-site.com testmail@ece.auth.gr testmail@hotmail.com .NET Java/.Net'''
    test_text = u'''In Java, the 'int' type is a primitive , whereas the 'Integer' type is an object. In C#, the 'int' type is the same as System.Int32 and is a value type (i.e. more like the java 'int'). An integer (just like any other value types) can be boxed ("wrapped") into an object. I've had numerous object's attribute I didn't isn't I've got this can't ca 0-first 'hello 100,500,300,200,400.23'''
    test_urls = u'''https://www.google.com/search?q=i%20like%20gizmodo&rct=j?te&rm=what+is+this%3F&public=true file:/aaa/bbb/ccc_20150310235959999.html'''

    print(test_punct, end='\n\n')
    doc = nlp(test_punct)
    result = u' '.join(t.norm_ for t in doc)
    doc = nlp(result)
    result = u' '.join(t.norm_ for t in doc if not (t.is_punct or t.is_bracket or t.is_quote or t._.is_symbol or t.like_num))
    print(result, end='\n\n')
    
    print(test_apis, end='\n\n')
    doc = nlp(test_apis)
    result = u' '.join(t.norm_ for t in doc)
    doc = nlp(result)
    result = u' '.join(t.norm_ for t in doc if not (t.is_punct or t.is_bracket or t.is_quote or t._.is_symbol or t.like_num))
    print(result, end='\n\n')

    print(test_urls, end='\n\n')
    doc = nlp(test_urls)
    result = u' '.join(t.norm_ for t in doc)
    doc = nlp(result)
    result = u' '.join(t.norm_ for t in doc if not (t.is_punct or t.is_bracket or t.is_quote or t._.is_symbol or t.like_num))
    print(result, end='\n\n')
