# -*- coding: utf-8 -*-

import re
import sys

import duralex.alinea_lexer as alinea_lexer
import duralex.tree

from duralex.tree import *

import parsimonious

def debug(node, tokens, i, msg):
    if '--debug' in sys.argv:
        print('    ' * get_node_depth(node) + msg + ' ' + str(tokens[i:i+8]))

def is_number(token):
    return re.compile('\d+').match(token)

def is_space(token):
    return re.compile('^\s+$').match(token)

def parse_int(s):
    return int(re.search(r'\d+', s).group())

def parse_roman_number(n):
    romans_map = zip(
        (1000,  900, 500, 400 , 100,  90 , 50 ,  40 , 10 ,   9 ,  5 ,  4  ,  1),
        ( 'M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
    )

    n = n.upper()
    i = res = 0
    for d, r in romans_map:
        while n[i:i + len(r)] == r:
            res += d
            i += len(r)
    return res

def is_roman_number(token):
    return re.compile(r"[IVXCLDM]+(er)?").match(token)

def is_number_word(word):
    return word_to_number(word) >= 0

def word_to_number(word):
    words = [
        [u'un', u'une', u'premier', u'première'],
        [u'deux', u'deuxième', u'second', u'seconde'],
        [u'trois', u'troisième'],
        [u'quatre', u'quatrième'],
        [u'cinq', u'cinquième'],
        [u'six', u'sixième'],
        [u'sept', u'septième'],
        [u'huit', u'huitième'],
        [u'neuf', u'neuvième'],
        [u'dix', u'dixième'],
        [u'onze', u'onzième'],
        [u'douze', u'douzième'],
        [u'treize', u'treizième'],
        [u'quatorze', u'quatorzième'],
        [u'quinze', u'quinzième'],
        [u'seize', u'seizième'],
    ]

    word = word.lower()
    word = word.replace(u'È', u'è')

    for i in range(0, len(words)):
        if word in words[i]:
            return i + 1

    return -1

def month_to_number(month):
    return alinea_lexer.TOKEN_MONTH_NAMES.index(month) + 1

def parse_section_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_SECTION_REFERENCE,
        'children': [],
    })

    debug(parent, tokens, i, 'parse_section_reference')

    # la section {order}
    if tokens[i].lower() == u'la' and tokens[i + 2] == u'section':
        node['order'] = parse_int(tokens[i + 4]);
        i += 6
    # de la section {order}
    elif tokens[i] == u'de' and tokens[i + 2] == u'la' and tokens[i + 4] == u'section':
        node['order'] = parse_int(tokens[i + 6]);
        i += 8
    else:
        remove_node(parent, node)
        return i

    i = parse_reference(tokens, i, node)

    debug(parent, tokens, i, 'parse_section_reference end')

    return i

def parse_subsection_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_SUBSECTION_REFERENCE,
        'children': [],
    })

    debug(parent, tokens, i, 'parse_subsection_reference')

    grammar = parsimonious.Grammar("""
sub_section = ~"(de )*" "la sous-section " sub_section_order
sub_section_order = ~"\d+"
    """)

    try:
        tree = grammar.match(''.join(tokens[i:]))
        i += len(alinea_lexer.tokenize(tree.text))
        capture = CaptureVisitor(['sub_section_order' ])
        capture.visit(tree)
        node['order'] = parse_int(capture.captures['sub_section_order'])
    except parsimonious.exceptions.ParseError:
        remove_node(parent, node)
        return i

    i = parse_reference(tokens, i, node)

    debug(parent, tokens, i, 'parse_subsection_reference end')

    return i

def parse_chapter_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_CHAPTER_REFERENCE,
        'children': [],
    })

    debug(parent, tokens, i, 'parse_chapter_reference')

    # du chapitre {order}
    # le chapitre {order}
    if tokens[i].lower() in [u'du', u'le'] and tokens[i + 2] == u'chapitre' and is_roman_number(tokens[i + 4]):
        node['order'] = parse_roman_number(tokens[i + 4]);
        i += 6
    else:
        remove_node(parent, node)
        return i

    i = parse_reference(tokens, i, node)

    debug(parent, tokens, i, 'parse_chapter_reference end')

    return i

def parse_paragraph_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_PARAGRAPH_REFERENCE,
        'children': [],
    })

    debug(parent, tokens, i, 'parse_paragraph_reference')

    # du paragraphe {order}
    # le paragraphe {order}
    if tokens[i].lower() in [u'du', u'le'] and tokens[i + 2] == u'paragraphe':
        node['order'] = parse_int(tokens[i + 4]);
        i += 6
    else:
        remove_node(parent, node)
        return i

    i = parse_reference(tokens, i, node)

    debug(parent, tokens, i, 'parse_paragraph_reference end')

    return i

def parse_subparagraph_definition(tokens, i, parent):
    if i >= len(tokens):
        return i

    debug(parent, tokens, i, 'parse_subparagraph_definition')

    node = create_node(parent, {
        'type': TYPE_SUBPARAGRAPH_DEFINITION,
        'children': [],
    })

    j = i

    # un sous-paragraphe[s] [{order}] [ainsi rédigé]
    if is_number_word(tokens[i]) and tokens[i + 2].startswith(u'sous-paragraphe'):
        count = word_to_number(tokens[i])
        i += 4
        # [{order}]
        if is_number(tokens[i]):
            node['order'] = parse_int(tokens[i])
        # ainsi rédigé
        if (i + 2 < len(tokens) and tokens[i + 2].startswith(u'rédigé')
            or (i + 4 < len(tokens) and tokens[i + 4].startswith(u'rédigé'))):
            i = alinea_lexer.skip_to_quote_start(tokens, i)
            i = parse_for_each(parse_quote, tokens, i, node)
    else:
        remove_node(parent, node)
        debug(parent, tokens, i, 'parse_subparagraph_definition none')
        return j

    debug(parent, tokens, i, 'parse_subparagraph_definition end')

    return i

def parse_law_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    j = i

    debug(parent, tokens, i, 'parse_law_reference')

    # de la loi n° 77-729 du 7 juillet 1977
    grammar = parsimonious.Grammar( """
entry = ( ~"de la loi n° +" numero_annee_identifiant du_date ) / ( ~"de la même loi" )

numero_annee_identifiant = ~"[0-9]+-[0-9]+"

du_date = ~" +du +"i date
date = jour espace mois espace annee
jour = ~"1er|[12][0-9]|3[01]|[1-9]"i
mois = ~"janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre"i
annee = ~"(1[5-9]|2[0-9])[0-9]{2}"

espace = ~" +"
numero = ~" +n° *| +no *"i
    """ )

    node = create_node(parent, {
        'type': TYPE_LAW_REFERENCE,
        'id': '',
        'children': [],
    })
    try:
        tree = grammar.match( ''.join( tokens[i:] ) )
        i += len( alinea_lexer.tokenize( tree.text ) )
        capture = CaptureVisitor( [ 'numero_annee_identifiant', 'annee', 'mois', 'jour' ] )
        capture.visit( tree )
        if 'numero_annee_identifiant' in capture.captures:
            node['id'] = capture.captures['numero_annee_identifiant']
            node['lawDate'] = '%s-%i-%s' % (capture.captures['annee'], month_to_number( capture.captures['mois'] ), capture.captures['jour'] )
    except parsimonious.exceptions.ParseError:
        remove_node(parent, node)

    debug(parent, tokens, i, 'parse_law_reference end')

    return i

def parse_multiplicative_adverb(tokens, i, node):
    if i >= len(tokens):
        return i

    adverbs = alinea_lexer.TOKEN_MULTIPLICATIVE_ADVERBS.sort(key = lambda s: -len(s))
    for adverb in alinea_lexer.TOKEN_MULTIPLICATIVE_ADVERBS:
        if tokens[i].endswith(adverb):
            node['is' + adverb.title()] = True;
            # skip {multiplicativeAdverb} and the following space
            i += 1
            i = alinea_lexer.skip_spaces(tokens, i)
            return i
    return i

def parse_definition(tokens, i, parent):
    if i >= len(tokens):
        return i

    i = parse_one_of(
        [
            parse_article_definition,
            parse_alinea_definition,
            parse_mention_definition,
            parse_header1_definition,
            parse_header2_definition,
            parse_header3_definition,
            parse_sentence_definition,
            parse_word_definition,
            parse_title_definition,
            parse_subparagraph_definition
        ],
        tokens,
        i,
        parent
    )

    return i

def parse_sentence_definition(tokens, i, parent):
    if i >= len(tokens):
        return i

    debug(parent, tokens, i, 'parse_sentence_definition')
    j = i

    # {count} phrases
    if is_number_word(tokens[i]) and tokens[i + 2].startswith(u'phrase'):
        count = word_to_number(tokens[i])
        i += 4
        # ainsi rédigé
        # est rédigé
        # est ainsi rédigé
        if (i + 2 < len(tokens) and tokens[i + 2].startswith(u'rédigé')
            or (i + 4 < len(tokens) and tokens[i + 4].startswith(u'rédigé'))):
            # we expect {count} definitions => {count} quotes
            # but they don't always match, so for now we parse all of the available contents
            # FIXME: issue a warning because the expected count doesn't match?
            i = alinea_lexer.skip_spaces(tokens, i)
            i = alinea_lexer.skip_to_quote_start(tokens, i)
            i = parse_for_each(
                parse_quote,
                tokens,
                i,
                lambda : create_node(parent, {'type': TYPE_SENTENCE_DEFINITION, 'children': []})
            )
        else:
            create_node(parent, {'type': TYPE_SENTENCE_DEFINITION, 'count': count})
    else:
        debug(parent, tokens, i, 'parse_sentence_definition none')
        return j

    debug(parent, tokens, i, 'parse_sentence_definition end')

    return i

def parse_word_definition(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_WORD_DEFINITION,
    })
    debug(parent, tokens, i, 'parse_word_definition')

    j = i
    i = parse_position(tokens, i, node)
    i = parse_scope(tokens, i, node)
    # le mot
    # les mots
    # des mots
    if tokens[i].lower() in [u'le', u'les', u'des'] and tokens[i + 2].startswith(u'mot'):
        i = alinea_lexer.skip_to_quote_start(tokens, i)
        i = parse_for_each(parse_quote, tokens, i, node)
        # i = alinea_lexer.skip_spaces(tokens, i)
    # le nombre
    # le chiffre
    # le taux
    elif tokens[i].lower() == u'le' and tokens[i + 2] in [u'nombre', u'chiffre', u'taux']:
        i = alinea_lexer.skip_to_quote_start(tokens, i)
        i = parse_quote(tokens, i, node)
    # "
    elif tokens[i] == alinea_lexer.TOKEN_DOUBLE_QUOTE_OPEN:
        i = parse_for_each(parse_quote, tokens, i, node)
        i = alinea_lexer.skip_spaces(tokens, i)
    # la référence
    # les références
    elif tokens[i].lower() in [u'la', u'les'] and tokens[i + 2].startswith(u'référence'):
        i = alinea_lexer.skip_to_quote_start(tokens, i)
        i = parse_quote(tokens, i, node)
    else:
        debug(parent, tokens, i, 'parse_word_definition none')
        remove_node(parent, node)
        return j
    debug(parent, tokens, i, 'parse_word_definition end')
    return i

def parse_article_definition(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_ARTICLE_DEFINITION,
        'children': [],
    })
    debug(parent, tokens, i, 'parse_article_definition')

    # un article
    if tokens[i].lower() == u'un' and tokens[i + 2] == u'article':
        i += 4
    # l'article
    elif tokens[i].lower() == u'l' and tokens[i + 2] == u'article':
        i += 4
    else:
        debug(parent, tokens, i, 'parse_article_definition none')
        remove_node(parent, node)
        return i

    i = parse_article_id(tokens, i, node)

    i = alinea_lexer.skip_spaces(tokens, i)
    if i < len(tokens) and tokens[i] == u'ainsi' and tokens[i + 2] == u'rédigé':
        i = alinea_lexer.skip_to_quote_start(tokens, i)
        i = parse_for_each(parse_quote, tokens, i, node)

    debug(parent, tokens, i, 'parse_article_definition end')

    return i

def parse_alinea_definition(tokens, i, parent):
    if i >= len(tokens):
        return i

    debug(parent, tokens, i, 'parse_alinea_definition')

    # {count} alinéa(s)
    if is_number_word(tokens[i]) and tokens[i + 2].startswith(u'alinéa'):
        count = word_to_number(tokens[i])
        i += 4
        # ainsi rédigé
        # est rédigé
        # est ainsi rédigé
        if (i + 2 < len(tokens) and tokens[i + 2].startswith(u'rédigé')
            or (i + 4 < len(tokens) and tokens[i + 4].startswith(u'rédigé'))):
            # we expect {count} definitions => {count} quotes
            # but they don't always match, so for now we parse all of the available contents
            # FIXME: issue a warning because the expected count doesn't match?
            i = alinea_lexer.skip_spaces(tokens, i)
            i = alinea_lexer.skip_to_quote_start(tokens, i)
            i = parse_for_each(
                parse_quote,
                tokens,
                i,
                lambda: create_node(parent, {'type': TYPE_ALINEA_DEFINITION, 'children': []})
            )
        else:
            node = create_node(parent, {'type': TYPE_ALINEA_DEFINITION, 'count': count})
    else:
        debug(parent, tokens, i, 'parse_alinea_definition none')
        return i

    debug(parent, tokens, i, 'parse_alinea_definition end')

    return i

def parse_mention_definition(tokens, i, parent):
    if i >= len(tokens):
        return i
    node = create_node(parent, {
        'type': TYPE_MENTION_DEFINITION,
    })
    debug(parent, tokens, i, 'parse_mention_definition')
    # la mention
    if tokens[i].lower() == u'la' and tokens[i + 2] == u'mention':
        i += 4
    else:
        debug(parent, tokens, i, 'parse_mention_definition none')
        remove_node(parent, node)
        return i
    # :
    if tokens[i] == ':':
        i = alinea_lexer.skip_to_quote_start(tokens, i)
        i = parse_for_each(parse_quote, tokens, i, node)

    debug(parent, tokens, i, 'parse_mention_definition end')

    return i

def parse_header1_definition(tokens, i, parent):
    if i >= len(tokens):
        return i

    debug(parent, tokens, i, 'parse_header1_definition')
    # un {romanPartNumber}
    if tokens[i].lower() == u'un' and is_roman_number(tokens[i + 2]):
        node = create_node(parent, {
            'type': TYPE_HEADER1_DEFINITION,
            'order': parse_roman_number(tokens[i + 2]),
            })
        i += 4
        i = alinea_lexer.skip_spaces(tokens, i)
        if i + 2 < len(tokens) and tokens[i] == u'ainsi' and tokens[i + 2] == u'rédigé':
            i = alinea_lexer.skip_to_quote_start(tokens, i)
            i = parse_quote(tokens, i, node)
    # des {start} à {end}
    elif (tokens[i].lower() == u'des' and is_roman_number(tokens[i + 2])
        and tokens[i + 4] == u'à' and is_roman_number(tokens[i + 6])):
        start = parse_roman_number(tokens[i + 2])
        end = parse_roman_number(tokens[i + 6])
        i += 8
        # ainsi rédigés
        if (i + 2 < len(tokens) and tokens[i + 2].startswith(u'rédigé')
            or (i + 4 < len(tokens) and tokens[i + 4].startswith(u'rédigé'))):
            i = alinea_lexer.skip_to_quote_start(tokens, i + 4)
            i = parse_for_each(
                parse_quote,
                tokens,
                i,
                lambda : create_node(parent, {'type': TYPE_HEADER1_DEFINITION, 'order': start + len(parent['children']), 'children': []})
            )
    else:
        debug(parent, tokens, i, 'parse_header1_definition end')
        return i

    return i

def parse_header2_definition(tokens, i, parent):
    if i >= len(tokens):
        return i

    debug(parent, tokens, i, 'parse_header2_definition')

    # un ... ° ({articlePartRef})
    if tokens[i].lower() == u'un' and ''.join(tokens[i + 2:i + 5]) == u'...' and tokens[i + 6] == u'°':
        node = create_node(parent, {
            'type': TYPE_HEADER2_DEFINITION,
            })
        # FIXME: should we simply ignore the 'order' field all together?
        node['order'] = '...'
        i += 8
        i = alinea_lexer.skip_spaces(tokens, i)
        if tokens[i] == u'ainsi' and tokens[i + 2] == u'rédigé':
            i = alinea_lexer.skip_to_quote_start(tokens, i + 4)
            i = parse_quote(tokens, i, node)
    # un {order}° ({orderLetter}) ({multiplicativeAdverb}) ({articlePartRef})
    elif tokens[i].lower() == u'un' and re.compile(u'\d+°').match(tokens[i + 2]):
        node = create_node(parent, {
            'type': TYPE_HEADER2_DEFINITION,
            })
        node['order'] = parse_int(tokens[i + 2])
        i += 4
        if re.compile(u'[A-Z]').match(tokens[i]):
            node['subOrder'] = tokens[i]
            i += 2
        i = parse_multiplicative_adverb(tokens, i, node)
        i = parse_article_part_reference(tokens, i, node)
        i = alinea_lexer.skip_spaces(tokens, i)
        if i < len(tokens) and tokens[i] == u'ainsi' and tokens[i + 2] == u'rédigé':
            i = alinea_lexer.skip_to_quote_start(tokens, i + 4)
            i = parse_quote(tokens, i, node)
    # des {start}° à {end}°
    elif (tokens[i].lower() == u'des' and re.compile(u'\d+°').match(tokens[i + 2])
        and tokens[i + 4] == u'à' and re.compile(u'\d+°').match(tokens[i + 6])):
        start = parse_int(tokens[i + 2])
        end = parse_int(tokens[i + 6])
        i += 8
        # ainsi rédigés
        if (i + 2 < len(tokens) and tokens[i + 2].startswith(u'rédigé')
            or (i + 4 < len(tokens) and tokens[i + 4].startswith(u'rédigé'))):
            i = alinea_lexer.skip_to_quote_start(tokens, i + 4)
            i = parse_for_each(
                parse_quote,
                tokens,
                i,
                lambda : create_node(parent, {'type': TYPE_HEADER2_DEFINITION, 'order': start + len(parent['children']), 'children': []})
            )
    else:
        debug(parent, tokens, i, 'parse_header2_definition end')
        return i

    return i

def parse_header3_definition(tokens, i, parent):
    if i >= len(tokens):
        return i

    debug(parent, tokens, i, 'parse_header3_definition')

    # un {orderLetter}
    if tokens[i].lower() == u'un' and re.compile(u'^[a-z]$').match(tokens[i + 2]):
        node = create_node(parent, {
            'type': TYPE_HEADER3_DEFINITION,
            'order': ord(str(tokens[i + 2])) - ord('a') + 1,
            })
        i += 4
        i = alinea_lexer.skip_spaces(tokens, i)
        if i < len(tokens) and tokens[i] == u'ainsi' and tokens[i + 2] == u'rédigé':
            i = alinea_lexer.skip_to_quote_start(tokens, i + 4)
            i = parse_quote(tokens, i, node)
    # des {orderLetter} à {orderLetter}
    elif (tokens[i].lower() == u'des' and re.compile(u'^[a-z]$').match(tokens[i + 2])
        and tokens[i + 4] == u'à' and re.compile(u'^[a-z]$').match(tokens[i + 6])):
        start = ord(str(tokens[i + 2])) - ord('a') + 1
        end = ord(str(tokens[i + 6])) - ord('a') + 1
        i += 8
        # ainsi rédigés
        if (i + 2 < len(tokens) and tokens[i + 2].startswith(u'rédigé')
            or (i + 4 < len(tokens) and tokens[i + 4].startswith(u'rédigé'))):
            i = alinea_lexer.skip_to_quote_start(tokens, i + 4)
            i = parse_for_each(
                parse_quote,
                tokens,
                i,
                lambda : create_node(parent, {'type': TYPE_HEADER3_DEFINITION, 'order': start + len(parent['children']), 'children': []})
            )
    else:
        debug(parent, tokens, i, 'parse_header3_definition end')
        return i

    return i

def parse_article_id(tokens, i, node):
    node['id'] = ''

    # article {articleId}
    if i < len(tokens) and tokens[i] == 'L' and tokens[i + 1] == '.':
        while not re.compile('\d+(-\d+)?').match(tokens[i]):
            node['id'] += tokens[i]
            i += 1

    if i < len(tokens) and re.compile('\d+(-\d+)?').match(tokens[i]):
        node['id'] += tokens[i]
        # skip {articleId} and the following space
        i += 1
        i = alinea_lexer.skip_spaces(tokens, i)

    # {articleId} {articleLetter}
    # FIXME: handle the {articleLetter}{multiplicativeAdverb} case?
    if i < len(tokens) and re.compile('^[A-Z]$').match(tokens[i]):
        node['id'] += ' ' + tokens[i]
        # skip {articleLetter} and the following space
        i += 1
        i = alinea_lexer.skip_spaces(tokens, i)

    i = parse_multiplicative_adverb(tokens, i, node)

    if not node['id'] or is_space(node['id']):
        del node['id']

    return i

def parse_title_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_TITLE_REFERENCE,
        'children': [],
    })

    debug(parent, tokens, i, 'parse_title_reference')

    j = i
    i = parse_position(tokens, i, node)
    i = parse_scope(tokens, i, node)

    # le titre {order}
    # du titre {order}
    if tokens[i].lower() in [u'le', u'du'] and tokens[i + 2] == u'titre' and is_roman_number(tokens[i + 4]):
        node['order'] = parse_roman_number(tokens[i + 4])
        i += 6
        i = parse_multiplicative_adverb(tokens, i, node)
    else:
        debug(parent, tokens, i, 'parse_title_reference none')
        remove_node(parent, node)
        return j

    i = parse_reference(tokens, i, node)

    debug(parent, tokens, i, 'parse_title_reference end')

    return i

def parse_title_definition(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_TITLE_DEFINITION,
        'children': [],
    })

    debug(parent, tokens, i, 'parse_title_definition')

    # un titre {order}
    if tokens[i].lower() == u'un' and tokens[i + 2] == u'titre' and is_roman_number(tokens[i + 4]):
        node['order'] = parse_roman_number(tokens[i + 4])
        i += 6
        i = parse_multiplicative_adverb(tokens, i, node)
    else:
        debug(parent, tokens, i, 'parse_title_definition none')
        remove_node(parent, node)
        return i

    i = alinea_lexer.skip_spaces(tokens, i)
    if tokens[i] == u'ainsi' and tokens[i + 2] == u'rédigé':
        i = alinea_lexer.skip_to_quote_start(tokens, i)
        i = parse_for_each(parse_quote, tokens, i, node)

    debug(parent, tokens, i, 'parse_title_definition end')

    return i

def parse_code_part_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_CODE_PART_REFERENCE,
        'children': [],
    })

    debug(parent, tokens, i, 'parse_code_part_reference')

    j = i
    i = parse_position(tokens, i, node)
    i = parse_scope(tokens, i, node)

    # la {order} partie [{codeReference}]
    if tokens[i] == u'la' and is_number_word(tokens[i + 2]) and tokens[i + 4] == u'partie':
        node['order'] = word_to_number(tokens[i + 2])
        i += 6
        i = parse_code_reference(tokens, i, node)
    # de la {order} partie [{codeReference}]
    elif tokens[i] == u'de' and tokens[i + 2] == u'la' and is_number_word(tokens[i + 4]) and tokens[i + 6] == u'partie':
        node['order'] = word_to_number(tokens[i + 4])
        i += 8
        i = parse_code_reference(tokens, i, node)
    else:
        debug(parent, tokens, i, 'parse_code_part_reference none')
        remove_node(parent, node)
        return j

    debug(parent, tokens, i, 'parse_code_part_reference end')

    return i

def parse_book_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_BOOK_REFERENCE,
        'children': [],
    })

    debug(parent, tokens, i, 'parse_book_reference')

    j = i
    i = parse_position(tokens, i, node)
    i = parse_scope(tokens, i, node)

    # le livre {order}
    # du livre {order}
    if tokens[i].lower() in [u'le', u'du'] and tokens[i + 2] == u'livre' and is_roman_number(tokens[i + 4]):
        node['order'] = parse_roman_number(tokens[i + 4])
        i += 6
    else:
        debug(parent, tokens, i, 'parse_book_reference none')
        remove_node(parent, node)
        return j

    i = parse_reference(tokens, i, node)

    debug(parent, tokens, i, 'parse_book_reference end')

    return i

def parse_scope(tokens, i, parent):
    if i >= len(tokens):
        return i

    debug(parent, tokens, i, 'parse_scope')

    node = None

    # la fin de
    if tokens[i] == u'la' and tokens[i + 2] == u'fin' and tokens[i + 4] in [u'de', u'du']:
        i += 4
        parent['scope'] = 'end'

    debug(parent, tokens, i, 'parse_scope end')

    return i

def parse_bill_article_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    debug(parent, tokens, i, 'parse_bill_article_reference')

    # cet article
    if tokens[i] == u'cet' and tokens[i + 2] == u'article':
        i += 4
        article_refs = filter_nodes(
            get_root(parent),
            lambda n: 'type' in n and n['type'] == TYPE_BILL_ARTICLE_REFERENCE
        )
        # the last one in order of traversal is the previous one in order of syntax
        article_ref = copy_node(article_refs[-1])
        push_node(parent, article_ref)

    debug(parent, tokens, i, 'parse_bill_article_reference end')

    return i

def parse_article_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_ARTICLE_REFERENCE,
    })

    debug(parent, tokens, i, 'parse_article_reference')

    j = i
    i = parse_position(tokens, i, node)
    i = parse_scope(tokens, i, node)
    # de l'article
    # à l'article
    if tokens[i].lower() in [u'de', u'à'] and tokens[i + 2] == u'l' and tokens[i + 4] == u'article':
        i += 5
        i = alinea_lexer.skip_spaces(tokens, i)
        i = parse_article_id(tokens, i, node)
    # l'article
    elif tokens[i].lower() == u'l' and tokens[i + 2].startswith(u'article'):
        i += 3
        i = alinea_lexer.skip_spaces(tokens, i)
        i = parse_article_id(tokens, i, node)
    # les articles
    # des articles
    elif tokens[i].lower() in [u'des', u'les'] and tokens[i + 2].startswith(u'article'):
        i += 3
        i = alinea_lexer.skip_spaces(tokens, i)
        i = parse_article_id(tokens, i, node)
        i = alinea_lexer.skip_spaces(tokens, i)
        nodes = []
        while tokens[i] == u',':
            i += 2
            nodes.append(create_node(parent, {'type':TYPE_ARTICLE_REFERENCE}))
            i = parse_article_id(tokens, i, nodes[-1])
            i = alinea_lexer.skip_spaces(tokens, i)
        if tokens[i] == u'et':
            i += 2
            nodes.append(create_node(parent, {'type':TYPE_ARTICLE_REFERENCE}))
            i = parse_article_id(tokens, i, nodes[-1])
        # i = parse_article_part_reference(tokens, i, node)
        # de la loi
        # de l'ordonnance
        # du code
        # les mots
        # l'alinéa
        i = parse_one_of(
            [
                parse_law_reference,
                parse_code_reference,
                parse_word_reference,
                parse_alinea_reference
            ],
            tokens,
            i,
            node
        )
        # if there are are descendant *-reference nodes parsed by the previous call to
        # parse_one_of, we must make sure they apply to all the article-reference nodes
        # we just created
        if len(node['children']) != 0:
            for n in nodes:
                for c in node['children']:
                    push_node(n, copy_node(c))
        return i
    # elif tokens[i] == u'un' and tokens[i + 2] == u'article':
    #     i += 4
    # Article {articleNumber}
    elif tokens[i].lower().startswith(u'article'):
        i += 1
        i = alinea_lexer.skip_spaces(tokens, i)
        i = parse_article_id(tokens, i, node)
    # le même article
    # du même article
    elif tokens[i].lower() in [u'le', u'du'] and tokens[i + 2] == u'même' and tokens[i + 4] == u'article':
        i += 6
        article_refs = filter_nodes(
            get_root(parent),
            lambda n: 'type' in n and n['type'] == TYPE_ARTICLE_REFERENCE
        )
        # the last one in order of traversal is the previous one in order of syntax
        # don't forget the current node is in the list too => -2 instead of -1
        article_ref = copy_node(article_refs[-2])
        push_node(parent, article_ref)
        remove_node(parent, node)
    else:
        remove_node(parent, node)
        return j

    # i = parse_article_part_reference(tokens, i, node)
    # de la loi
    # de l'ordonnance
    # du code
    # les mots
    # l'alinéa
    i = parse_one_of(
        [
            parse_law_reference,
            parse_code_reference,
            parse_word_reference,
            parse_alinea_reference
        ],
        tokens,
        i,
        node
    )

    # i = parse_quote(tokens, i, node)

    debug(parent, tokens, i, 'parse_article_reference end')

    return i

def parse_position(tokens, i, node):
    if i >= len(tokens):
        return i

    j = i
    # i = alinea_lexer.skip_to_next_word(tokens, i)

    # après
    if tokens[i].lower() == u'après':
        node['position'] = 'after'
        i += 2
    # avant
    elif tokens[i].lower() == u'avant':
        node['position'] = 'before'
        i += 2
    # au début
    elif tokens[i].lower() == u'au' and tokens[i + 2] == u'début':
        node['position'] = 'beginning'
        i += 4
    # à la fin du {article}
    elif tokens[i].lower() == u'à' and tokens[i + 2] == u'la' and tokens[i + 4] == u'fin':
        node['position'] = 'end'
        i += 6
    else:
        return j

    return i

def parse_alinea_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_ALINEA_REFERENCE,
    })
    debug(parent, tokens, i, 'parse_alinea_reference')

    j = i
    i = parse_position(tokens, i, node)
    i = parse_scope(tokens, i, node)
    # le {order} alinéa
    # du {order} alinéa
    # au {order} alinéa
    if tokens[i].lower() in [u'du', u'le', u'au'] and is_number_word(tokens[i + 2]) and tokens[i + 4].startswith(u'alinéa'):
        node['order'] = word_to_number(tokens[i + 2])
        i += 6
    # l'alinéa
    elif tokens[i].lower() == u'l' and tokens[i + 2].startswith(u'alinéa'):
        node['order'] = parse_int(tokens[i + 4])
        i += 6
    # de l'alinéa
    elif tokens[i] == 'de' and tokens[i + 2].lower() == [u'l'] and tokens[i + 4].startswith(u'alinéa'):
        i += 6
    # {order} {partType}
    elif is_number_word(tokens[i].lower()) and tokens[i + 2].startswith(u'alinéa'):
        node['order'] = word_to_number(tokens[i])
        i += 4
    # aux {count} {position} alinéas
    # elif tokens[i].lowers() == u'aux' and is_number_word(tokens[i + 2]) and tokens[i + 6] == u'alinéas':
    # le même alinéa
    elif tokens[i].lower() in [u'le'] and tokens[i + 2] == u'même' and tokens[i + 4] == u'alinéa':
        i += 6
        alinea_refs = filter_nodes(
            get_root(parent),
            lambda n: 'type' in n and n['type'] == TYPE_ALINEA_REFERENCE
        )
        # the lduralex.tree.one in order of traversal is the previous one in order of syntax
        # don't forget the current node is in the list too => -2 instead of -1
        alinea_ref = copy_node(alinea_refs[-2])
        push_node(parent, alinea_ref)
        remove_node(parent, node)
    # du dernier alinéa
    # au dernier alinéa
    # le dernier alinéa
    elif tokens[i].lower() in [u'du', u'au', u'le'] and tokens[i + 2] == u'dernier' and tokens[i + 4] == u'alinéa':
        node['order'] = -1
        i += 6
    # à l'avant dernier alinéa
    elif tokens[i].lower() == u'à' and tokens[i + 4] == u'avant' and tokens[i + 6] == u'dernier' and tokens[i + 8] == u'alinéa':
        node['order'] = -2
        i += 10
    # l'avant-dernier alinéa
    elif tokens[i].lower() == u'l' and tokens[i + 2] == u'avant-dernier' and tokens[i + 4] == u'alinéa':
        node['order'] = -2
        i += 6
    # à l'avant-dernier alinéa
    elif tokens[i].lower() == u'à' and tokens[i + 2] == u'l' and tokens[i + 4] == u'avant-dernier' and tokens[i + 6] == u'alinéa':
        node['order'] = -2
        i += 10
    # alinéa {order}
    elif tokens[i].lower() == u'alinéa' and is_number(tokens[i + 2]):
        node['order'] = parse_int(tokens[i + 2])
        i += 4
    # les alinéas
    # des alinéas
    elif tokens[i].lower() in [u'les', u'des'] and tokens[i + 2] == u'alinéas':
        node['order'] = parse_int(tokens[i + 4])
        i += 5
        i = alinea_lexer.skip_spaces(tokens, i)
        nodes = []
        while tokens[i] == u',':
            nodes.append(create_node(parent, {
                'type': TYPE_ALINEA_REFERENCE,
                'order': parse_int(tokens[i + 2])
            }))
            i += 3
            i = alinea_lexer.skip_spaces(tokens, i)
        if tokens[i] == u'et':
            i += 2
            nodes.append(create_node(parent, {
                'type': TYPE_ALINEA_REFERENCE,
                'order': parse_int(tokens[i])
            }))
            i += 2
        i = parse_article_part_reference(tokens, i, node)
        if len(node['children']) != 0:
            for n in nodes:
                for c in node['children']:
                    push_node(n, copy_node(c))
        return i
    else:
        debug(parent, tokens, i, 'parse_alinea_reference none')
        remove_node(parent, node)
        return j

    i = parse_article_part_reference(tokens, i, node)
    # i = parse_quote(tokens, i, node)

    debug(parent, tokens, i, 'parse_alinea_reference end')

    return i

def parse_sentence_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_SENTENCE_REFERENCE,
    })
    debug(parent, tokens, i, 'parse_sentence_reference')

    j = i
    i = parse_position(tokens, i, node)
    i = parse_scope(tokens, i, node)
    # une phrase
    # la phrase
    if tokens[i].lower() in [u'la', u'une'] and tokens[i + 2] == 'phrase':
        i += 4
    # de la {partNumber} phrase
    elif tokens[i].lower() == u'de' and tokens[i + 2] == u'la' and is_number_word(tokens[i + 4]) and tokens[i + 6] == u'phrase':
        node['order'] = word_to_number(tokens[i + 4])
        i += 8
    # la {partNumber} phrase
    elif tokens[i].lower() == u'la' and is_number_word(tokens[i + 2]) and tokens[i + 4] == u'phrase':
        node['order'] = word_to_number(tokens[i + 2])
        i += 6
    # à la {partNumber} phrase
    # À la {partNumber} phrase
    elif (tokens[i] == u'à' or tokens[i] == u'À') and tokens[i + 2].lower() == u'la' and is_number_word(tokens[i + 4]) and tokens[i + 6] == u'phrase':
        node['order'] = word_to_number(tokens[i + 4])
        i += 8
    # la dernière phrase
    elif tokens[i].lower() == u'la' and tokens[i + 2] == u'dernière' and tokens[i + 4] == u'phrase':
        node['order'] = -1
        i += 6
    # les {n} première phrases
    elif tokens[i].lower() == u'les' and is_number_word(tokens[i + 2]) and tokens[i + 4] == u'premières' and tokens[i + 6] == u'phrases':
        node['order'] = [0, word_to_number(tokens[i + 2])]
        i += 8
    else:
        debug(parent, tokens, i, 'parse_sentence_reference none')
        remove_node(parent, node)
        return j

    i = parse_article_part_reference(tokens, i, node)

    debug(parent, tokens, i, 'parse_sentence_reference end')

    fix_incomplete_references(parent, node)

    return i

def fix_incomplete_references(parent, node):
    if len(parent['children']) >= 2:
        for child in parent['children']:
            if child['type'] == TYPE_INCOMPLETE_REFERENCE:
                # set the actual reference type
                child['type'] = node['type']
                # copy all the child of the fully qualified reference node
                for c in node['children']:
                    push_node(child, copy_node(c))

def parse_back_reference(tokens, i, parent):
    if i >= len(tokens):
        return i
    if tokens[i] == u'Il':
        refs = filter_nodes(
            get_root(parent),
            lambda n: is_reference(n)
        )
        for j in reversed(range(0, len(refs))):
            if get_node_depth(refs[j]) <= get_node_depth(parent):
                push_node(parent, copy_node(refs[j]))
                break
        i += 2
    return i

def parse_incomplete_reference(tokens, i, parent):
    if i >= len(tokens):
        return i
    node = create_node(parent, {
        'type': TYPE_INCOMPLETE_REFERENCE,
    })
    j = i
    i = parse_position(tokens, i, node)
    i = parse_scope(tokens, i, node)
    if tokens[i].lower() == u'à' and tokens[i + 2] in [u'le', u'la'] and is_number_word(tokens[i + 4]):
        node['order'] = word_to_number(tokens[i + 4])
        i += 6
    elif tokens[i].lower() in [u'le', u'la'] and is_number_word(tokens[i + 2]):
        node['order'] = word_to_number(tokens[i + 2])
        i += 4
    elif j == i:
        remove_node(parent, node)
        return j

    return i

def parse_word_reference(tokens, i, parent):
    if i >= len(tokens):
        return i
    node = create_node(parent, {
        'type': TYPE_WORD_REFERENCE
    })
    debug(parent, tokens, i, 'parse_word_reference')
    j = i
    i = alinea_lexer.skip_to_next_word(tokens, i)
    i = parse_position(tokens, i, node)
    i = parse_scope(tokens, i, node)
    # le mot
    # les mots
    # des mots
    if tokens[i].lower() in [u'le', u'les', u'des'] and tokens[i + 2].startswith(u'mot'):
        i = alinea_lexer.skip_to_quote_start(tokens, i)
        i = parse_for_each(parse_quote, tokens, i, node)
        i = alinea_lexer.skip_to_next_word(tokens, i)
        i = parse_reference(tokens, i, node)
    # le nombre
    # le chiffre
    # le taux
    elif tokens[i].lower() == u'le' and tokens[i + 2] in [u'nombre', u'chiffre', u'taux']:
        i = alinea_lexer.skip_to_quote_start(tokens, i)
        i = parse_quote(tokens, i, node)
    # la référence
    # les références
    elif tokens[i].lower() in [u'la', u'les'] and tokens[i + 2].startswith(u'référence'):
        i = alinea_lexer.skip_to_quote_start(tokens, i)
        i = parse_quote(tokens, i, node)
    else:
        debug(parent, tokens, i, 'parse_word_reference none')
        remove_node(parent, node)
        return j
    debug(parent, tokens, i, 'parse_word_reference end')
    return i

def parse_header2_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_HEADER2_REFERENCE
    })
    debug(parent, tokens, i, 'parse_header2_reference')
    j = i
    i = parse_position(tokens, i, node)
    i = parse_scope(tokens, i, node)

    # le {order}° ({multiplicativeAdverb}) ({articlePartRef})
    # du {order}° ({multiplicativeAdverb}) ({articlePartRef})
    # au {order}° ({multiplicativeAdverb}) ({articlePartRef})
    if tokens[i].lower() in [u'le', u'du', u'au'] and re.compile(u'\d+°').match(tokens[i + 2]):
        node['order'] = parse_int(tokens[i + 2])
        i += 4
        i = parse_multiplicative_adverb(tokens, i, node)
        i = parse_article_part_reference(tokens, i, node)
    # le même {order}° ({multiplicativeAdverb}) ({articlePartRef})
    # du même {order}° ({multiplicativeAdverb}) ({articlePartRef})
    # au même {order}° ({multiplicativeAdverb}) ({articlePartRef})
    elif tokens[i].lower() in [u'le', u'du', u'au'] and tokens[i + 2] == u'même' and re.compile(u'\d+°').match(tokens[i + 4]):
        node['order'] = parse_int(tokens[i + 4])
        i += 6
        i = parse_multiplicative_adverb(tokens, i, node)
        i = parse_article_part_reference(tokens, i, node)
    else:
        debug(parent, tokens, i, 'parse_header2_reference none')
        remove_node(parent, node)
        return j
    # i = parse_quote(tokens, i, node)
    debug(parent, tokens, i, 'parse_header2_reference end')
    return i

def parse_header3_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_HEADER3_REFERENCE
    })
    debug(parent, tokens, i, 'parse_header3_reference')
    j = i
    i = parse_position(tokens, i, node)
    i = parse_scope(tokens, i, node)

    # le {orderLetter} ({articlePartRef})
    # du {orderLetter} ({articlePartRef})
    # au {orderLetter} ({articlePartRef})
    if tokens[i].lower() in [u'le', u'du', u'au'] and re.compile(u'^[a-z]$').match(tokens[i + 2]):
        node['order'] = ord(str(tokens[i + 2])) - ord('a') + 1
        i += 4
        i = parse_multiplicative_adverb(tokens, i, node)
        i = parse_article_part_reference(tokens, i, node)
    # le même {orderLetter} ({articlePartRef})
    # du même {orderLetter} ({articlePartRef})
    # au même {orderLetter} ({articlePartRef})
    elif tokens[i].lower() in [u'le', u'du', u'au'] and tokens[i + 2] == u'même' and re.compile(u'^[a-z]$').match(tokens[i + 4]):
        node['order'] = ord(str(tokens[i + 4])) - ord('a') + 1
        i += 6
        i = parse_multiplicative_adverb(tokens, i, node)
        i = parse_article_part_reference(tokens, i, node)
    else:
        debug(parent, tokens, i, 'parse_header3_reference none')
        remove_node(parent, node)
        return j
    # i = parse_quote(tokens, i, node)
    debug(parent, tokens, i, 'parse_header3_reference end')
    return i

def parse_header1_reference(tokens, i, parent):
    if i >= len(tokens):
        return i
    node = create_node(parent, {
        'type': TYPE_HEADER1_REFERENCE,
    })
    debug(parent, tokens, i, 'parse_header1_reference')
    j = i
    i = parse_position(tokens, i, node)
    i = parse_scope(tokens, i, node)
    # le {romanPartNumber}
    # du {romanPartNumber}
    # un {romanPartNumber}
    if tokens[i].lower() in [u'le', u'du', u'un'] and is_roman_number(tokens[i + 2]):
        node['order'] = parse_roman_number(tokens[i + 2])
        i += 4
    else:
        debug(parent, tokens, i, 'parse_header1_reference end')
        remove_node(parent, node)
        return j

    i = parse_article_part_reference(tokens, i, node)
    # i = parse_quote(tokens, i, node)

    debug(parent, tokens, i, 'parse_header1_reference end')

    return i

def parse_article_part_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    # i = alinea_lexer.skip_to_next_word(tokens, i)

    i = parse_one_of(
        [
            parse_alinea_reference,
            parse_sentence_reference,
            parse_word_reference,
            parse_article_reference,
            parse_header1_reference,
            parse_header2_reference,
            parse_header3_reference,
        ],
        tokens,
        i,
        parent
    )

    return i

def parse_quote(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_QUOTE,
        'words': '',
    })

    debug(parent, tokens, i, 'parse_quote')

    i = alinea_lexer.skip_spaces(tokens, i)

    # "
    if tokens[i] == alinea_lexer.TOKEN_DOUBLE_QUOTE_OPEN:
        i += 1
    # # est rédigé(es)
    # # ainsi rédigé(es)
    # # est ainsi rédigé(es)
    # elif (i + 2 < len(tokens) and tokens[i + 2].startswith(u'rédigé')
    #     or (i + 4 < len(tokens) and tokens[i + 4].startswith(u'rédigé'))):
    #     i = alinea_lexer.skip_to_quote_start(tokens, i + 2) + 1
    else:
        remove_node(parent, node)
        return i

    while i < len(tokens) and tokens[i] != alinea_lexer.TOKEN_DOUBLE_QUOTE_CLOSE and tokens[i] != alinea_lexer.TOKEN_NEW_LINE:
        node['words'] += tokens[i]
        i += 1
    node['words'] = node['words'].strip()

    # skipalinea_lexer.TOKEN_DOUBLE_QUOTE_CLOSE
    i += 1
    i = alinea_lexer.skip_spaces(tokens, i)

    debug(parent, tokens, i, 'parse_quote end')

    return i

# Parse the verb to determine the corresponding action (one of 'add', 'delete', 'edit' or 'replace').
def parse_edit(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_EDIT
    })

    debug(parent, tokens, i, 'parse_edit')

    # Supprimer {reference}
    if tokens[i] == u'Supprimer':
        i += 2
        node['editType'] = 'delete'
        i = parse_reference(tokens, i, node)
        return i

    r = i
    # i = parse_for_each(parse_reference, tokens, i, node)
    i = parse_reference_list(tokens, i, node)
    # if we did not parse a reference

    i = alinea_lexer.skip_spaces(tokens, i)

    # if we didn't find any reference as a subject and the subject/verb are not reversed
    if len(node['children']) == 0 and tokens[i] != 'Est' and tokens[i] != 'Sont':
        remove_node(parent, node)
        debug(parent, tokens, i, 'parse_edit none')
        return i
    # i = r

    i = alinea_lexer.skip_tokens(tokens, i, lambda t: t.lower() not in [u'est', u'sont', u'devient'] and not t == u'.')
    if i + 2 >= len(tokens):
        remove_node(parent, node)
        debug(parent, tokens, i, 'parse_edit eof')
        return r

    # sont supprimés
    # sont supprimées
    # est supprimé
    # est supprimée
    # est abrogé
    # est abrogée
    # sont abrogés
    # sont abrogées
    if i + 2 < len(tokens) and (tokens[i + 2].startswith(u'supprimé') or tokens[i + 2].startswith(u'abrogé')):
        node['editType'] = 'delete'
        i = alinea_lexer.skip_to_end_of_line(tokens, i)
    # est ainsi rédigé
    # est ainsi rédigée
    # est ainsi modifié
    # est ainsi modifiée
    elif i + 4 < len(tokens) and (tokens[i + 4].startswith(u'rédigé') or tokens[i + 4].startswith(u'modifié')):
        node['editType'] = 'edit'
        i = alinea_lexer.skip_to_end_of_line(tokens, i)
        i = alinea_lexer.skip_spaces(tokens, i)
        i = parse_definition(tokens, i, node)
    # est remplacé par
    # est remplacée par
    # sont remplacés par
    # sont remplacées par
    elif i + 2 < len(tokens) and (tokens[i + 2].startswith(u'remplacé')):
        node['editType'] = 'replace'
        i += 6
        i = parse_definition(tokens, i, node)
        i = alinea_lexer.skip_to_end_of_line(tokens, i)
    # remplacer
    elif tokens[i].lower() == u'remplacer':
        node['editType'] = 'replace'
        i += 2
        # i = parse_definition(tokens, i, node)
        i = parse_reference(tokens, i, node)
        i = alinea_lexer.skip_to_end_of_line(tokens, i)
        if tokens[i].lower() == 'par':
            i += 2
            i = parse_definition(tokens, i, node)
            i = alinea_lexer.skip_to_end_of_line(tokens, i)
    # est inséré
    # est insérée
    # sont insérés
    # sont insérées
    # est ajouté
    # est ajoutée
    # sont ajoutés
    # sont ajoutées
    elif i + 2 < len(tokens) and (tokens[i + 2].startswith(u'inséré') or tokens[i + 2].startswith(u'ajouté')):
        node['editType'] = 'add'
        i += 4
        i = parse_definition(tokens, i, node)
        i = alinea_lexer.skip_to_end_of_line(tokens, i)
    # est ainsi rétabli
    elif i + 4 < len(tokens) and tokens[i + 4].startswith(u'rétabli'):
        node['editType'] = 'add'
        i = alinea_lexer.skip_to_end_of_line(tokens, i)
        i = alinea_lexer.skip_spaces(tokens, i)
        i = parse_definition(tokens, i, node)
    # est complété par
    elif i + 2 < len(tokens) and tokens[i + 2] == u'complété':
        node['editType'] = 'add'
        i += 6
        # i = parse_definition(tokens, i, node)
        i = parse_definition_list(tokens, i, node)
        # i = alinea_lexer.skip_to_end_of_line(tokens, i)
    # devient
    elif tokens[i] == u'devient':
        node['editType'] = 'rename'
        i += 2
        i = parse_definition(tokens, i, node)
    # est ratifié:
    elif i + 2 < len(tokens) and (tokens[i].lower() == u'est' and tokens[i + 2] == u'ratifié'):
        node['editType']= 'ratified'
        i += 4
    else:
        i = r
        debug(parent, tokens, i, 'parse_edit remove')
        remove_node(parent, node)
        i = parse_raw_article_content(tokens, i, parent)
        i = alinea_lexer.skip_to_end_of_line(tokens, i)
        return i

    # We've parsed pretty much everything we could handle. At this point,
    # there should be no meaningful content. But their might be trailing
    # spaces or ponctuation (often "." or ";"), so we skip to the end of
    # the line.
    i = alinea_lexer.skip_to_end_of_line(tokens, i)

    debug(parent, tokens, i, 'parse_edit end')

    return i

def parse_raw_article_content(tokens, i, parent):
    node = create_node(parent, {
        'type': 'raw-content',
        'content': ''
    })

    debug(parent, tokens, i, 'parse_raw_article_content')

    while i < len(tokens) and tokens[i] != alinea_lexer.TOKEN_NEW_LINE:
        node['content'] += tokens[i]
        i += 1

    if node['content'] == '' or is_space(node['content']):
        remove_node(parent, node)

    debug(parent, tokens, i, 'parse_raw_article_content end')

    return i


def parse_code_name(tokens, i, node):
    while i < len(tokens) and tokens[i] != u',' and tokens[i] != u'est':
        node['id'] += tokens[i]
        i += 1
    node['id'] = node['id'].strip()
    return i

# Parse a reference to a specific or aforementioned code.
# References to a specific code are specified by using the exact name of that code (cf parse_code_name).
# References to an aforementioned code will be in the form of "le même code".
def parse_code_reference(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_CODE_REFERENCE,
        'id': '',
    })

    debug(parent, tokens, i, 'parse_code_reference')

    # code
    if tokens[i] == u'code':
        i = parse_code_name(tokens, i, node)
    # le code
    # du code
    elif tokens[i].lower() in [u'le', u'du'] and tokens[i + 2] == 'code':
        i = parse_code_name(tokens, i + 2, node)
    # le même code
    # du même code
    elif tokens[i].lower() in [u'le', u'du'] and tokens[i + 2] == u'même' and tokens[i + 4] == 'code':
        remove_node(parent, node)
        codeRefs = filter_nodes(
            get_root(parent),
            lambda n: 'type' in n and n['type'] == TYPE_CODE_REFERENCE
        )
        # the lduralex.tree.one in order of traversal is the previous one in order of syntax
        node = copy_node(codeRefs[-1])
        node['children'] = []
        push_node(parent, node)
        # skip "le même code "
        i += 6

    if node['id'] == '' or is_space(node['id']):
        remove_node(parent, node)
    else:
        i = parse_reference(tokens, i, node)

    debug(parent, tokens, i, 'parse_code_reference end')

    return i

def parse_definition_list(tokens, i, parent):
    if i >= len(tokens):
        return i

    i = parse_definition(tokens, i, parent)
    i = alinea_lexer.skip_spaces(tokens, i)
    if ((i + 2 < len(tokens) and tokens[i] == u',' and tokens[i + 2] in [u'à', u'au'])
        or (i + 2 < len(tokens) and tokens[i] == u'et')):
        i = parse_definition_list(tokens, i + 2, parent)
    i = alinea_lexer.skip_spaces(tokens, i)

    # est rédigé(es)
    # ainsi rédigé(es)
    # est ainsi rédigé(es)
    if (i + 2 < len(tokens) and tokens[i + 2].startswith(u'rédigé')
        or (i + 4 < len(tokens) and tokens[i + 4].startswith(u'rédigé'))):
        i += 6
        def_nodes = filter_nodes(parent, lambda x: duralex.tree.is_definition(x))
        for def_node in def_nodes:
            i = alinea_lexer.skip_to_quote_start(tokens, i)
            i = parse_quote(tokens, i, def_node)

    return i

# Parse multiple references separated by comas or the "et" word.
# All the parsed references will be siblings in parent['children'] and reso lve_fully_qualified_references + sort_references
# will take care of reworking the tree to make sure each reference in the list is complete and consistent.
def parse_reference_list(tokens, i, parent):
    if i >= len(tokens):
        return i

    i = parse_reference(tokens, i, parent)
    i = alinea_lexer.skip_spaces(tokens, i)
    if ((i + 2 < len(tokens) and tokens[i] == u',' and tokens[i + 2] in [u'à', u'au'])
        or (i + 2 < len(tokens) and tokens[i] == u'et')):
        i = parse_reference_list(tokens, i + 2, parent)
    i = alinea_lexer.skip_spaces(tokens, i)

    return i

def parse_one_of(fns, tokens, i, parent):
    # i = alinea_lexer.skip_to_next_word(tokens, i)

    if i >= len(tokens):
        return i

    for fn in fns:
        j = fn(tokens, i, parent)
        if j != i:
            return j
        i = j

    return i

def parse_reference(tokens, i, parent):

    # node = create_node(parent, {'type':'reference'})
    node = parent

    j = i
    i = parse_one_of(
        [
            parse_law_reference,
            parse_code_reference,
            parse_code_part_reference,
            parse_section_reference,
            parse_subsection_reference,
            parse_chapter_reference,
            parse_title_reference,
            parse_book_reference,
            parse_article_reference,
            parse_article_part_reference,
            parse_paragraph_reference,
            parse_back_reference,
            parse_incomplete_reference,
            parse_alinea_reference,
            parse_word_reference,
            parse_bill_article_reference,
        ],
        tokens,
        i,
        node
    )

    # if len(node['children']) == 0:
    #     remove_node(parent, node)
    #     return j

    return i

# {romanNumber}.
# u'ex': I., II.
def parse_header1(tokens, i, parent):
    if i >= len(tokens):
        return i

    i = alinea_lexer.skip_spaces(tokens, i)

    node = create_node(parent, {
        'type': TYPE_HEADER1,
    })

    debug(parent, tokens, i, 'parse_header1')

    # skip '{romanNumber}.'
    if is_roman_number(tokens[i]) and tokens[i + 1] == u'.':
        debug(parent, tokens, i, 'parse_header1 found article header-1')
        node['order'] = parse_roman_number(tokens[i])
        i = alinea_lexer.skip_to_next_word(tokens, i + 2)
    else:
        remove_node(parent, node)
        node = parent

    j = i
    i = parse_edit(tokens, i, node)
    i = parse_for_each(parse_header2, tokens, i, node)
    if len(node['children']) == 0:
        i = parse_raw_article_content(tokens, i, node)
        i = parse_for_each(parse_header2, tokens, i, node)

    if len(node['children']) == 0 and parent != node:
        remove_node(parent, node)

    debug(parent, tokens, i, 'parse_header1 end')

    return i

# {number}°
# u'ex': 1°, 2°
def parse_header2(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_HEADER2,
    })

    debug(parent, tokens, i, 'parse_header2')

    i = alinea_lexer.skip_spaces(tokens, i)
    if i < len(tokens) and re.compile(u'\d+°').match(tokens[i]):
        debug(parent, tokens, i, 'parse_header2 found article header-2')

        node['order'] = parse_int(tokens[i])
        # skip {number}°
        i += 2
        i = alinea_lexer.skip_to_next_word(tokens, i)
    else:
        remove_node(parent, node)
        node = parent

    j = i
    i = parse_edit(tokens, i, node)
    i = parse_for_each(parse_header3, tokens, i, node)
    if len(node['children']) == 0 and 'order' in node:
        i = parse_raw_article_content(tokens, i, node)
        i = parse_for_each(parse_header3, tokens, i, node)

    if node != parent and len(node['children']) == 0:
        remove_node(parent, node)

    debug(parent, tokens, i, 'parse_header2 end')

    return i

# {number})
# u'ex': a), b), a (nouveau))
def parse_header3(tokens, i, parent):
    if i >= len(tokens):
        return i

    node = create_node(parent, {
        'type': TYPE_HEADER3,
    })

    debug(parent, tokens, i, 'parse_header3')

    i = alinea_lexer.skip_spaces(tokens, i)
    if i >= len(tokens):
        remove_node(parent, node)
        return i

    match = re.compile('([a-z]+)').match(tokens[i])
    if match and (tokens[i + 1] == u')' or (tokens[i + 2] == u'(' and tokens[i + 5] == u')')):
        node['order'] = ord(match.group()[0].encode('utf-8')) - ord('a') + 1
        # skip'{number}) ' or '{number} (nouveau))'
        if tokens[i + 1] == u')':
            i += 3
        else:
            i += 7
        # i = parse_edit(tokens, i, node)
    else:
        remove_node(parent, node)
        node = parent

    j = i
    i = parse_edit(tokens, i, node)
    if len(node['children']) == 0 and 'order' in node:
        i = parse_raw_article_content(tokens, i, node)

    if node != parent and len(node['children']) == 0:
        remove_node(parent, node)

    debug(parent, tokens, i, 'parse_header3 end')

    return i

def parse_for_each(fn, tokens, i, parent):
    n = parent() if callable(parent) else parent
    test = fn(tokens, i, n)
    if (test == i or len(n['children']) == 0) and callable(parent):
        remove_node(n['parent'], n)

    while test != i:
        i = test
        n = parent() if callable(parent) else parent
        test = fn(tokens, i, n)
        if (test == i or len(n['children']) == 0) and callable(parent):
            remove_node(n['parent'], n)

    return i

def parse_bill_articles(data, parent):
    if 'articles' in data:
        for article_data in data['articles']:
            parse_bill_article(article_data, parent)
    elif 'alineas' in data:
        parse_bill_article(data, parent)

    return data

def parse_bill_article(data, parent):
    node = create_node(parent, {
        'type': TYPE_BILL_ARTICLE,
        'order': 1,
        'isNew': False
    })

    node['order'] = data['order']

    if 'alineas' in data:
        parse_json_alineas(data['alineas'], node)

def parse_json_alineas(data, parent):
    text = alinea_lexer.TOKEN_NEW_LINE.join(value for key, value in list(iter(sorted(data.items()))))
    parent['content'] = text#.decode('utf-8')
    return parse_alineas(text, parent)

def parse_alineas(data, parent):
    tokens = alinea_lexer.tokenize(data.strip())
    parse_for_each(parse_header1, tokens, 0, parent)

    if len(parent['children']) == 0:
        parse_raw_article_content(tokens, 0, parent)

def parse(data, tree):
    # tree = create_node(tree, {'type': 'articles'})
    parse_bill_articles(data, tree)
    return tree


class CaptureVisitor(parsimonious.NodeVisitor):

    def __init__( self, table ):

        self.table = table
        self.captures = {}

    def generic_visit( self, node, visited_children ):

        if node.expr_name in self.table:

            rule_name = node.expr_name
            self.captures[rule_name] = node.text

# vim: set ts=4 sw=4 sts=4 et:
