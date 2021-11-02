import sqlite3
import os
from sqlite3 import Error
import numpy as np
import io
import csv
from collections import namedtuple
from zipfile import ZipFile
from io import TextIOWrapper
from shutil import copyfile

# write to csv instead?
# save spec to db as blob for later use?


class NABat_DB:

    def __init__(self, path, class_list=None):
        try:
            os.mkdir('{}/NABat'.format(path))
        except:
            pass

        self.path = path + '/NABat'
        self.db_name = '{}/NABatAcoustics.v1.sqlite'.format(self.path)
        if os.path.isfile(self.db_name):
            pass
        else:
            copyfile('nabat/NABatAcoustics.v1.base.sqlite', self.db_name)
        self.conn = self._create_connection(self.db_name)
        self.conn.row_factory = namedtuple_factory
        self.cursor = self.conn.cursor()

        self.fastCon = self._create_connection(self.db_name)
        self.fastCursor = self.fastCon.cursor()

        self.cursor.execute("PRAGMA journal_mode=WAL")
        self.fastCursor.execute("PRAGMA journal_mode=WAL")

        self._set_species_list(class_list)

    def __del__(self):
        self.conn.close()
        self.fastCon.close()

    def _create_connection(self, db_file):
        conn = None
        try:
            conn = sqlite3.connect(
                db_file, detect_types=sqlite3.PARSE_DECLTYPES)
            return conn
        except Error as e:
            print(e)

        return conn

    def species_from_species_code(self, species_code):
        for s in self.query('select * from species;'):
            if s.species_code == species_code:
                return s

    def to_csv(self, table):
        names = self.query('PRAGMA table_info({});'.format(table))
        data = self.query('select * from {};'.format(table))
        with open('{}/{}.csv'.format(self.path, table), 'w') as f:
            writer = csv.writer(f)
            writer.writerow([n[1] for n in names])
            writer.writerows(data)

    def delete(self):
        self.conn.close()
        os.remove(self.db_name)
        self.__init__(self.path, self.class_list)

    def set_species_list(self, grts_id):
        self.insert(
            "UPDATE species set available = 0 where id not in (select species_id from species_grts where grts_id = ?);", (grts_id,))
        return self.query('select * from species;')

    def _set_species_list(self, class_list):
        if class_list is not None:
            self.insert(
                "UPDATE species set available = 0 where species_code not in ({})".format(','.join(['?'] * len(class_list))), class_list)

    def get_full_sl(self, grts_id):
        rows = self.query(
            'select s.id, sg.species_id from species s left join species_grts sg on sg.species_id = s.id and grts_id = ? order by id', (grts_id,))
        return np.array([0 if s.species_id == None else 1 for s in rows])

    def set_location(self, grts_id, grts_cell_id, sample_frame, location, sublocation):
        self.insert("DELETE FROM location;")
        self.insert("INSERT INTO location (grts_id, grts_cell_id, sample_frame, location, sublocation) VALUES (?,?,?,?,?);",
                    (grts_id, grts_cell_id, sample_frame, location, sublocation))

    def get_location(self):
        return self.query("select * from location;")

    def get_file(self, file=None):
        if file is not None:
            return self.query(
                "SELECT * FROM file where name = ?;", (file,))
        else:
            return self.fastQuery(
                "SELECT name FROM file;")

    def get_files(self):
        return self.fastQuery(
            """ 
                with x as (
                select file_id,  pulse_id, max(confidence) as con, count(*)  as c
                from pulse p 
                join prediction pp on pp.pulse_id = p.id
                join species s on s.id = pp.species_id
                where s.available = 1
                group by 1,2
                )
                select f.id, f.name, f.duration,  f.sample_rate,  avg(x.con)
                from x
                join file f on f.id = x.file_id
                group by 1
                order by sum(case when x.con > 0.7 then x.con else 0 end) desc
                --by max(x.con) + avg(x.con) + (CASE 
                 --   WHEN x.c >=10 THEN 1 
                 --   ELSE (x.c/10)
                 --   END) desc;
            """)

    def get_pulses(self, file_id):
        return self.query(
            "SELECT * FROM pulse where file_id = ?;", (file_id,))

    def get_predictions(self, pulse_id, file_id):

        if pulse_id:
            return self.query(
                "SELECT pulse_id, species_code, confidence FROM prediction p join species s on p.species_id = s.id where pulse_id = ? and available = 1 order by species_code;", (pulse_id,))
        elif file_id:
            return self.query(
                "SELECT pulse_id, species_code, confidence FROM pulse pp join prediction p on p.pulse_id = pp.id join species s on p.species_id = s.id where file_id = ? and available = 1 order by pulse_id, species_code;", (file_id,))

    def add_file(self, name, duration, sample_rate, grts_id):
        return self.insert(
            "INSERT INTO file (name, duration, sample_rate, grts_id) VALUES (?,?,?,?);", (name, duration, sample_rate, grts_id))

    def add_pulse(self, file_id, frequency, amplitude, sig_noise, offset, time,  window):
        return self.insert(
            "INSERT INTO pulse (file_id, frequency, amplitude, sig_noise, offset, time, window) VALUES (?,?,?,?,?,?,?);", (file_id, frequency, amplitude, sig_noise, offset, time, window))

    def add_predictions(self, values):

        self.conn.executemany(
            'INSERT INTO prediction (pulse_id, species_id, confidence)  values (?,?,?);', values)
        self.conn.execute('commit;')
        # return self.insert(
        #     "INSERT INTO prediction (pulse_id, species_id, confidence) select {}, id, {} from species where species_code = ?;".format(pulse_id, confidence), (species_id,))

    def get_predictions_file(self, file_name):
        return self.query("""
        
            with samples as (
                select
                    f.id as file_id,
                    count(*) pc
                from 
                    file f
                join
                    pulse p on f.id = p.file_id
                where
                    f.name = ?
                group by 1
            ) 
            , conf as (
                select
                    p.file_id,
                    pp.species_id,
                    count(p.id) num_samples,
                    sum(confidence)/(pc) sc
                from 
                    samples
                join 
                    pulse p on p.file_id = samples.file_id
                join
                    prediction pp on pp.pulse_id = p.id
                where 
                    pp.confidence > 0.57
                group by
                    p.file_id, pp.species_id
            )
            , result  as (
                select
                    conf.file_id,
                    name,
                    f.grts_id,
                    s.species_code,
                    s.id as species_id,
                    max(conf.sc) conf
                from 
                    conf
                join
                    file f on f.id = conf.file_id
                join 
                    species s on s.id = conf.species_id
                group by 
                    1,2 ,3
			)
			select
                r.*
            from
                result r
            join
                species_grts sg on sg.grts_id = r.grts_id and sg.species_id = r.species_id
        ;
        """, (file_name,))

    def query(self, query, args={}):
        try:
            self.cursor.execute(query, args)
            return self.cursor.fetchall()
        except Error as e:
            print(e)
            return None

    def fastQuery(self, query, args={}):
        try:
            self.fastCursor.execute(query, args)
            return self.fastCursor.fetchall()
        except Error as e:
            print(e)
            return None

    def insert(self, query, args={}):

        try:
            self.cursor.execute(query, args)
            self.conn.commit()
            return self.cursor.lastrowid
        except Error as e:
            print(e)
            return None


def adapt_array(arr):
    """
    http://stackoverflow.com/a/31312102/190597 (SoulNibbler)
    """
    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())


def convert_array(text):
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)


def namedtuple_factory(cursor, row):
    """Returns sqlite rows as named tuples."""
    fields = [col[0] for col in cursor.description]
    Row = namedtuple("Row", fields)
    return Row(*row)


# Converts np.array to TEXT when inserting
sqlite3.register_adapter(np.ndarray, adapt_array)

# Converts TEXT to np.array when selecting
sqlite3.register_converter("array", convert_array)


# Species frequency ranges

# http://www.sonobat.com/download/WesternUS_Acoustic_Table_Mar2011.pdf
# http://www.sonobat.com/download/EasternUS_Acoustic_Table_Mar2011.pdf
# http://www.sonobat.com/download/AZ_Acoustic_Table-Mar08.pdf

SPECIES_FREQUENCY_RANGES = {
    'ANPA': [27000, 51000],
    'ARJA': [4999, 99999],
    'BRCA': [4999, 99999],
    'CHME': [4999, 99999],
    'CORA': [4999, 99999],
    'COTO': [22000, 41000],
    'COTOVI': [4999, 99999],
    'DIEC': [4999, 99999],
    'EPFU': [25000, 52000],
    'EUFL': [10000, 25000],
    'EUMA': [10000, 17000],
    'EUPE': [10000, 19000],
    'EUUN': [4999, 99999],
    'IDPH': [14000, 18000],
    'LABL': [37000, 61000],
    'LABO': [29000, 73000],
    'LACI': [17000, 49000],
    'LAEG': [4999, 99999],
    'LAIN': [25000, 41000],
    'LAMI': [4999, 99999],
    'LANO': [24000, 44000],
    'LASE': [35000, 52000],
    'LAXA': [28000, 56000],
    'LENI': [4999, 99999],
    'LEYE': [4999, 99999],
    'MACA': [28000, 55000],
    'MOME': [4999, 99999],
    'MOMO': [4999, 99999],
    'MYAR': [33000, 45000],
    'MYAU': [42000, 65000],
    'MYCA': [45000, 95000],
    'MYCI': [40000, 71000],
    'MYEV': [31000, 71000],
    'MYGR': [41000, 85000],
    'MYKE': [4999, 99999],
    'MYLE': [40000, 71000],
    'MYLU': [38000, 73000],
    'MYOC': [4999, 99999],
    'MYSE': [37000, 95000],
    'MYSO': [37000, 70000],
    'MYTH': [24000, 50000],
    'MYVE': [41000, 49000],
    'MYVO': [39000, 89000],
    'MYYU': [46000, 91000],
    'NOISE': [5000, 120000],
    'NOLE': [4999, 99999],
    'NYFE': [10000, 41000],
    'NYHU': [32000, 48000],
    'NYMA': [12000, 30000],
    'PAHE': [41000, 70000],
    'PESU': [36000, 50000],
    'STRU': [4999, 99999],
    'TABR': [18000, 46000]
}
