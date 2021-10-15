
import json
import os
import traceback
import boto3
import numpy as np
import psycopg2
from spectrogram_v2 import Spectrogram
from tensorflow import keras
from io import BytesIO
import shutil
import gc

s3 = boto3.client('s3')


AWS_S3_BUCKET_NAME = os.environ.get("AWS_S3_BUCKET_NAME")
if AWS_S3_BUCKET_NAME is None:
    raise Exception('AWS_S3_BUCKET_NAME')

BACKYARD_BAT_PROJECT_NUMBER = os.environ.get("BACKYARD_BAT_PROJECT_NUMBER")
if BACKYARD_BAT_PROJECT_NUMBER is None:
    raise Exception('BACKYARD_BAT_PROJECT_NUMBER')

SPECIES_IDS = [1, 4, 5, 6, 8, 10, 11, 12, 13, 14, 16, 17, 25, 26,
               27, 28, 29, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42, 43, 44, 65]


SPECTROGRAM = Spectrogram()


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

        SPECTROGRAM = Spectrogram()
        self.predictor = Prediction(SPECTROGRAM.img_height,
                                    SPECTROGRAM.img_width, SPECTROGRAM.img_channels)

    def process(self):
        processed_file = SPECTROGRAM.process_file(self.file)

        to_predict = []

        if len(processed_file.metadata) == 0:
            return processed_file, np.asarray([])

        for pulse in processed_file.metadata:

            img = SPECTROGRAM.make_spectrogram(
                pulse.window, processed_file.sample_rate)
            to_predict.append(img)

        predictions = self.predictor.predict_images(to_predict)

        return processed_file, predictions


pg_tools = PostgresTools()


def handler(event, context):
    for event in event['Records']:

        event = json.loads(event['body'])
        key = event['key']

        buff = BytesIO()
        s3.download_fileobj(AWS_S3_BUCKET_NAME, key, buff)
        file_size = buff.getbuffer().nbytes
        buff.seek(0)

        try:

            file_batch = pg_tools.execute_query("""
                select af.id, afb.id, s.grts_id from nabatmonitoring.acoustic_file af 
                join nabatmonitoring.acoustic_file_batch afb on afb.file_id = af.id
                join nabatmonitoring.acoustic_batch ab on ab.id = afb.batch_id 
                join nabatmonitoring.survey_event se on se.id = ab.survey_event_id 
                join nabatmonitoring.survey s on s.id = se.survey_id
                where af.project_id = %s and file_name = %s ;""",
                                                (BACKYARD_BAT_PROJECT_NUMBER,
                                                 key.split('/')[-1]),
                                                True)

            file_id = file_batch[0][0]
            file_batch_id = file_batch[0][1]
            grts_id = file_batch[0][2]

            processor = Processor(
                grts_id=grts_id, file=buff)
            processed_file, predictions = processor.process()
            predictions = predictions.tolist()
            print("DONE PROCESSING")

            pg_tools.execute_query('update nabatmonitoring.acoustic_file set size_bytes = %s, length_ms = %s where id = %s ;',
                                   (file_size, int(
                                       processed_file.duration * 1000), file_id),
                                   False)

            query1 = """
                INSERT INTO nabatmonitoring.acoustic_file_batch_pulse
                (offset_milliseconds, amplitude, frequency, signal_to_noise, acoustic_file_bactch_id)
                VALUES(%s, %s, %s, %s, %s) returning id;
            """
            query2 = """
                INSERT INTO nabatmonitoring.acoustic_file_batch_pulse_predictions
                (acoustic_file_batch_pulse_id, species_id, rate)
                VALUES(%s, %s, %s);
            """
            for i, pulse in enumerate(processed_file.metadata):

                result = pg_tools.execute_query(query1,
                                                (pulse.offset + pulse.time, pulse.amplitude, pulse.frequency, pulse.snr, file_batch_id), True)
                acoustic_file_batch_pulse_id = result[0][0]

                for j, predicton in enumerate(predictions[i]):
                    result = pg_tools.execute_query(query2,
                                                    (acoustic_file_batch_pulse_id, SPECIES_IDS[j],  predicton), False)
            # publish on c = 0.57
            query3 = """
                with conf as (
                    select
                        pp.species_id,
                        count(p.id) num_samples,
                        sum(rate)/(select count(*) from nabatmonitoring.acoustic_file_batch_pulse where acoustic_file_bactch_id = %s) confidence
                    from
                        nabatmonitoring.acoustic_file_batch_pulse p
                    join
                        nabatmonitoring.acoustic_file_batch_pulse_predictions pp on pp.acoustic_file_batch_pulse_id = p.id
                    join 
                        species s on s.id = pp.species_id
                where acoustic_file_bactch_id = %s
                    group by
                        1
                )
                select 
                    conf.species_id
                from 
                    conf 
                join 
                    nabat.grts_species_range_buffered b on b.species_id = conf.species_id and b.grts_id = %s
                where
                    confidence >= 0.25
                order by
                    confidence desc ;
            """

            result = pg_tools.execute_query(
                query3, (file_batch_id, file_batch_id, grts_id), True)

            if result and len(result) > 0:
                pg_tools.execute_query(
                    'update nabatmonitoring.acoustic_file_batch set auto_id = %s where id = %s ;', (result[0][0], file_batch_id), False)

        except Exception as e:
            print(e)
            traceback.print_exc()
        finally:
            # running out of space on lambda
            shutil.rmtree('/tmp/NUMBA_CACHE_DIR')
            shutil.rmtree('/tmp/MPLCONFIGDIR')

            os.mkdir('/tmp/NUMBA_CACHE_DIR')
            os.mkdir('/tmp/MPLCONFIGDIR')

            gc.collect()
