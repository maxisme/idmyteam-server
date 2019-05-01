# code 100% comes from https://github.com/VisualComputingInstitute/triplet-reid/blob/master/loss.py
import numbers
import tensorflow as tf


def all_diffs(a, b):
    """ Returns a tensor of all combinations of a - b.

    Args:
        a (2D tensor): A batch of vectors shaped (B1, F).
        b (2D tensor): A batch of vectors shaped (B2, F).

    Returns:
        The matrix of all pairwise differences between all vectors in `a` and in
        `b`, will be of shape (B1, B2).

    Note:
        For convenience, if either `a` or `b` is a `Distribution` object, its
        mean is used.
    """
    return tf.expand_dims(a, axis=1) - tf.expand_dims(b, axis=0)


def cdist(a, b, metric='euclidean'):
    """Similar to scipy.spatial's cdist, but symbolic.

    The currently supported metrics can be listed as `cdist.supported_metrics` and are:
        - 'euclidean', although with a fudge-factor epsilon.
        - 'sqeuclidean', the squared euclidean.
        - 'cityblock', the manhattan or L1 distance.

    Args:
        a (2D tensor): The left-hand side, shaped (B1, F).
        b (2D tensor): The right-hand side, shaped (B2, F).
        metric (string): Which distance metric to use, see notes.

    Returns:
        The matrix of all pairwise distances between all vectors in `a` and in
        `b`, will be of shape (B1, B2).

    Note:
        When a square root is taken (such as in the Euclidean case), a small
        epsilon is added because the gradient of the square-root at zero is
        undefined. Thus, it will never return exact zero in these cases.
    """
    with tf.name_scope("cdist"):
        diffs = all_diffs(a, b)
        if metric == 'sqeuclidean':
            return tf.reduce_sum(tf.square(diffs), axis=-1)
        elif metric == 'euclidean':
            return tf.sqrt(tf.reduce_sum(tf.square(diffs), axis=-1) + 1e-12)
        elif metric == 'cityblock':
            return tf.reduce_sum(tf.abs(diffs), axis=-1)
        else:
            raise NotImplementedError(
                'The following metric is not implemented by `cdist` yet: {}'.format(metric))
cdist.supported_metrics = [
    'euclidean',
    'sqeuclidean',
    'cityblock',
]


def get_at_indices(tensor, indices):
    """ Like `tensor[np.arange(len(tensor)), indices]` in numpy. """
    counter = tf.range(tf.shape(indices, out_type=indices.dtype)[0])
    return tf.gather_nd(tensor, tf.stack((counter, indices), -1))


def apply_margin(x, margin):
    if isinstance(margin, numbers.Real):
        return tf.maximum(x + margin, 0.0)
    elif margin == 'soft':
        return tf.nn.softplus(x)
    elif margin.lower() == 'none':
        return x
    else:
        raise NotImplementedError(
            'The margin {} is not implemented in batch_hard'.format(margin))


def _generic_batchloss(dists, pids, margin, batch_precision_at_k=None, variant='hard'):
    """Computes the batch-hard loss from arxiv.org/abs/1703.07737.

    Args:
        dists (2D tensor): A square all-to-all distance matrix as given by cdist.
        pids (1D tensor): The identities of the entries in `batch`, shape (B,).
            This can be of any type that can be compared, thus also a string.
        margin: The value of the margin if a number, alternatively the string
            'soft' for using the soft-margin formulation, or `None` for not
            using a margin at all.

    Returns:
        A 1D tensor of shape (B,) containing the loss value for each sample.
    """
    with tf.name_scope("batch_hard"):
        same_identity_mask = tf.equal(tf.expand_dims(pids, axis=1),
                                      tf.expand_dims(pids, axis=0))
        negative_mask = tf.logical_not(same_identity_mask)
        positive_mask = tf.logical_xor(same_identity_mask,
                                       tf.eye(tf.shape(pids)[0], dtype=tf.bool))

        if variant == 'sample':
            # -inf gives that index a probability of zero.
            neg_infs = -tf.constant(float('inf'))*tf.ones_like(dists)
            # higher logits are more likely to be sampled.
            pos_logits = tf.where(positive_mask, dists, neg_infs)
            pos_indices = tf.multinomial(pos_logits, num_samples=1)[:,0]
            positive = get_at_indices(dists, pos_indices)

            # Same for the negatives, but we need to turn the logits around,
            # since we want to sample the smaller distances more likely.
            neg_logits = tf.where(negative_mask, -dists, neg_infs)
            neg_indices = tf.multinomial(neg_logits, num_samples=1)[:,0]
            negative = get_at_indices(dists, neg_indices)
        elif variant == 'hard':
            # Furthest one is worst positive.
            positive = tf.reduce_max(dists*tf.cast(positive_mask, tf.float32), axis=1)
            # Closest one is worst negative.
            negative = tf.map_fn(lambda x: tf.reduce_min(tf.boolean_mask(x[0], x[1])),
                                 (dists, negative_mask), tf.float32)
            # negative = tf.reduce_min(dists + 1e5*tf.cast(same_identity_mask, tf.float32), axis=1)

        losses = apply_margin(positive - negative, margin)

    return return_with_extra_stats(losses, dists, batch_precision_at_k,
                                   same_identity_mask,
                                   positive_mask, negative_mask)

def batch_hard(dists, pids, margin, batch_precision_at_k=None):
    return _generic_batchloss(dists, pids, margin, batch_precision_at_k, variant='hard')


def batch_sample(dists, pids, margin, batch_precision_at_k=None):
    return _generic_batchloss(dists, pids, margin, batch_precision_at_k, variant='sample')


def batch_all(dists, pids, margin, batch_precision_at_k=None):
    with tf.name_scope("batch_hard"):
        same_identity_mask = tf.equal(tf.expand_dims(pids, axis=1),
                                      tf.expand_dims(pids, axis=0))
        negative_mask = tf.logical_not(same_identity_mask)
        positive_mask = tf.logical_xor(same_identity_mask,
                                       tf.eye(tf.shape(pids)[0], dtype=tf.bool))

        # Unfortunately, foldl can only go over one tensor, unlike map_fn,
        # so we need to convert and stack around.
        packed = tf.stack([dists,
                           tf.cast(positive_mask, tf.float32),
                           tf.cast(negative_mask, tf.float32)], axis=1)

        def per_anchor(accum, row):
            # `dists_` is a 1D array of distance (row of `dists`)
            # `poss_` is a 1D bool array marking positives.
            # `negs_` is a 1D bool array marking negatives.
            dists_, poss_, negs_ = row[0], row[1], row[2]

            # Now construct a (P,N)-matrix of all-to-all (anchor-pos - anchor-neg).
            diff = all_diffs(tf.boolean_mask(dists_, tf.cast(poss_, tf.bool)),
                             tf.boolean_mask(dists_, tf.cast(negs_, tf.bool)))

            losses = tf.reshape(apply_margin(diff, margin), [-1])
            return tf.concat([accum, losses], axis=0)

        # Some very advanced trickery in order to get the initialization tensor
        # to be an empty 1D tensor with a dynamic shape, such that it is
        # allowed to grow during the iteration.
        init = tf.placeholder_with_default([], shape=[None])
        losses = tf.foldl(per_anchor, packed, init)

    return return_with_extra_stats(losses, dists, batch_precision_at_k,
                                   same_identity_mask,
                                   positive_mask, negative_mask)


def return_with_extra_stats(to_return, dists, batch_precision_at_k,
                            same_identity_mask, positive_mask, negative_mask):
    if batch_precision_at_k is None:
        return to_return

    # For monitoring, compute the within-batch top-1 accuracy and the
    # within-batch precision-at-k, which is somewhat more expressive.
    with tf.name_scope("monitoring"):
        # This is like argsort along the last axis. Add one to K as we'll
        # drop the diagonal.
        _, indices = tf.nn.top_k(-dists, k=batch_precision_at_k+1)

        # Drop the diagonal (distance to self is always least).
        indices = indices[:,1:]

        # Generate the index indexing into the batch dimension.
        # This is simething like [[0,0,0],[1,1,1],...,[B,B,B]]
        batch_index = tf.tile(
            tf.expand_dims(tf.range(tf.shape(indices)[0]), 1),
            (1, tf.shape(indices)[1]))

        # Stitch the above together with the argsort indices to get the
        # indices of the top-k of each row.
        topk_indices = tf.stack((batch_index, indices), -1)

        # See if the topk belong to the same person as they should, or not.
        topk_is_same = tf.gather_nd(same_identity_mask, topk_indices)

        # All of the above could be reduced to the simpler following if k==1
        #top1_is_same = get_at_indices(same_identity_mask, top_idxs[:,1])

        topk_is_same_f32 = tf.cast(topk_is_same, tf.float32)
        top1 = tf.reduce_mean(topk_is_same_f32[:,0])
        prec_at_k = tf.reduce_mean(topk_is_same_f32)

        # Finally, let's get some more info that can help in debugging while
        # we're at it!
        negative_dists = tf.boolean_mask(dists, negative_mask)
        positive_dists = tf.boolean_mask(dists, positive_mask)

        return to_return, top1, prec_at_k, topk_is_same, negative_dists, positive_dists


# Adaptive weights
def softmax_weights(dist, mask):
    max = tf.reduce_max(dist * mask, axis=1)
    max_v = tf.expand_dims(max,1)
    max_r = tf.tile(max_v,[1, tf.shape(mask)[1] ])
    diff = dist - max_r
    Z = tf.reduce_sum(tf.exp(diff) * mask,axis=1) + 1e-6 # avoid division by zero
    W = tf.exp(diff) * mask / tf.expand_dims(Z,1)

    return W


def weighted_triplet(dists, pids, margin, batch_precision_at_k=None):
    """Computes the adaptive weighted triplet loss
    Args:
        dists (2D tensor): A square all-to-all distance matrix as given by cdist.
        pids (1D tensor): The identities of the entries in `batch`, shape (B,).
            This can be of any type that can be compared, thus also a string.
        margin: The value of the margin if a number, alternatively the string
            'soft' for using the soft-margin formulation, or `None` for not
            using a margin at all.
    Returns:
        A 1D tensor of shape (B,) containing the loss value for each sample.
    """
    with tf.name_scope("batch_hard"):
        same_identity_mask = tf.equal(tf.expand_dims(pids, axis=1),
                                      tf.expand_dims(pids, axis=0))
        negative_mask = tf.logical_not(same_identity_mask)
        positive_mask = tf.logical_xor(same_identity_mask,
                                       tf.eye(tf.shape(pids)[0], dtype=tf.bool))

        pos_dist = dists*tf.cast(positive_mask, tf.float32)
        neg_dist = dists*tf.cast(negative_mask, tf.float32)

        pos_weights = softmax_weights(pos_dist, tf.cast(positive_mask, tf.float32))
        neg_weights = softmax_weights(-neg_dist, tf.cast(negative_mask, tf.float32))

        furthest_positive = tf.reduce_sum(pos_dist * pos_weights , axis=1)
        closest_negative = tf.reduce_sum(neg_dist * neg_weights, axis=1)

        diff = furthest_positive - closest_negative
        if isinstance(margin, numbers.Real):
            diff = tf.maximum(diff + margin, 0.0)
        elif margin == 'soft':
            diff = tf.nn.softplus(diff)
        elif margin.lower() == 'none':
            pass
        else:
            raise NotImplementedError(
                'The margin {} is not implemented in batch_hard'.format(margin))

    if batch_precision_at_k is None:
        return diff

    # For monitoring, compute the within-batch top-1 accuracy and the
    # within-batch precision-at-k, which is somewhat more expressive.
    with tf.name_scope("monitoring"):
        # This is like argsort along the last axis. Add one to K as we'll
        # drop the diagonal.
        _, indices = tf.nn.top_k(-dists, k=batch_precision_at_k+1)

        # Drop the diagonal (distance to self is always least).
        indices = indices[:,1:]

        # Generate the index indexing into the batch dimension.
        # This is simething like [[0,0,0],[1,1,1],...,[B,B,B]]
        batch_index = tf.tile(
            tf.expand_dims(tf.range(tf.shape(indices)[0]), 1),
            (1, tf.shape(indices)[1]))

        # Stitch the above together with the argsort indices to get the
        # indices of the top-k of each row.
        topk_indices = tf.stack((batch_index, indices), -1)

        # See if the topk belong to the same person as they should, or not.
        topk_is_same = tf.gather_nd(same_identity_mask, topk_indices)

        # All of the above could be reduced to the simpler following if k==1
        #top1_is_same = get_at_indices(same_identity_mask, top_idxs[:,1])

        topk_is_same_f32 = tf.cast(topk_is_same, tf.float32)
        top1 = tf.reduce_mean(topk_is_same_f32[:,0])
        prec_at_k = tf.reduce_mean(topk_is_same_f32)

        # Finally, let's get some more info that can help in debugging while
        # we're at it!
        negative_dists = tf.boolean_mask(dists, negative_mask)
        positive_dists = tf.boolean_mask(dists, positive_mask)

        return diff, top1, prec_at_k, topk_is_same, negative_dists, positive_dists

LOSS_CHOICES = {
    'batch_hard': batch_hard,
    'batch_sample': batch_sample,
    'batch_all': batch_all,
    'weighted_triplet': weighted_triplet,
}