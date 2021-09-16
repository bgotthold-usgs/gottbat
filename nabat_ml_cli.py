import argparse
import time
import glob
import os
from nabat.db_manager import NABat_DB
from prediction.prediction import Prediction
from spectrogram.spectrogram_v2 import Spectrogram
from nabat.gql_api import GraphQL_API
import numpy as np
import matplotlib
import threading

os.chdir(os.path.dirname(os.path.abspath(__file__)))
print(os.getcwd())
matplotlib.use('Agg')



class Processor():
    def __init__(self, grts_id, directory, uuid):
        self.grts_id = grts_id
        self.directory = directory
        self.uuid = uuid

        self.spectrogram = Spectrogram()

        self.predictor = Prediction(self.spectrogram.img_height,
                                    self.spectrogram.img_width, self.spectrogram.img_channels)
        self.db = NABat_DB(
            self.directory, class_list=self.predictor.CLASS_NAMES)

        self.species = self.db.query('select * from species;')

    def get_manual_id(self, species_code):
        for s in self.species:
            if s.species_code == species_code:
                return s.id

    def process(self, file):
        d = self.spectrogram.process_file(file)

        file_id = self.db.add_file(
            d.name, d.duration, d.sample_rate, self.grts_id)

        to_predict = ([], [])
        pulse_count = 0
        frequency_sum = 0
        for i, m in enumerate(d.metadata):
            pulse_id = self.db.add_pulse(file_id, m.frequency,
                                         m.amplitude, m.snr, m.offset, m.time, m.window)
            pulse_count += 1
            frequency_sum += m.frequency

            cur_window_length = m.window.shape[1]
            empty = np.zeros(m.window.shape)
            windows = m.window[:, int(
                m.window.shape[1] * 0.2): int(m.window.shape[1] * 0.8)]
            for j in range(1, 4):
                if len(d.metadata) > i+j:
                    w = d.metadata[i+j].window[:, int(
                        cur_window_length * 0.2): int(cur_window_length * 0.8)]
                    windows = np.concatenate((windows, w), axis=1)
                else:
                    windows = np.concatenate(
                        (windows, empty), axis=1)
            img = self.spectrogram.make_spectrogram(
                windows, d.sample_rate)

            to_predict[0].append(img)
            to_predict[1].append(pulse_id)
        all_predictions = self.predictor.predict_images(to_predict[0])

        db_insert = []
        for k, p in enumerate(all_predictions):
            for j, prediction in enumerate(p):
                db_insert.append((
                    int(to_predict[1][k]), int(self.get_manual_id(self.predictor.CLASS_NAMES[j])), float(prediction)))

        self.db.add_predictions(db_insert)

        detection = self.db.get_predictions_file(file)

        if len(detection) >= 1:
            detection = detection[0]
            print(detection)

            # x = threading.Thread(target=upload, args=(
            #     detection, self.grts_id, self.uuid, pulse_count, frequency_sum))
            # x.start()
            return detection.conf, d.duration
        return 0, d.duration


def upload(detection, grts_id, uuid, pulse_count, frequency_sum):
    api = GraphQL_API()
    api.upload_gottbat_detection(detection.name, time.time(
    ), grts_id, uuid, detection.species_id, detection.conf, pulse_count, int(frequency_sum/pulse_count))
    return


parser = argparse.ArgumentParser(
    description='Process full spectrum acoustics.')

parser.add_argument('-s, --sleep', dest='sleep', type=int, nargs=1, default=[10],
                    help='Integer delay in seconds between checking for new files')

parser.add_argument('-p, --path', dest='path', type=str, nargs=1, default=[''],
                    help='The directory to monitor.')

parser.add_argument('-g, --grts', dest='grts', type=int, nargs=1, default=[],
                    help='The NABat Grts Id where theses sounds were recorded.')

parser.add_argument('-u, --uuid', dest='uuid', type=str, nargs=1, default=[],
                    help='The Gottbat detector identifier.')

print('Initializing...')
args = parser.parse_args()
processor = Processor(
    grts_id=args.grts[0], directory=args.path[0], uuid=args.uuid[0])
print('Starting...')
time.sleep(1)
while True:
    files = glob.glob('{}/**/*.wav'.format(args.path[0]), recursive=True)
    files += glob.glob('{}/**/*.WAV'.format(args.path[0]), recursive=True)
    for f in files:
        # do work
        start = time.time()
        duration = 0
        try:
            conf, duration = processor.process(f)
            if conf > 0:
                os.rename(f, f + '.processed')
            else:
                os.remove(f)
        except Exception as e:
            print(e)
        finally:
            end = time.time()
            print('{} - File Length: {} - Processing Time: {}'.format(f,
                  duration, end - start))
    time.sleep(args.sleep[0])
