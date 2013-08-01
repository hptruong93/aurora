# Aurora-Client Utils
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
# Borrowed From Mohammad Faraji (SAVI Toronto, Janus-Client Code)

import prettytable

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
