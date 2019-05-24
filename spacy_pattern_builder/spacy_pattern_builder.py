import itertools
from pprint import pprint
import spacy_pattern_builder.util as util
from spacy_pattern_builder.exceptions import TokensNotFullyConnectedError, DuplicateTokensError, TokenNotInMatchTokens


DEFAULT_BUILD_PATTERN_FEATURE_DICT = {
    'DEP': 'dep_',
    'TAG': 'tag_'
}


def node_name(token):
    return 'node{0}'.format(token.i)


def node_features(token, feature_dict):
    node_features = {
        name: getattr(token, feature) for name, feature in feature_dict.items()
    }
    return node_features


def build_dependency_pattern(doc, match_tokens, feature_dict=DEFAULT_BUILD_PATTERN_FEATURE_DICT, nx_graph=None):
    '''Build a depedency pattern for use with DependencyTreeMatcher that will match the set of tokens provided in "match_tokens". This set of tokens must form a fully connected graph.

    Arguments:
        doc {SpaCy Doc object}
        match_tokens {list} -- Set of tokens to match with the resulting dependency pattern
        token_features {list} -- Attributes of spaCy tokens to match in the pattern
        nx_graph {NetworkX object} -- graph representing the doc dependency tree

    Returns:
        [list] -- Dependency pattern in the format consumed by SpaCy's DependencyTreeMatcher
    '''
    # Pre-flight checks
    if not nx_graph:
        nx_graph = util.doc_to_nx_graph(doc)
    try:
        doc[0]._.depth
    except AttributeError:
        util.annotate_token_depth(doc)
    connected_tokens = util.smallest_connected_subgraph(
        match_tokens, doc, nx_graph=nx_graph)
    tokens_not_fully_connected = match_tokens != connected_tokens
    if tokens_not_fully_connected:
        raise TokensNotFullyConnectedError('Try expanding the training example to include all tokens in between those you are trying to match. Or, try the "role-pattern-nlp" module which handles this for you.')
    tokens_contain_duplicates = util.list_contains_duplicates(match_tokens)
    if tokens_contain_duplicates:
        raise DuplicateTokensError('Ensure the match_tokens is a unique list of tokens.')
    match_tokens = util.sort_by_depth(match_tokens)  # We'll iterate through tokens in descending depth order
    root_token = match_tokens[0]
    dependency_pattern = []
    for i, token in enumerate(match_tokens):
        features = node_features(token, feature_dict)
        is_root = token == root_token
        if is_root:  # This is the first element of the pattern
            pattern_element = {'SPEC': {'NODE_NAME': node_name(token)}, 'PATTERN': features}
            dependency_pattern.append(pattern_element)
        else:
            head = token.head
            if head not in match_tokens:
                raise TokenNotInMatchTokensError('Head token not in match_tokens. Is match_tokens fully connected?')
            pattern_element = {
                'SPEC': {
                    'NODE_NAME': node_name(token),
                    'NBOR_NAME': node_name(head),
                    'NBOR_RELOP': '>'
                },
                'PATTERN': features
            }
            dependency_pattern.append(pattern_element)
    return dependency_pattern
