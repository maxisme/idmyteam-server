#!/usr/bin/env python3
"""
Code adapted from https://github.com/VisualComputingInstitute/triplet-reid/blob/master/train.py
and customised to fit our system.

Which is an implementation of the ideas produced in "In Defense of the Triplet Loss for Person Re-Identification"
"""

from importlib import import_module
import os, time, glob
import numpy as np
import requests
import tensorflow as tf

import plotly.plotly as py
from plotly.grid_objs import Column, Grid

from train import triplet_loss as loss
from settings import config

import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt


def logger(title, message):
    try:
        requests.post('https://notifi.it/api', {
            'credentials': 'SFE82Li5zEzI1Z99ot42nUUeM',
            'title': title,
            'message': message
        })

        requests.post('https://notifi.it/api', {
            'credentials': 'SCqJj4PDPwJtUbn9qyAV6ftFv',
            'title': title,
            'message': message
        })

        requests.post('https://new.boxcar.io/api/notifications', {
            'user_credentials': 'tkCOatNHadLSrs8Mm1jA',
            'notification[title]': message
        })
    except:
        print("Error sending notification")


def fid_to_image(fid, pid, image_size):
    # load image
    image_encoded = tf.read_file(fid)
    image_decoded = tf.image.decode_jpeg(image_encoded, channels=3)

    # resize image
    image_resized = tf.image.resize_images(image_decoded, image_size)

    return image_resized, fid, pid


def sample_k_fids_for_pid(pid, all_fids, all_pids, batch_k):
    """ Given a PID, select K FIDs of that specific PID. """
    possible_fids = tf.boolean_mask(all_fids, tf.equal(all_pids, pid))

    # The following simply uses a subset of K of the possible FIDs
    # if more than, or exactly K are available. Otherwise, we first
    # create a padded list of indices which contain a multiple of the
    # original FID count such that all of them will be sampled equally likely.
    count = tf.shape(possible_fids)[0]
    padded_count = tf.cast(tf.ceil(batch_k / tf.cast(count, tf.float32)), tf.int32) * count
    full_range = tf.mod(tf.range(padded_count), count)

    # Sampling is always performed by shuffling and taking the first k.
    shuffled = tf.random_shuffle(full_range)
    selected_fids = tf.gather(possible_fids, shuffled[:batch_k])

    return selected_fids, tf.fill([batch_k], pid)


################
## variables ###
################
DATA_DIR = "/var/www/idmy.team/python/data-sets/Faces/CROPPED/"

tech = 'batch_hard'  # 'batch_hard' 'batch_sample' 'batch_all' 'weighted_triplet'
arch = 'resnet_v1_50'
batch_p = 18 # num people
batch_k = 2 # num images of person
learning_rate = 4e-5  # 3e-5
epsilon = 1e-8  # 1e-7
optimizer_name = 'Adam'  # Adam MO RMS
train_iterations = int(5e5)
decay_start_iteration = int(4e5) #train_iterations / 10
net_input_size = (config.FEATURE_EXTRACTOR_IMG_SIZE, config.FEATURE_EXTRACTOR_IMG_SIZE)
embedding_dim = 128
margin = 'soft'  # 'soft'
metric = 'euclidean'  # 'sqeuclidean' 'euclidean' 'cityblock'
output_model = config.FEATURE_MODEL_DIR
log_save_every = train_iterations / 200
resume = True  # set to true when wanting to extend team data
OUT_DIR = config.MODEL_DIR + "/save_features_start/"

################
##    run    ###
################

logger('Start', "tech: " + tech + " arch: " + arch + " lr: " + str(learning_rate) + " input: " + str(
    net_input_size) + " metric:" + metric + " epsilon: " + str(
    epsilon) + " optimizer: " + optimizer_name + " batch_k: " + str(batch_k) + " batch_p: " + str(batch_p))

# make out directory
if not os.path.exists(OUT_DIR):
    os.makedirs(OUT_DIR)

"""
PIDs are the "person IDs", i.e. class names/labels.
FIDs are the "file IDs", which are individual relative filenames.
"""
pids, fids = [], []
classes = [path for path in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, path))]
for c in classes:
    for file in glob.glob(DATA_DIR + c + "/*.jpg"):
        pids.append(c)
        fids.append(file)

logger("num people", str(len(classes)))
logger("num images", str(len(fids)))

# Setup a tf.Dataset where one "epoch" loops over all PIDS.
# PIDS are shuffled after every epoch and continue indefinitely.
unique_pids = np.unique(pids)
dataset = tf.data.Dataset.from_tensor_slices(unique_pids)
dataset = dataset.shuffle(len(unique_pids))

# Constrain the dataset size to a multiple of the batch-size, so that
# we don't get overlap at the end of each epoch.
dataset = dataset.take((len(unique_pids) // batch_p) * batch_p)
dataset = dataset.repeat(None)  # Repeat forever. Funny way of stating it.

# For every PID, get K images.
dataset = dataset.map(lambda pid: sample_k_fids_for_pid(
    pid, all_fids=fids, all_pids=pids, batch_k=batch_k))

# Ungroup/flatten the batches for easy loading of the files.
dataset = dataset.apply(tf.contrib.data.unbatch())

# Convert filenames to actual image tensors.
dataset = dataset.map(
    lambda fid, pid: fid_to_image(
        fid, pid,
        image_size=net_input_size),
    num_parallel_calls=4)

# Group it back into PK batches.
batch_size = batch_p * batch_k
dataset = dataset.batch(batch_size)

# Overlap producing and consuming for parallelism.
dataset = dataset.prefetch(1)

# Since we repeat the data infinitely, we only need a one-shot iterator.
images, fids, pids = dataset.make_one_shot_iterator().get_next()

# Create the model and an embedding head.
model = import_module('train.' + arch)
head = import_module('train.fc1024')

# Feed the image through the model. The returned `body_prefix` will be used
# further down to load the pre-trained weights for all variables with this
# prefix.
endpoints, body_prefix = model.endpoints(images, is_training=True)
with tf.name_scope('head'):
    endpoints = head.head(endpoints, embedding_dim, is_training=True)

# Create the loss in two steps:
# 1. Compute all pairwise distances according to the specified metric.
# 2. For each anchor along the first dimension, compute its loss.
dists = loss.cdist(endpoints['emb'], endpoints['emb'], metric=metric)
losses, train_top1, prec_at_k, _, neg_dists, pos_dists = loss.LOSS_CHOICES[tech](
    dists, pids, margin, batch_precision_at_k=batch_k - 1)

# Count the number of active entries, and compute the total batch loss.
num_active = tf.reduce_sum(tf.cast(tf.greater(losses, 1e-5), tf.float32))

loss_mean = tf.reduce_sum(losses) / (1e-33 + tf.count_nonzero(losses, dtype=tf.float32))
# loss_mean = tf.reduce_sum(losses) / (1e-33 + tf.reduce_sum(tf.to_float(tf.greater(losses, 1e-5))))
# loss_mean = tf.reduce_mean(losses)

# These are collected here before we add the optimizer, because depending
# on the optimizer, it might add extra slots, which are also global
# variables, with the exact same prefix.
model_variables = tf.get_collection(
    tf.GraphKeys.GLOBAL_VARIABLES, body_prefix)

# Define the optimizer and the learning-rate schedule.
# Unfortunately, we get NaNs if we don't handle no-decay separately.
global_step = tf.Variable(0, name='global_step', trainable=False)
if 0 <= decay_start_iteration < train_iterations:
    learning_rate = tf.train.exponential_decay(
        learning_rate,
        tf.maximum(0, global_step - decay_start_iteration),
        train_iterations - decay_start_iteration, 0.01)
else:
    learning_rate = learning_rate
tf.summary.scalar('learning_rate', learning_rate)

if optimizer_name == 'Adam':
    optimizer = tf.train.AdamOptimizer(learning_rate, epsilon=epsilon)
elif optimizer_name == 'MO':
    optimizer = tf.train.MomentumOptimizer(learning_rate, momentum=0.9)
elif optimizer_name == 'RMS':
    optimizer = tf.train.RMSPropOptimizer(learning_rate, momentum=0.9, epsilon=epsilon)

# Update_ops are used to update batchnorm stats.
with tf.control_dependencies(tf.get_collection(tf.GraphKeys.UPDATE_OPS)):
    train_op = optimizer.minimize(loss_mean, global_step=global_step)

# Define a saver for the complete model.
checkpoint_saver = tf.train.Saver(max_to_keep=5)

min, mean, max = [], [], []  # for plotting
cp = tf.ConfigProto()
cp.gpu_options.allow_growth = True
with tf.Session(config=cp) as sess:
    if resume:
        print("resuming from last checkpoint")
        # In case we're resuming, simply load the full checkpoint to init.
        last_checkpoint = tf.train.latest_checkpoint(OUT_DIR)
        checkpoint_saver.restore(sess, last_checkpoint)
    else:
        sess.run(tf.global_variables_initializer())

        saver = tf.train.Saver(model_variables)
        # insert 'pre trained' network weights
        saver.restore(sess, config.MODEL_DIR + arch + '.ckpt')

        checkpoint_saver.save(sess, os.path.join(OUT_DIR, 'checkpoint'), global_step=0)

    merged_summary = tf.summary.merge_all()
    start_step = sess.run(global_step)

    grid, plotly_url = None, None
    for i in range(start_step, train_iterations):
        # Compute gradients, update weights
        start_time = time.time()
        _, summary, step, b_prec_at_k, b_embs, b_loss, b_fids = \
            sess.run([train_op, merged_summary, global_step,
                      prec_at_k, endpoints['emb'], losses, fids])
        elapsed_time = time.time() - start_time

        # logger and saver
        if step % log_save_every == 0:
            # save checkpoint
            checkpoint_saver.save(sess, os.path.join(OUT_DIR, 'checkpoint'), global_step=step)
            logger("saved",str(step) + "\t" + str(np.min(b_loss)) + "\t" + str(np.mean(b_loss)) + "\t" + str(np.max(b_loss)))

        # if step > 0 and step % 10 == 0:
        #     #####################
        #     # log to plotly checkpoint #
        #     #####################
        #     try:
        #
        #         cols = [Column(np.around(min, 3), 'Min'), Column(np.around(mean,3), 'Mean'), Column(np.around(max,3), 'Max')]
        #         if not grid:
        #             grid = Grid(cols)
        #             plotly_url = py.grid_ops.upload(grid,
        #                                      filename='Feature Extractor',
        #                                      world_readable=False,
        #                                      auto_open=False)
        #             logger('Created', plotly_url)
        #         else:
        #             logger('Saved '+str(step), plotly_url)
        #             py.grid_ops.append_columns(cols, grid_url=grid)
        #         min, mean, max = [], [], []  # reset plots
        #     except Exception as e:
        #         logger('Faled to log', str(e))


        if np.max(b_loss) < 0.693:  # impressive to fall below this
            logger("low", str(step) + "\t" + str(np.min(b_loss)) + "\t" + str(np.mean(b_loss)) + "\t" + str(np.max(b_loss)))
        print((str(step) + "\t" + str(np.min(b_loss)) + "\t" + str(np.mean(b_loss)) + "\t" + str(np.max(b_loss))))


        # for plotting
        min.append(np.min(b_loss))
        mean.append(np.mean(b_loss))
        max.append(np.max(b_loss))

    checkpoint_saver.save(sess, os.path.join(OUT_DIR, 'final'), global_step=step)

# write plot
fig = plt.figure(figsize=(100, 10), dpi=600)
plt.errorbar(list(range(len(mean))), mean, yerr=(min, max), fmt='o', markersize=6)
plt.savefig(OUT_DIR + 'fe_' + str(learning_rate) + '_' + str(epsilon) + '.jpg', dpi=300)

with open(OUT_DIR + 'loss.csv', 'w') as the_file:
    for i in range(len(min)):
        the_file.write(str(min[i]) + "," + str(mean[i]) + "," + str(max[i]) + "\n")

logger('Finished training FE', OUT_DIR + 'loss.csv')
