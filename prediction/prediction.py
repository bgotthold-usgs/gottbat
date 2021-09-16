import logging
import os.path
import pickle
import json

import numpy as np
from sklearn.cluster import KMeans
from tensorflow import keras
from collections import Counter

logging.root.setLevel(logging.INFO)

os.environ['TF_XLA_FLAGS'] = '--tf_xla_enable_xla_devices'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'


class Prediction():

    def __init__(self, img_height, img_width, img_channels):
        self.img_height = img_height
        self.img_width = img_width
        self.img_channels = img_channels
        self.MODEL_NAME = 'm-1'
        self.DIRNAME = os.path.dirname(__file__)
        self.MODEL = keras.models.load_model(os.path.join(
            self.DIRNAME, 'tf-models/{}'.format(self.MODEL_NAME)))
        with open(os.path.join(self.DIRNAME, 'tf-models/training_history_{}.p'.format(self.MODEL_NAME)), 'rb') as fp:
            self.CLASS_NAMES = pickle.load(fp)[1]

    # def predict_image(self, img):
    #     batch = np.zeros(
    #         (1, self.img_height, self.img_width, self.img_channels))
    #     batch[0] = img
    #     return self.MODEL.predict(batch)

    def predict_images(self, data):
        if len(data) == 0:
            return []
        b1 = np.zeros(
            (len(data), self.img_height, self.img_width, self.img_channels))

        b2 = np.zeros(
            (len(data), 53))
        for i, d in enumerate(data):
            b1[i] = d[0]
            b2[i] = d[1]

        return self.MODEL.predict([b2, b1], batch_size=len(data))

    def predict_file(self, db_predictions, frequency_k_means, confidence_thresh=0):
        values = []
        [values.append(x[0]) for x in db_predictions if x[0] not in values]
        db_predictions = [[y for y in db_predictions if y[0] == x]
                          for x in values]

        species_predictions = json.loads(json.dumps(
            [[]] * len(np.unique(frequency_k_means))))
        for i, p in enumerate(db_predictions):
            predictions = [x[2] for x in p]
            best_index = np.argmax(predictions)
            if p[best_index][2] > (confidence_thresh + 0.001)/100:
                species_predictions[frequency_k_means[i]].append(
                    p[best_index][1])
            else:
                species_predictions[frequency_k_means[i]].append(None)

        counts = []
        for sp in species_predictions:
            most_common = Counter(sp).most_common()
            counts.append([c for c in most_common if c[0]
                          != None or len(most_common) == 1])
        return (counts, species_predictions)

    def frequency_k_means(self, frequencies, k=2):
        if len(frequencies) >= 2 and max(frequencies) - min(frequencies) > 9000:
            frequencies = np.array([(f, 0) for f in frequencies])
            k_means = KMeans(n_clusters=k)
            k_means.fit(frequencies)
            k_means.predict(frequencies)
            y_k_means = k_means.predict(frequencies)

            # first group is always 0 to orevent flip flopping
            centers = [x[0] for x in k_means.cluster_centers_]
            if y_k_means[0] == 1:
                y_k_means = 1-y_k_means
                centers.reverse()

            return y_k_means, centers
        else:
            return [0] * len(frequencies), [np.mean(frequencies)]
