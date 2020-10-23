import tensorflow as tf
import tensorflow_datasets as tfds


def _normalize_img(img, label):
    img = tf.cast(img, tf.float32) / 255.0
    return (img, label)


train_dataset, test_dataset = tfds.load(
    name="dataset", split=["train", "test"], as_supervised=True
)

# Build your input pipelines
train_dataset = train_dataset.shuffle(1024).batch(32)
train_dataset = train_dataset.map(_normalize_img)

test_dataset = test_dataset.batch(32)
test_dataset = test_dataset.map(_normalize_img)
