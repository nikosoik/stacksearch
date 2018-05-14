import os
import re
import sys
import base64
from collections import OrderedDict
from subprocess import PIPE, STDOUT, Popen

from javalang import tokenizer

file_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(file_path)
codeparser_jar = os.path.join(file_path, 'CodeParser-0.1.5.jar')

# CodeParser Special Messages
START_MSG = '__START__'
END_MSG = '__END__'
ERROR_MSG = '__ERROR__'


class CodeParser:
    def __init__(self,
                 codeparser_jar=codeparser_jar,
                 index_path=None,
                 extract_sequence=True,
                 keep_imports=False,
                 keep_comments=False,
                 keep_literals=False,
                 keep_unknown_method_calls=False):

        self.index = None
        self.num_messages = 0

        if index_path:
            self.index = open(index_path, 'a')

        self.args = [
            'java', '-jar', codeparser_jar,
            'true' if extract_sequence else 'false',
            'true' if keep_imports else 'false',
            'true' if keep_comments else 'false',
            'true' if keep_literals else 'false',
            'true' if keep_unknown_method_calls else 'false'
        ]
        self.proc = Popen(self.args, stdin=PIPE, stdout=PIPE, stderr=STDOUT)

        line = self._send_message(START_MSG)
        if line != START_MSG:
            self._print_error('CodeParser error...')
            print(line)
            exit()
        else:
            self._print_info('Connection established...')

    def _send_message(self, message):
        messagebytes = message.encode()
        b64encodedbytes = base64.b64encode(messagebytes)
        self.proc.stdin.write(b64encodedbytes + b'\n')
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        try:
            b64decodedbytes = base64.b64decode(line)
            decodedline = b64decodedbytes.decode()
        except Exception as e:
            decodedline = ERROR_MSG
            self.restart(force=True)
            print(e)
        return decodedline

    def _print_error(self, message, end='\n'):
        sys.stdout.write('\x1b[1;31m' + '[CodeParser]: ' + '\x1b[0m')
        print(message.strip(), end=end)

    def _print_info(self, message, end='\n'):
        sys.stdout.write('\x1b[1;33m' + '[CodeParser]: ' + '\x1b[0m')
        print(message.strip(), end=end)

    def close(self):
        if self.index:
            self.index.close()
            self.index = None
        if self._send_message(END_MSG) == END_MSG:
            self._print_info('Connection terminated...')
        else:
            self._print_error('Error terminating CodeParser connection...')

    def restart(self, force=False):
        if force or self._send_message(END_MSG) == END_MSG:
            self.num_messages = 0
            self.proc.kill()
            self.proc = Popen(
                self.args, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        else:
            self._print_error('Error restarting CodeParser service...')
            exit()

    def parse_code(self, code_snippet):
        self.num_messages += 1
        if self.num_messages == 200000:
            self.restart()
        return self._send_message(code_snippet)

    def tokenize_sequence(self, code_snippet, unique_tokens=False):
        sequence = self.parse_code(code_snippet)
        if sequence == ERROR_MSG:
            return []
        sequence = sequence.split(', ')
        sequence = [
            re.sub(r'^_(IM|COM|VAR|OC|MC|UMC)+_', r'', token)
            for token in sequence
        ]
        if unique_tokens:
            sequence = list(OrderedDict.fromkeys(sequence))
        if self.index and len(sequence) > 0:
            for token in sequence:
                self.index.write(token + '\n')
        return sequence

    def tokenize_code(self, code_snippet):
        parsed_code = self.parse_code(code_snippet)
        if parsed_code == ERROR_MSG:
            return []
        try:
            return [t.value for t in tokenizer.tokenize(parsed_code)]
        except Exception as e:
            print('\n'.join([parsed_code, e]))
            return []
