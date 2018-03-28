import os
import re
import sys
import json
from collections import OrderedDict

file_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(file_path)
extractor_path = file_path + '/SequenceExtractor-0.4.jar'
from javalang_extractor import extract_api_info
from sequenceextractor import SequenceExtractor

class APIExtractor:
	def __init__(self, seq_extractor_jar_path=extractor_path, index_path=None):
		self.sequence_extractor = SequenceExtractor(seq_extractor_jar_path, 
									keep_function_call_types=True, 
									keep_literals=True, 
									keep_branches=True, 
									output_tree=False, 
									flatten_output=False, 
									add_unique_ids=False)
		self.index = None
		if index_path:
		    self.index = open(index_path, 'a')
		else:
			print('Extracted API calls won\'t be recorded. API index path not provided.')

	def extract_api_tokens(self, snippet):
		try:
			code = snippet
			sequences = self.sequence_extractor.parse_snippet(code)
			sequences = re.sub("(\s|\[)(\w|\(|\))", r'\1"\2', sequences)
			sequences = re.sub("(\w|\(|\))(,|\])", r'\1"\2', sequences)
			sequences = re.sub("(\[)(\])", r'\1""\2', sequences)
			sequences = re.sub(",( ,)*", r',', sequences)
			sequences = re.sub(", ]", r']', sequences)
			sequences = eval(sequences)
		except:
			sequences = []
		final_sequence = []
		literals = []
		for sequence in sequences:
			for item in sequence:
				if item.startswith("CI_"):
					final_sequence.append(item[3:] + '.__init__')
				elif item.startswith("FC_"):
					p2 = re.compile('FC_.*\((.*)\)')
					inner = list(p2.findall(item))
					if inner:
						final_sequence.append(inner[0])
				elif item.startswith("AM_"):
					literals.append(item[3:])
		return list(OrderedDict.fromkeys(final_sequence)), literals

	def fused_api_extraction(self, snippet, keep_jlang_tokens):
		api_tokens, literals = self.extract_api_tokens(snippet)
		je_api_tokens, comments = extract_api_info(snippet, keep_jlang_tokens=keep_jlang_tokens)
		total_api_tokens = api_tokens + je_api_tokens
		if self.index and len(total_api_tokens) > 0:
			self.dump_api_tokens(total_api_tokens)
		return ' '.join([' '.join(total_api_tokens), comments])

	def dump_api_tokens(self, tokens):
		for t in tokens:
			self.index.write(t + '\n')

	def close(self):
		self.sequence_extractor.close()
		if self.index:
			self.index.close()
			self.index = None


if __name__ == "__main__":
	ae = APIExtractor(index_path='testindex')
	TESTFILE = 'TEST'
	with open(TESTFILE, 'r') as f:
		code_snippet = f.read()
		print(ae.fused_api_extraction(code_snippet, True))
