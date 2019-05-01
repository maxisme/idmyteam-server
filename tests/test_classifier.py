# # Used to test our classification abilities of the feature extractor model
# import time, os, random
# from importlib import import_module
#
# import cv2
# from sklearn.externals import joblib
# from sklearn.svm import SVC
#
# from settings import functions, config
# import glob
# import tensorflow as tf
# from chainercv import utils
# import copy
#
# import numpy as np
#
# # variables
# # DATA_DIR = "/var/www/idmy.team/python/data-sets/Faces/vggface/train_cropped/"
# local_test = "/var/www/idmy.team/python/tests/real/"
# DATA_DIR = "/var/www/idmy.team/python/data-sets/Faces/lfw_crop/"
#
# num_tests = 1
#
# num_classes = 20  # number of members
# num_train_images = 10  # num images per member to train with
# num_train_shuffles = 2  # num of random noise added to image to create more train_images
# num_test_images = 1  # number of images to test the trained model with
#
# # threshold = 0.4
# threshold = None
#
# # random.seed(1)
#
# ## load FE model
# model = import_module('train.resnet_v1_50')
# head = import_module('train.fc1024')
# image_placeholder = tf.placeholder(tf.float32, shape=(None, 256, 256, 3))
# endpoints, body_prefix = model.endpoints(image_placeholder, is_training=False)
# with tf.name_scope('head'):
#     endpoints = head.head(endpoints, 128, is_training=False)
# sess = tf.Session()
# tf.train.Saver().restore(sess, '/var/www/idmy.team/python/models/save_features_start/checkpoint-407500')
#
# def get_emb(file, shuffle=False):
#     localisation_coords = functions.read_img_comment(file)
#     img = utils.read_image(file)
#     if localisation_coords:
#         x, y, w, h = functions.add_coord_padding(img, config.CROP_PADDING, localisation_coords['x'],
#                                                  localisation_coords['y'], localisation_coords['width'],
#                                                  localisation_coords['height'])
#         img = functions.crop_img(img, x, y, w, h)
#     if shuffle:
#         img = functions.img_augmentation(img)
#
#     img = functions.preProcessCroppedImage(img, config.FEATURE_EXTRACTOR_IMG_SIZE)
#     emb = sess.run(endpoints['emb'], feed_dict={image_placeholder: [img]})
#     return emb.tolist()
# ######################
#
#
# acu = []
# emb_time = []
# sql_X, sql_y = None, None
# for _ in range(num_tests):
#     classes = [path for path in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, path))]
#     random.shuffle(classes)
#
#     X, y, test_X, test_y = [], [], [], []
#     class_num = num_classes
#     for c in classes:
#         if class_num > 0:
#             images = glob.glob(DATA_DIR+c+"/*.jpg")
#             random.shuffle(images)
#             if len(images) >= num_test_images + num_train_images:
#                 class_num -= 1
#
#                 train_images = images[:num_train_images]
#                 for file in train_images:
#                     X.append(get_emb(file))
#                     y.append(c)
#
#                     for _ in range(num_train_shuffles - 1):
#                         t = time.time()
#                         X.append(get_emb(file, shuffle=True))
#                         emb_time.append(time.time() - t)
#                         y.append(c)
#
#                 for file in images[num_train_images:num_train_images+num_test_images]:
#                     test_X.append(get_emb(file))
#                     test_y.append([c, file])
#         else:
#             break
#
#     sql_X = copy.deepcopy(X)
#     sql_y = copy.deepcopy(y)
#
#     ########################
#     # fetch local test set #
#     ########################
#     local_classes = [path for path in os.listdir(local_test) if os.path.isdir(os.path.join(local_test, path))]
#     for c in local_classes:
#         images = glob.glob(local_test + c + "/*.jpg")
#         random.shuffle(images)
#
#         if len(images) < num_train_images + 1:
#             print("Unable to test real images %s! Too few train images", c)
#             continue
#
#         train_images = images[:num_train_images]
#         for file in train_images:
#             X.append(get_emb(file))
#             y.append(c)
#
#             for _ in range(num_train_shuffles - 1):
#                 X.append(get_emb(file, shuffle=True))
#                 y.append(c)
#
#         test_images = glob.glob(local_test + c + "/test/*.jpg")  # specific images to test
#         test_images.extend(images[num_train_images:])
#         for file in test_images:
#             localisation_coords = functions.read_img_comment(file)
#             test_X.append(get_emb(file))
#             test_y.append([c, file])
#
#     ## fit
#     t = time.time()
#     clf = SVC(kernel='linear', probability=True)
#     n_X = [x[0] for x in np.array(X)]
#     clf.fit(n_X, y)
#     print "SVM fit took: "+str(time.time() - t) +" with "+str(len(X))+" training images{features}."
#
#     ## test
#     classes = clf.classes_
#
#     ind = range(len(test_X))
#     random.shuffle(ind)
#
#     major_errors = 0
#     for a in ind:
#         probabilities = clf.predict_proba(test_X[a])
#         max_prob = 0
#         probs = {}
#         for i, prob in enumerate(probabilities[0]):
#             probs[classes[i]] = prob
#             if prob >= max_prob:
#                 cla = classes[i]
#                 max_prob = prob
#
#         if cla in local_classes:
#             print test_y[a][1]
#             print max_prob
#
#         if threshold and max_prob < threshold:
#             print "UNSURE: " + cla + " should have been: " + test_y[a][0] + " certainty: " + str(max_prob)
#
#         elif cla != test_y[a][0]:
#             print "WRONG: " + cla + " should have been: " + test_y[a][0] +" certainty: "+str(max_prob)
#             if cla in local_classes:
#                 print test_y[a][1]
#             major_errors += 1
#         else:
#             acu.append(max_prob)
#     print str(major_errors)+" out of "+ str(len(ind))+" wrong"
#
#
# # joblib.dump(clf, "/var/www/idmy.team/python/models/39a552b5fa462d26368f542c743b43e8c2f78c11669982ff1390f8cf625a30f0.model")
#
# print("Average feature extractor time:"+ str(sum(emb_time)/float(len(emb_time))))
#
# # print "major errors: "+str(major_errors)
# print "average confidence: " +str(sum(acu)/float(len(acu))) + "from "+ str(len(test_X))+" images"
#
#
# # store init training features for model
# conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
#
# # remove all inits
# x = conn.cursor()
# x.execute("DELETE FROM `Features` "
#           "WHERE `account_username` = 'init'")
# conn.commit()
#
# # store new inits
# if True:
#     last_y = None
#     Y = 1
#     for i in range(len(sql_X)):
#         x = sql_X[i]
#         if sql_y[i] != last_y:
#             Y += 1
#             last_y = sql_y[i]
#         functions.store_feature(conn, "init", "-"+str(Y), x, manual=True)