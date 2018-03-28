import re
import os
import sys
import spacy
import codecs
import subprocess
import multiprocessing
from spacy.lang import en

script_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(script_path)
from so_tokenizer import so_tokenizer, add_custom_properties

# number of CPU cores available
cores = multiprocessing.cpu_count()

# regular expressions
PATH_RE = r"\b((?:[Cc]:)?(?:\\\S{2,}){2,})\b"
LARGE_TOKEN_RE = r"[a-b0-9]{50,}|[\*-=\+~#!_]{3,}"

def remove_paths(text):
    '''
    helper function that removes large Windows paths from text
    '''
    return re.sub(PATH_RE, ' ', text)

def remove_large_tokens(text):
    '''
    helper function that removes large tokens from text
    '''
    return re.sub(LARGE_TOKEN_RE, '', text)

def symbol_num(token):
    '''
    helper function to eliminate tokens that
    are symbols or number-like
    symbol is a custom attribute added in so_tokenizer.py
    add_custom_properties(nlp) function
    '''
    return token.like_num or token._.is_symbol

def url_email(token):
    '''
    helper function to eliminate tokens that
    are urls and emails
    '''
    return token.like_url or token.like_email

def punct_space(token):
    '''
    helper function to eliminate tokens that
    are pure punctuation or whitespace
    '''
    return token.is_punct or token.is_bracket or token.is_quote or token.is_space

def line_feed(filename, func=remove_paths):
    '''
    generator function feed lines from file
    *func is a user provided function that preprocesses the line
    and returns text
    '''
    with codecs.open(filename, encoding='utf_8') as f:
        for line in f:
            yield func(line)

def normalized_line_feed(filename, nlp):
    '''
    generator function that uses spaCy to parse lines,
    normalize the text and yield sentences
    '''
    for parsed_line in nlp.pipe(line_feed(filename), batch_size=5000, n_threads=cores):
        # tokenize a second time to remove leftover punctuation from complex strings
        parsed_line = nlp(u' '.join([token.norm_ for token in parsed_line
                        if not (punct_space(token) or url_email(token) or symbol_num(token))]))
        yield u' '.join([token.norm_ for token in parsed_line
                        if not (punct_space(token) or url_email(token) or symbol_num(token))])

def lemmatized_line_feed(filename, nlp):
    '''
    generator function that uses spaCy to parse lines,
    lemmatize the text, and yield sentences
    '''
    for parsed_line in nlp.pipe(line_feed(filename), batch_size=1600, n_threads=cores):
        yield u' '.join([token.lemma_ for token in parsed_line
                        if not (punct_space(token) or url_email(token) or symbol_num(token))])

def unigrams_to_disk(func, raw_fp, output_fp, nlp):
    '''
    helper function that saves unigrams to disk
    '''
    with codecs.open(output_fp, 'w', encoding='utf_8') as f:
        for line in func(raw_fp, nlp):
            f.write(line + '\n')

def ngrams_to_disk(prev_ngram_sents, ngram_phraser, output_fp):
    '''
    uses (n-1)-gram sentences and an ngram phraser
    to generate ngram sentences and save them to disk
    e.g. in: bigram_sentences, trigram_phraser out: trigrams
    '''
    with codecs.open(output_fp, 'w', encoding='utf_8') as f:
        for prev_ngram_sent in prev_ngram_sents:        
            ngram_sent = u' '.join(ngram_phraser[prev_ngram_sent])
            f.write(ngram_sent + '\n')
    
def ngram_model_to_disk(sents, output_fp):
    '''
    helper function that saves ngram model to disk and returns
    it for further use
    '''
    ngrams = Phrases(sents, min_count=40, common_terms=frozenset(en.STOP_WORDS))
    ngram_phraser = Phraser(ngrams)
    ngram_phraser.save(output_fp)
    return ngram_phraser

def process_corpus(corpus_path, export_file, del_stack_trace):
    # bash scripts
    del_trash_strings = os.path.join(script_path, 'del_trash_strings.sh')
    norm_corpus = os.path.join(script_path, 'normalize_corpus.sh')
    # clean leftover java stack traces from corpus
    corpus_wo_stacktrace = corpus_path
    if del_stack_trace:
        inp_corpus_name = os.path.basename(corpus_path)
        print('Removing leftover java stack traces from "{}" corpus...'.format(inp_corpus_name))
        subprocess.check_call([del_trash_strings, corpus_path])
        corpus_wo_stacktrace = corpus_path + '_nst'
    # load spacy basic pipeline (just tokenizer) with the custom so_tokenizer
    nlp = spacy.load('en', disable=['tagger', 'parser', 'ner'])
    nlp.tokenizer = so_tokenizer(nlp)
    add_custom_properties(nlp)
    print('spaCy model loaded...\nProcessing text...')# save unigrams to disk
    unigrams_to_disk(normalized_line_feed, corpus_wo_stacktrace, export_file, nlp)
    # normalize text
    print('Normalizing text (removing unneeded punctuation and strings)...')
    export_file = os.path.realpath(export_file)
    subprocess.check_call([norm_corpus, export_file])
    print('Output corpus at:', export_file + '_norm')


if __name__ == '__main__':
    
    """
    # load unigrams from disk
    unigram_sents = LineSentence(unigrams_fp)
    print('unigram loading finished...')

    # train and save bigram model to disk
    bigram_phraser = ngram_model_to_disk(unigram_sents, bigram_model_fp)
    
    # load the finished bigram model from disk
    #bigram_phraser = Phraser.load(bigram_model_fp)

    # save bigrams to disk
    ngrams_to_disk(unigram_sents, bigram_phraser, bigrams_fp)
    print('bigrams saved to disk...')

    # load bigrams from disk
    bigram_sents = LineSentence(bigrams_fp)
    
    # train and save trigram model to disk
    trigram_phraser = ngram_model_to_disk(bigram_sents, trigram_model_fp)

    # load the finished trigram model from disk
    #trigram_phraser = Phraser.load(trigram_model_fp)
    
    # save trigrams to disk
    ngrams_to_disk(bigram_sents, trigram_phraser, trigrams_fp)
    print('trigrams saved to disk...')
    """