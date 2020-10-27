import tensorflow as tf
import tensorflow_addons as tfa


def _normalize_img(img, label):
    img = tf.cast(img, tf.float32) / 255.0
    return (img, label)


dataset = tf.data.Dataset.list_files()

# # Build your input pipelines
# train_dataset = train_dataset.shuffle(1024).batch(32)
# train_dataset = train_dataset.map(_normalize_img)
#
# test_dataset = test_dataset.batch(32)
# test_dataset = test_dataset.map(_normalize_img)


model = tf.keras.Sequential(
    [
        tf.keras.layers.Conv2D(
            filters=64,
            kernel_size=2,
            padding="same",
            activation="relu",
            input_shape=(28, 28, 1),
        ),
        tf.keras.layers.MaxPooling2D(pool_size=2),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Conv2D(
            filters=32, kernel_size=2, padding="same", activation="relu"
        ),
        tf.keras.layers.MaxPooling2D(pool_size=2),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(
            256, activation=None
        ),  # No activation on final dense layer
        tf.keras.layers.Lambda(
            lambda x: tf.math.l2_normalize(x, axis=1)
        ),  # L2 normalize embeddings
    ]
)

# Compile the model
model.compile(
    optimizer=tf.keras.optimizers.Adam(0.001), loss=tfa.losses.TripletSemiHardLoss()
)

history = model.fit(train_dataset, epochs=5)
