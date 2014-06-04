'''
Created on Jan 7, 2013

@author: Mohammad Faraji<ms.faraji@utoronto.ca>
'''
import prettytable
import uuid
import string

def is_authentication_required(f):
    """Checks to see if the function requires authentication.

Use the skip_authentication decorator to indicate a caller may
skip the authentication step.
"""
    return getattr(f, 'require_authentication', True)


def arg(*args, **kwargs):
    def _decorator(func):
        func.__dict__.setdefault('arguments', []).insert(0, (args, kwargs))
        return func
    return _decorator

def pretty_choice_list(l):
        return ','.join("%s" % i for i in l)

def print_list(objs, fields, formatters={}):
    pt = prettytable.PrettyTable([f for f in fields], caching=False)
    pt.align = 'l'

    for o in objs:
        row = []
        for field in fields:
            if field in formatters:
                row.append(formatters[field](o))
            else:
                data = o[field] or ''
                row.append(data)
        pt.add_row(row)

    print pt.get_string(sortby=fields[0])


def print_dict(d):
    pt = prettytable.PrettyTable(['Property', 'Value'], caching=False)
    pt.align = 'l'
    [pt.add_row(list(r)) for r in d.iteritems()]
    print pt.get_string(sortby='Property')

def generate_request_id():
    return str(uuid.uuid4())

def remove_letters(input_string):
    translate = string.maketrans('','')
    nodigs = translate.translate(translate, string.digits)
    return input_string.translate(translate, nodigs)

def remove_digits(input_string):
    return ''.join([i for i in input_string if not i.isdigit()])