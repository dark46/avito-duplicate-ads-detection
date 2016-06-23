#!/bin/bash

# This script is to generate image feature
# Prerequisite: ../data/data_files/image_itemPairs_train.csv and ../data/data_files/image_itemPairs_test.csv
# To generate them, execute: cd ../data && python image_item_pair.py

# Generate image feature in parallel
function work(){
 csvcut -c 'images_array_1,images_array_2' | csvjson --stream \
 |  python ../feature/mxnet_feature.py | in2csv -f ndjson

}

# Generate image feature for training data set and testing data set
head -n 1000 ../data/data_files/image_itemPairs_train.csv | work #> ../data/data_files/mxnet_feature_train.head.csv
#cat ../data/data_files/image_itemPairs_train.csv | work > ../data/data_files/image_feature_train.csv
#cat ../data/data_files/image_itemPairs_test.csv | work > ../data/data_files/image_feature_test.csv