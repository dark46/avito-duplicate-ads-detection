#!/usr/bin/env python

import cv2
import numpy as np
import logging
import sys
import mxnet as mx
from skimage import io, transform
from skimage.color import gray2rgb

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='mxnet_feature.log',
                    filemode='a')

__all__ = [ 'mxnet_model_parent_dir', 'mxnet_model_dir_prefix', 'mxnet_mean_img_path', 'init_models', 'batch_image_mxnet_feature', 'compare_images_batch', 'cos_sim']



# root of image locations
images_dir = "/home/hzqianfeng/work/avito-duplicate-ads-detection/images"

# 模型文件放置的顶级目录
mxnet_model_parent_dir = "/home/hzqianfeng/work/avito-duplicate-ads-detection/mxnetmodels"

# 模型文件名称作为键，模型文件的目录、模型前缀和epoch数量作为值
mxnet_model_dir_prefix = {"bn" : ("inception-bn", "Inception_BN", 39), 
                  "v3" : ("inception-v3", "Inception-7", 1), 
                  "21k" : ("inception-21k", "Inception", 9)}

mxnet_mean_img_path = {"bn" : "mean_224.nd"}


def init_models(mxnet_model_parent_dir,mxnet_model_dir_prefix, mxnet_mean_img_path):
    models_dict = {}
    mean_img_dict = {}
    #遍历所有的模型
    for (name,(dir, prefix, num_epoch)) in mxnet_model_dir_prefix.items() :
        model = mx.model.FeedForward.load(mxnet_model_parent_dir + "/" + dir + "/" + prefix, num_epoch, ctx=mx.gpu(), numpy_batch_size=100)
        # get internals from model's symbol
        internals = model.symbol.get_internals()
        # get feature layer symbol out of internals
        fea_symbol = internals["global_pool_output"]
        # Make a new model by using an internal symbol. We can reuse all parameters from model we trained before
        # In this case, we must set ```allow_extra_params``` to True
        # Because we don't need params from FullyConnected symbol
        feature_extractor = mx.model.FeedForward(ctx=mx.gpu(1), symbol=fea_symbol, numpy_batch_size=100,
                                         arg_params=model.arg_params, aux_params=model.aux_params,
                                         allow_extra_params=True)
        models_dict[name] = feature_extractor
        if name in mxnet_mean_img_path.keys() :
            mean_img_dict[name] = mx.nd.load(mxnet_model_parent_dir + "/" + dir + "/" + mxnet_mean_img_path.get(name))["mean_img"]
    return (models_dict, mean_img_dict)

def preprocess_image(path, mean_img, method, show_img=False):
    """
    预处理图像
    path: 图像位置
    mean_img: 均值图像
    method: 使用哪种预处理方式
    """
    # load image
    img = io.imread(path)
    if (len(img.shape) == 2):
        img = gray2rgb(img)
    # we crop image from center
    short_egde = min(img.shape[:2])
    yy = int((img.shape[0] - short_egde) / 2)
    xx = int((img.shape[1] - short_egde) / 2)
    crop_img = img[yy : yy + short_egde, xx : xx + short_egde]
    
    def precess_helper(resize_l, resize_r) :
        # resize to 224, 224
        resized_img = transform.resize(crop_img, (resize_l, resize_r))
        # convert to numpy.ndarray
        sample = np.asarray(resized_img) * 256
        # swap axes to make image from (224, 224, 4) to (3, 224, 224)
        sample = np.swapaxes(sample, 0, 2)
        sample = np.swapaxes(sample, 1, 2)
        return sample
    
    if method == "bn":
        sample = precess_helper(224, 224)
        # sub mean 
        normed_img = sample - mean_img.asnumpy()
        return normed_img.reshape([1, 3, 224, 224])
    elif method == "v3" :
        sample = precess_helper(299, 299)
        # sub mean
        normed_img = sample - 128.
        normed_img /= 128.
        return normed_img.reshape([1, 3, 299, 299])
    elif method == "21k" :
        sample = precess_helper(224, 224)
        # sub mean 
        normed_img = sample - 117.
        return normed_img.reshape([1, 3, 224, 224])
    else:
        raise Exception('Model Error', method)

#@profile
def batch_image_mxnet_feature(img_ids, models, means):
    """
    批量获得图像特征
    """
    # {{}}
    
    result_dict = dict( (img_id, {}) for img_id in img_ids )
    paths = batch_image_location(img_ids)
    for model_name in models.keys():
        # 获得所有的图像预处理数据
        img_sample = []
        for path in paths:
            if model_name in means.keys():
                img_sample.append(preprocess_image(path, means.get(model_name), model_name, False))
            else:
                img_sample.append(preprocess_image(path, None, model_name, False))
        samples = np.row_stack(img_sample)
        global_pooling_feature = models.get(model_name).predict(samples)
        result = []
        for i in range(len(paths)):
            img_id = img_ids[i]
            result_dict[img_id][model_name] =  global_pooling_feature[i,:,0,0].tolist()
    return result_dict
            
        
# 根据图片ID获得图片的具体路径
def image_location(image_id):
    """
    Get image location from image ID
    """
    first_index = str(int(int(image_id) % 100 / 10))
    second_index = str(int(image_id) % 100)
    return ''.join([images_dir, "/Images_", first_index, "/", second_index, "/", str(image_id).strip(), ".jpg"])

# 批量获得图片路径
def batch_image_location(image_ids):
    """
    Get images location from image IDs
    """
    img_locs = [ image_location(img_id) for img_id in image_ids ]
    return img_locs

#@profile
def batch_img_pair_mxnet_features(img_pairs, models, img_means):
    """
    批量获得特征
    img_pairs: 图片对列表  [([1,2,3],[4,5,6]), ([1,2,3],[4,5,6])], 一些元组的集合，元组第一个是左边，第二个是右边
    """
    img_ids = sum([ a + b for a,b in img_pairs], [])
    return batch_image_mxnet_feature(img_ids, models, img_means)
    

def compare_images_from_minority(img_features_l, img_features_r, comp_func):
    """
    对一对图像进行相似度计算
    输入是mxnet的特征
    """
    #保持长度短的在左边
    if len(img_features_l) > len(img_features_r):
        img_features_l, img_features_r = img_features_r, img_features_l
    # 最小的相似度     
    batch_min_sim = sys.maxsize
    # 最大的相似度
    batch_max_sim = -sys.maxsize
    # 相似度的和
    sum_sim = 0
    for img_f_l in img_features_l:
        # 图片相似度，选择右边和当前图片相似度最接近的作为这个值
        img_sim = -sys.maxsize
        for img_f_r in img_features_r:
            sim = comp_func(img_f_l, img_f_r)
            if sim is not np.nan and img_sim < sim:
                img_sim = sim
        if batch_min_sim > img_sim:
            batch_min_sim = img_sim
        if batch_max_sim < img_sim:
            batch_max_sim = img_sim
        sum_sim += img_sim
    return [batch_min_sim, batch_max_sim, sum_sim / len(img_features_l) ]

#@profile
def compare_images_batch(img_ids_pairs, models, means, comp_func):
    """
    获得最终的相似度
    """
    # 获得有哪些特征类型，如bn、v3、21k，进行排序，确保知道输出的情况
    feature_types = [ key for key in models.keys()]
    feature_types.sort()
    # 获得所有图片ID对应的特征
    img_features = batch_img_pair_mxnet_features(img_ids_pairs, models, means)
    # 整理为训练样本那样的特征对，如左边图片对应的特征列表和右边图片对应的特征列表 [([左边的特征列表],[右边的特征列表]),([],[])]
    result = []
    for img_ids_pair in img_ids_pairs:
        if len(img_ids_pair[0]) <=0 or len(img_ids_pair[1]) <=0:
            result.append(dict( (x, [np.nan] * 3) for x in feature_types ))
        else :    
            # 获得各自商品的图片特征, 结果如 [{"bn":feature, "21k":feature}]
            img_feature_l = [ img_features[img_id_l] for img_id_l in img_ids_pair[0] ]
            img_feature_r = [ img_features[img_id_r] for img_id_r in img_ids_pair[1] ]
            img_sim = {}
            for feature_type in feature_types:
                # 获得当前特征方式的所有特征
                img_feature_l_t = [ feature[feature_type] for feature in img_feature_l ]
                img_feature_r_t = [ feature[feature_type] for feature in img_feature_r ]
                sims = compare_images_from_minority(img_feature_l_t, img_feature_r_t, comp_func)
                img_sim[feature_type] = sims
            result.append(img_sim)
    return result

def cos_sim(v1, v2):
    vv1 = np.asarray(v1)
    vv2 = np.asarray(v2)
    return vv1.dot(vv2) / (np.linalg.norm(vv1, 2) * np.linalg.norm(vv2, 2))

def parse_int_list(x):
    return list(map(int, [x for x in x.split(', ') if len(x)>0]))


if __name__ == '__main__':
    """ Generate image feature in parallel
        Input is from stdin, output is to stdout
    """
    import sys
    import json
    # 获得所有的模型
    (models, means) = init_models(mxnet_model_parent_dir, mxnet_model_dir_prefix, mxnet_mean_img_path)
    jsonify = lambda x: json.dumps(x, ensure_ascii=False)
    # 每次处理多少行的数据
    batch_line_size = 100
    f = open('test.txt')
    while True:
        line_count = 0
        img_ids_pairs = []
        for line in f:
            line = json.loads(line.rstrip())
            img_ids_pairs.append((parse_int_list(line['images_array_1']), parse_int_list(line['images_array_2'])))
            line_count += 1
            if line_count == batch_line_size:
                break
        if line_count == 0:
            break
        else:
            result = compare_images_batch(img_ids_pairs, models, means, cos_sim)
            for x in result:
                print(jsonify(x))