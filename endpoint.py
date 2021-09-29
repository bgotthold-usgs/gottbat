
import os
import json
import numpy as np
from spectrogram_v2 import Spectrogram
from tensorflow import keras

# SPECIES = [[1, "ANPA", "Pallid bat", 27000, 51000, 1], [2, "CHME", "Mexican long-tongued bat", 4999, 99999, 0], [3, "CORA", "Rafinesque's big-eared bat", 4999, 99999, 0], [4, "COTO", "Townsend's big-eared bat", 22000, 41000, 1], [5, "EPFU", "Big brown bat", 25000, 52000, 1], [6, "EUMA", "Spotted bat", 10000, 17000, 1], [7, "EUFL", "Florida bonneted bat", 10000, 25000, 0], [8, "EUPE", "Greater mastiff bat", 10000, 19000, 1], [9, "EUUN", "Underwood's mastiff bat", 4999, 99999, 0], [10, "IDPH", "Allen's big-eared bat", 14000, 18000, 1], [11, "LANO", "Silver-haired bat", 24000, 44000, 1], [12, "LABL", "Western red bat", 37000, 61000, 1], [13, "LABO", "Eastern red bat", 29000, 73000, 1], [14, "LACI", "Hoary bat", 17000, 49000, 1], [15, "LAEG", "Southern yellow bat", 4999, 99999, 0], [16, "LAIN", "Northern yellow bat", 25000, 41000, 1], [17, "LASE", "Seminole bat", 35000, 52000, 1], [18, "LAXA", "Western yellow bat", 28000, 56000, 0], [19, "LENI", "Greater long-nosed bat", 4999, 99999, 0], [20, "LEYE", "Lesser long-nosed bat", 4999, 99999, 0], [21, "MACA", "California leaf-nosed bat", 28000, 55000, 0], [22, "MOMO", "Pallas's mastiff bat", 4999, 99999, 0], [23, "MOME", "Ghost-faced bat", 4999, 99999, 0], [24, "MYAR", "Southwestern myotis", 33000, 45000, 0], [25, "MYAU", "Southeastern myotis", 42000, 65000, 1], [26, "MYCA", "California myotis", 45000, 95000, 1], [27, "MYCI",
#                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   "Western small-footed myotis", 40000, 71000, 1], [28, "MYEV", "Western long-eared myotis", 31000, 71000, 1], [29, "MYGR", "Gray bat", 41000, 85000, 1], [30, "MYKE", "Keen's myotis", 4999, 99999, 0], [31, "MYLE", "Eastern small-footed myotis", 40000, 71000, 1], [32, "MYLU", "Little brown bat", 38000, 73000, 1], [33, "MYSE", "Northern long-eared bat", 37000, 95000, 1], [34, "MYSO", "Indiana bat", 37000, 70000, 1], [35, "MYTH", "Fringed myotis", 24000, 50000, 1], [36, "MYVE", "Cave myotis", 41000, 49000, 1], [37, "MYVO", "Long-legged myotis", 39000, 89000, 1], [38, "MYYU", "Yuma myotis", 46000, 91000, 1], [39, "NYHU", "Evening bat", 32000, 48000, 1], [40, "NYFE", "Pocketed free-tailed bat", 10000, 41000, 0], [41, "NYMA", "Big free-tailed bat", 12000, 30000, 1], [42, "PAHE", "Canyon bat", 41000, 70000, 1], [43, "PESU", "Tricolored bat", 36000, 50000, 1], [44, "TABR", "Brazilian free-tailed bat", 18000, 46000, 1], [45, "ARJA", "Jamaican fruit-eating bat", 4999, 99999, 0], [46, "BRCA", "Antillean fruit-eating bat", 4999, 99999, 0], [47, "DIEC", "Hairy-legged vampire bat", 4999, 99999, 0], [48, "LAMI", "Minor red bat", 4999, 99999, 0], [52, "MYOC", "Arizona myotis", 4999, 99999, 0], [53, "NOLE", "Greater bulldog bat", 4999, 99999, 0], [54, "STRU", "Red fruit bat", 4999, 99999, 0], [65, "NOISE", "Not a bat/Noise", 5000, 120000, 1], [86, "COTOVI", "Virginia big-eared bat", 4999, 99999, 0]]
# LOOKUP = [''] * 100
# for row in SPECIES:
#     LOOKUP[row[0]] = row[1]


class Prediction():

    def __init__(self, img_height, img_width, img_channels):
        self.img_height = img_height
        self.img_width = img_width
        self.img_channels = img_channels
        self.MODEL_NAME = 'm-1'
        self.DIRNAME = os.path.dirname(__file__)
        self.MODEL = keras.models.load_model(os.path.join(
            self.DIRNAME, '{}'.format(self.MODEL_NAME)))

    def predict_images(self, data):
        if len(data) == 0:
            return []
        batch = np.zeros(
            (len(data), self.img_height, self.img_width, self.img_channels))
        for i, img in enumerate(data):
            batch[i] = img
        return self.MODEL.predict(batch)


class Processor():
    def __init__(self, grts_id, file):

        self.grts_id = grts_id
        self.file = file

        self.spectrogram = Spectrogram()
        self.predictor = Prediction(self.spectrogram.img_height,
                                    self.spectrogram.img_width, self.spectrogram.img_channels)

    def process(self):
        d = self.spectrogram.process_file(self.file)

        to_predict = []

        if len(d.metadata) == 0:
            return 0

        for m in d.metadata:

            img = self.spectrogram.make_spectrogram(
                m.window, d.sample_rate)
            to_predict.append(img)

        all_predictions = self.predictor.predict_images(to_predict)

        return all_predictions


def handler(event, context):

    print(event)

    for event in event['Records']:
        body = json.loads(event['body'])
        for record in body['Records']:
            if(record["eventSource"] == "aws:s3"):
                key = unquote(record["s3"]["object"]["key"])
                print(key)
                processor = Processor(
                    grts_id=2, file='example.py')
                return processor.process().tolist()
