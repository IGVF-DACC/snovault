'''
Extracted from https://github.com/Pylons/pyramid/blob/1.10-branch/src/pyramid/_compat.py
'''

from urllib.parse import unquote_to_bytes


string_types = (str,)
integer_types = (int,)
class_types = (type,)
text_type = str
binary_type = bytes
long = int


def native_(s, encoding='latin-1', errors='strict'):
    """If ``s`` is an instance of ``text_type``, return
    ``s``, otherwise return ``str(s, encoding, errors)``"""
    if isinstance(s, text_type):
        return s
    return str(s, encoding, errors)


def unquote_bytes_to_wsgi(bytestring):
    return unquote_to_bytes(bytestring).decode('latin-1')


def ascii_native_(s):
    if isinstance(s, text_type):
        s = s.encode('ascii')
    return str(s, 'ascii', 'strict')


def bytes_(s, encoding='latin-1', errors='strict'):
    """If ``s`` is an instance of ``text_type``, return
    ``s.encode(encoding, errors)``, otherwise return ``s``"""
    if isinstance(s, text_type):
        return s.encode(encoding, errors)
    return s
