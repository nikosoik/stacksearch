import base64
import subprocess
from subprocess import STDOUT, PIPE

class _SequenceExtractor(object):
	"""
	Inner python binding to the SequenceExtractor library. It works by executing the jar file as a subprocess
	and opening pipes to the standard input and standard output so that messages can be sent and received.
	Instead of using this class, it is highly recommended to use the abstracted SequenceExtractor class.
	"""
	def __init__(self, path_to_SequenceExtractor_jar, keep_function_call_types=False, keep_literals=False, keep_branches=True, output_tree=False, flatten_output=True, add_unique_ids=False):
		"""
		Initializes this inner extractor.
		
		:param path_to_SequenceExtractorjar: the path to the SequenceExtractor jar.
		:param keep_function_call_types: boolean denoting whether function call types should be retained.
		:param keep_literals: boolean denoting whether literals (primitives) should be retained.
		:param keep_branches: boolean denoting whether all branches should be kept.
		:param output_tree: boolean denoting whether the output should be a tree or a sequence.
		:param flatten_output: boolean denoting whether the output should be flattened.
		:param add_unique_ids: boolean denoting whether statements should have IDs.
		"""
		self.cmd = ['java', '-cp', path_to_SequenceExtractor_jar, 'sequenceextractor.PythonBinder',
					'true' if keep_function_call_types else 'false', 'true' if keep_literals else 'false',
					'true' if keep_branches else 'false', 'true' if output_tree else 'false',
					'true' if flatten_output else 'false', 'true' if add_unique_ids else 'false']
		self.proc = subprocess.Popen(self.cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
		self.nummessages = 0
		line = self.send_message("START_OF_TRANSMISSION")
		if line != "START_OF_TRANSMISSION":
			print("Error in Sequence Extractor!!")
			exit()

	def close_extractor(self):
		"""
		Closes the extractor.
		"""
		return self.send_message("END_OF_TRANSMISSION") == "END_OF_TRANSMISSION"

	def restart_extractor(self, force=False):
		"""
		Restarts the extractor.
		"""
		if force or self.send_message("END_OF_TRANSMISSION") == "END_OF_TRANSMISSION":
			self.proc = subprocess.Popen(self.cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
			self.nummessages = 0
		else:
			print("Error in Java compiler!!")
			exit()

	def get_sequence(self, code_entity):
		"""
		Returns the command sequence of a code_entity.
		
		:param code_entity: the contents of the code entity.
		"""
		self.nummessages += 1
		if self.nummessages == 10000:
			self.restart_extractor()
		return self.send_message(code_entity)

	def send_message(self, message):
		"""
		Sends a new message to the SequenceExtractor jar.
		
		:param message: the message to be sent.
		"""
		decodedbytes = message.encode(encoding='ascii')
		b64encodedbytes = base64.b64encode(decodedbytes)
		self.proc.stdin.write(b64encodedbytes + b"\r\n")
		self.proc.stdin.flush()
		line = self.proc.stdout.readline()
		try:
			b64decodedbytes = base64.b64decode(line)
			decodedline = b64decodedbytes.decode()
		except:
			self.restart_extractor(True)
			decodedline = ""
		return decodedline

class SequenceExtractor(_SequenceExtractor):
	"""
	Class used as a python binding to the SequenceExtractor library. It contains functions for parsing java snippets to sequences.
	"""
	def __init__(self, path_to_SequenceExtractor_jar, keep_function_call_types=False, keep_literals=False, keep_branches=True, output_tree=False, flatten_output=True, add_unique_ids=False):
		"""
		Initializes this Sequence Extractor.
		
		:param path_to_SequenceExtractor_jar: the path to the SequenceExtractor jar
		:param keep_function_call_types: boolean denoting whether function call types should be retained.
		:param keep_literals: boolean denoting whether literals (primitives) should be retained.
		:param keep_branches: boolean denoting whether all branches should be kept.
		:param output_tree: boolean denoting whether the output should be a tree or a sequence.
		:param flatten_output: boolean denoting whether the output should be flattened.
		:param add_unique_ids: boolean denoting whether statements should have IDs.
		"""
		super(SequenceExtractor, self).__init__(path_to_SequenceExtractor_jar, keep_function_call_types, keep_literals, keep_branches, output_tree, flatten_output, add_unique_ids)

	def parse_snippet(self, snippet_contents):
		"""
		Parses the contents of a java snippet and returns its sequence.

		:param snippet_contents: the contents of a java snippet, given as a string.
		:returns: a string containing the sequence of the java snippet.
		"""
		return super(SequenceExtractor, self).get_sequence(snippet_contents)

	def close(self):
		"""
		Closes the Sequence Extractor. Note that this function must be called after using the class.
		Otherwise, this may result to a memory leak.
		"""
		super(SequenceExtractor, self).close_extractor()
