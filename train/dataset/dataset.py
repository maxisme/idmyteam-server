import os
from collections import Iterator
from typing import Tuple

import tensorflow_datasets as tfds
import tensorflow as tf
from tensorflow_datasets.core.tfrecords_writer import Example
from tensorflow_datasets.scripts.documentation.dataset_markdown_builder import Key


class MyDataset(tfds.core.GeneratorBasedBuilder):
    """DatasetBuilder for my_dataset dataset."""

    VERSION = tfds.core.Version("1.0.0")

    def _info(self) -> tfds.core.DatasetInfo:
        """Dataset metadata (homepage, citation,...)."""
        return tfds.core.DatasetInfo(
            builder=self,
            features=tfds.features.FeaturesDict(
                {
                    "image": tfds.features.Image(shape=(256, 256, 3)),
                    "label": tfds.features.ClassLabel(names=["no", "yes"]),
                }
            ),
        )

    def _split_generators(self, dl_manager: tfds.download.DownloadManager):
        """Download the data and define splits."""
        extracted_path = dl_manager.download_and_extract("http://data.org/data.zip")
        train_path = os.path.join(extracted_path, "train_images")
        test_path = os.path.join(extracted_path, "test_images")
        # `**gen_kwargs` are forwarded to `_generate_examples`
        return [
            tfds.core.SplitGenerator("train", gen_kwargs=dict(path=train_path)),
            tfds.core.SplitGenerator("test", gen_kwargs=dict(path=test_path)),
        ]

    def _generate_examples(self, path) -> Iterator[Tuple[Key, Example]]:
        """Generator of examples for each split."""
        for filename in tf.io.gfile.listdir(path):
            # Yields (key, example)
            yield filename, {
                "image": os.path.join(path, filename),
                "label": "yes" if filename.startswith("yes_") else "no",
            }
