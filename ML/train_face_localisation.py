# Train a face localisation model
# code heavily inspired by library documentation: https://github.com/chainer/chainercv/blob/master/examples/faster_rctrain.py
import chainer
from chainer import training
from chainer.training import extensions
from chainer.training.triggers import ManualScheduleTrigger
from chainercv.datasets import TransformDataset
from chainercv.extensions import DetectionVOCEvaluator
from chainercv.links import FasterRCNNVGG16
from chainercv.links.model.faster_rcnn import FasterRCNNTrainChain
from chainercv import transforms


import numpy as np
import os
 
from settings import config
from train import wider_ds as WP


class Transform(object):

    def __init__(self, faster_rcnn):
        self.faster_rcnn = faster_rcnn

    def __call__(self, in_data):
        img, bbox, label = in_data
        _, H, W = img.shape
        img = self.faster_rcnn.prepare(img)
        _, o_H, o_W = img.shape
        scale = o_H / H
        bbox = transforms.resize_bbox(bbox, (H, W), (o_H, o_W))

        # horizontally flip
        img, params = transforms.random_flip(
            img, x_random=True, return_param=True)
        bbox = transforms.flip_bbox(
            bbox, (o_H, o_W), x_flip=params['x_flip'])

        return img, bbox, label, scale


np.random.seed(224332)

# get wider_face_data
train_data = WP.WiderDataset('/var/www/idmy.team/python/data-sets/Faces/WIDER/WIDER_train/images/',
                            '/var/www/idmy.team/python/data-sets/Faces/WIDER/wider_face_split/wider_face_train_bbx_gt.txt')

print("---")
test_data = WP.WiderDataset('/var/www/idmy.team/python/data-sets/Faces/WIDER/WIDER_val/images/',
                           '/var/www/idmy.team/python/data-sets/Faces/WIDER/wider_face_split/wider_face_val_bbx_gt.txt')

# quick check to validate the dataset acquires the correct bbox for an image
bbx = train_data.bboxs['/var/www/idmy.team/python/data-sets/Faces/WIDER/WIDER_train/images/36--Football/36_Football_americanfootball_ball_36_571.jpg']
print(bbx)
print("should be [[112. 398. 365. 595.]]")
print(len(test_data))
print(len(train_data))

###############
## variables ##
###############
iterations = 70000
step_size = 50000
lr = 1e-3
out_dir = config.MODEL_DIR + "/tmp_localisation2/"
out_model = "snapshot.model"
save_every = 1000

# initialise RCNN model with pretrained imagenet model
rcnn = FasterRCNNVGG16(n_fg_class=1, # 1 class as just looking for faces
                       pretrained_model='imagenet')
rcnn.use_preset('evaluate')

# initalise training
model = FasterRCNNTrainChain(rcnn)
model.to_gpu(0)
chainer.cuda.get_device(0).use()

## Dataset
# initialise training data
train_data = TransformDataset(train_data, Transform(rcnn))
train_iter = chainer.iterators.MultiprocessIterator(
        train_data, batch_size=1, shared_mem=100000000)
# initialise testing data
test_iter = chainer.iterators.SerialIterator(test_data, batch_size=1, repeat=False, shuffle=False)


# set model training paramas
optimizer = chainer.optimizers.MomentumSGD(lr=lr, momentum=0.9)
# optimizer = chainer.optimizers.AdaGrad(lr=lr)
optimizer.setup(model)
optimizer.add_hook(chainer.optimizer_hooks.WeightDecay(rate=0.0005))

updater = chainer.training.updater.StandardUpdater(train_iter, optimizer, device=0)

# when training with team data extend from previous model

trainer = training.Trainer(updater, (iterations, 'iteration'), out=out_dir)
trainer.extend(extensions.snapshot_object(model.faster_rcnn, out_model), trigger=(save_every, 'iteration')) # saves the model when finished
trainer.extend(extensions.ExponentialShift('lr', 0.1), trigger=(step_size, 'iteration'))


## LOGGING ##
log_inter = trigger=(20, 'iteration')
trainer.extend(chainer.training.extensions.observe_lr(), trigger=log_inter)
trainer.extend(extensions.LogReport(trigger=log_inter))
trainer.extend(extensions.PrintReport(
    ['iteration', 'epoch', 'elapsed_time',
     'lr',
     'main/loss',
     'main/roi_loc_loss',
     'main/roi_cls_loss',
     'main/rpn_loc_loss',
     'main/rpn_cls_loss',
     'validation/main/map',
     ]), log_inter)
trainer.extend(extensions.ProgressBar(update_interval=10))
##############

# evaluates model by PASCAL VOC metric
trainer.extend(DetectionVOCEvaluator(
        test_iter, model.faster_rcnn, use_07_metric=True),
    trigger=ManualScheduleTrigger(
        [step_size, iterations], 'iteration'))

print("started")
trainer.run()

# move the final trained model
os.rename(out_dir + out_model, config.LOCALISATION_MODEL)