
import os
import json
import numpy as np
from spectrogram_v2 import Spectrogram
from tensorflow import keras
import boto3
import psycopg2

s3 = boto3.client('s3')


AWS_S3_BUCKET_NAME = os.environ.get("AWS_S3_BUCKET_NAME")
if AWS_S3_BUCKET_NAME is None:
    raise Exception('AWS_S3_BUCKET_NAME')

BACKYARD_BAT_PROJECT_NUMBER = os.environ.get("BACKYARD_BAT_PROJECT_NUMBER")
if BACKYARD_BAT_PROJECT_NUMBER is None:
    raise Exception('BACKYARD_BAT_PROJECT_NUMBER')

SPECIES_IDS = [1, 4, 5, 6, 8, 10, 11, 12, 13, 14, 16, 17, 25, 26,
               27, 28, 29, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42, 43, 44, 65]


class PostgresTools:

    # return None on Success. else return the error
    def execute_query(self, query, values=tuple(), results=False):
        connection = None
        response = None
        try:
            connection = psycopg2.connect(dbname=os.environ['PG_NAME'], host=os.environ['PG_HOST'],
                                          port=os.environ['PG_PORT'], user=os.environ['PG_USER'], password=os.environ['PG_PASS'])
            cursor = connection.cursor()
            cursor.execute(query, values)
            if results:
                response = cursor.fetchall()
            connection.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            print("Encountered a Database Error.", error)
            print(query, values)
            return error
        except Exception as error:
            print("Encountered an Unknown Error.", error)
            print(query, values)
            return error
        finally:
            cursor.close()
            connection.close()
        return response


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
        processed_file = self.spectrogram.process_file(self.file)

        to_predict = []

        if len(processed_file.metadata) == 0:
            return 0

        for pulse in processed_file.metadata:

            img = self.spectrogram.make_spectrogram(
                pulse.window, processed_file.sample_rate)
            to_predict.append(img)

        predictions = self.predictor.predict_images(to_predict)

        return processed_file, predictions


pg_tools = PostgresTools()


def handler(event, context):
    for event in event['Records']:
        event = json.loads(event['body'])

        key = event['key']
        grts_id = event['grts_id']
        temp_name = '/tmp/recording.wav'

        with open(temp_name, mode='wb') as f:
            s3.download_fileobj(AWS_S3_BUCKET_NAME, key, f)
            print("DONE DOWNLOAD")
        file_size = os.path.getsize(temp_name)

        try:
            processor = Processor(
                grts_id=grts_id, file=temp_name)
            resprocessed_file, predictions = processor.process()
            predictions = predictions.tolist()
            print("DONE PROCESSING")

            file_batch = pg_tools.execute_query('select af.id, afb.id from nabatmonitoring.acoustic_file af join nabatmonitoring.acoustic_file_batch afb on afb.file_id = af.id where project_id = %s and file_name = %s ;',
                                                (BACKYARD_BAT_PROJECT_NUMBER,
                                                 key.split('/')[-1]),
                                                True)
            file_id = file_batch[0][0]
            file_batch_id = file_batch[0][1]

            pg_tools.execute_query('update nabatmonitoring.acoustic_file set size_bytes = %s, length_ms = %s where id = %s ;',
                                   (file_size, resprocessed_file.duration, file_id),
                                   True)

            query1 = """
                INSERT INTO nabatmonitoring.acoustic_file_batch_pulse
                (offset_milliseconds, amplitude, frequency, signal_to_noise, acoustic_file_bactch_id)
                VALUES(%s, %s, %s, %s, %s, %s) returning id;
            """
            query2 = """
                INSERT INTO nabatmonitoring.acoustic_file_batch_pulse_predictions
                (acoustic_file_batch_pulse_id, species_id, rate)
                VALUES(%s, %s, %s);
            """
            for i, pulse in enumerate(resprocessed_file.metadata):

                result = pg_tools.execute_query(query1,
                                                (pulse.offset + pulse.time, pulse.amplitude, pulse.frequency, pulse.snr, file_batch_id), True)
                acoustic_file_batch_pulse_id = result[0][0]

                for j, predicton in enumerate(predictions[i]):
                    result = pg_tools.execute_query(query2,
                                                    (acoustic_file_batch_pulse_id, SPECIES_IDS[j],  predicton), False)

        except Exception as e:
            print(e)
        finally:
            os.remove(temp_name)