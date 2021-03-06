from .item import get_item
from .original import item_pairs_train, item_pairs_test
from . import generate_with_cache
import pandas as pd
from .aggregation_feature import *

__all__ = ['gen_features',
           'simple_features_train', 'simple_features_test',
           'title_features_train', 'title_features_test',
           'description_features_train', 'description_features_test',
           'aggregation_features_train', 'aggregation_features_test',
           'ncd_features_train', 'ncd_features_test']

from feature import *


def gen_features(g, pairs):
    X = []
    for i, j in zip(pairs['itemID_1'], pairs['itemID_2']):
        a = get_item(i)
        b = get_item(j)
        X.append(g(a, b))
    return pd.DataFrame(X)


simple_features_train = generate_with_cache('simple_features_train',
                                            lambda: gen_features(gen_simple_feature, item_pairs_train))
simple_features_test = generate_with_cache('simple_features_test',
                                           lambda: gen_features(gen_simple_feature, item_pairs_test))
title_features_train = generate_with_cache('title_features_train',
                                           lambda: gen_features(gen_title_feature, item_pairs_train))
title_features_test = generate_with_cache('title_features_test',
                                          lambda: gen_features(gen_title_feature, item_pairs_test))
description_features_train = generate_with_cache('description_features_train',
                                                 lambda: gen_features(gen_description_feature, item_pairs_train))
description_features_test = generate_with_cache('description_features_test',
                                                lambda: gen_features(gen_description_feature, item_pairs_test))
aggregation_features_train = generate_with_cache('aggregation_features_train',
                                                 lambda: gen_features(gen_aggregation_feature, item_pairs_train))
aggregation_features_test = generate_with_cache('aggregation_features_test',
                                                lambda: gen_features(gen_aggregation_feature, item_pairs_test))

ncd_features_train = generate_with_cache('ncd_features_train',
                                            lambda: gen_features(gen_ncd_feature, item_pairs_train))
ncd_features_test = generate_with_cache('ncd_features_test',
                                           lambda: gen_features(gen_ncd_feature, item_pairs_test))