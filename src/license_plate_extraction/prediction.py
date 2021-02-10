from pathlib import Path
import numpy as np
import tensorflow as tf
import data_reader
import settings
import visualization_tools


PREDICTION_MODEL_PATH = settings.MODELS_DIR / "test_02.tf"
prediction_model = tf.keras.models.load_model(PREDICTION_MODEL_PATH)


def predict_bounding_box(image_tensor: tf.Tensor) -> np.ndarray:
    """
    Predicts a bounding box for an image.

    :param image_tensor: A tf.Tensor object containing the image. Shape: [height, width, 3]
    :param model_path: The path where the trained keras model is located.
    :returns: An np.ndarray containing the bounding box prediction in the format [x_min, y_min, width, height] (Percent values).
    """

    # resize image to match model input
    input_height = prediction_model.inputs[0].shape[1]
    input_width = prediction_model.inputs[0].shape[2]
    image_tensor = tf.image.resize(
        image_tensor, size=(input_height, input_width), antialias=True
    )

    image_tensor = tf.reshape(image_tensor, shape=(1, input_height, input_width, 3))

    prediction = prediction_model(image_tensor)[0]

    return prediction.numpy()
