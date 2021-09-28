import glob
import time as _time
import tkinter as tk
from functools import partial
from tkinter import filedialog, ttk
import librosa
import librosa.display
import matplotlib
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import os
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from nabat.db_manager import NABat_DB
from nabat.gql_api import GraphQL_API
from prediction.prediction import Prediction
from spectrogram.spectrogram_v2 import Spectrogram

matplotlib.use('TkAgg')


class Nabat_Gui():
    def __init__(self, root):
        self.files = []
        self.species_code_predictions = []
        self.directory = None
        self.predictor = None

        root.title('NABat Acoustic Classifier')
        root.resizable(False, False)
        root.iconbitmap('assets/pulse.ico')
        img = tk.PhotoImage(file='assets/pulse.png')
        root.tk.call('wm', 'iconphoto', root._w, img)
        self.root = tk.Frame(root)
        self.root.grid()

        self.chart_frame = None
        self.location = None
        self.file_display = 0
        self.pulse_display = 0
        self.updating = False
        self.display_cache = {'pulses': {}}
        self.sensitivity = tk.IntVar(self.root, 70)
        # spectrogram = Spectrogram()
        # self.predictor = Prediction(spectrogram.img_height,
        #                             spectrogram.img_width, spectrogram.img_channels)

        # self.progress bar widget
        self.progress = ttk.Progressbar(self.root, orient=tk.HORIZONTAL,
                                        length=900, mode='determinate')

        # set button style with ttk, MacOS bug :(
        ttk.Style().configure('black/grey.TButton', foreground='black', background='grey')

        # define some buttons
        ttk.Button(self.root, width=20, padding=[
            35, 10], text='Choose Directory', style='black/grey.TButton', command=self.load_directory).grid(row=7, column=0, padx=5)

        self.loc_btn = ttk.Button(self.root, width=20, padding=[
            35, 10], text='Recording Location', style='black/grey.TButton', command=self.select_recording_location)
        self.loc_btn['state'] = tk.DISABLED
        self.loc_btn.grid(row=7, column=2, padx=5)

        # self.reset_btn = ttk.Button(self.root, width=20, padding=[
        #     35, 10], text='Reset', style='black/grey.TButton', command=self.reset)
        # self.reset_btn['state'] = tk.DISABLED
        # self.reset_btn.grid(row=7, column=3, padx=5)

        self.start_btn = ttk.Button(self.root, width=20, padding=[
            35, 10], text='Start Classification', style='black/grey.TButton', command=self.start_classification)
        self.start_btn['state'] = tk.DISABLED
        self.start_btn.grid(row=7, column=5, padx=5)

        # title
        self.title_var = tk.StringVar(
            self.root, 'Click \'Choose Directory\' to load WAV files.')
        tk.Label(self.root, textvariable=self.title_var).grid(
            row=0, column=0, columnspan=6, padx=5, pady=20)

        self.footer_var = tk.StringVar(
            self.root, 'Click \'Recording Location\' to set a species list.')
        tk.Label(self.root, textvariable=self.footer_var).grid(
            row=8, column=0, columnspan=6, padx=5, pady=1)

        self.api = GraphQL_API()
        self.root.mainloop()

    def load_directory(self):
        if len(self.files):
            self.files = []
            self.directory = ""

        self.root.update_idletasks()
        self.directory = filedialog.askdirectory(
            title="Choose a directory with wav files.")
        self.root.update_idletasks()
        if self.directory:
            self.files = glob.glob(
                '{}/**/*.WAV'.format(self.directory), recursive=True)
            self.files += glob.glob(
                '{}/**/*.wav'.format(self.directory), recursive=True)
            self.title_var.set(
                "Found {} files! Click \'Start Classification\' to begin NABat AutoID process.".format(len(self.files)))
            # self.reset_btn['state'] = tk.NORMAL
            nabat_db = NABat_DB(self.directory)
            if not self.location and len(nabat_db.get_location()):
                self.location = nabat_db.get_location()[0]
                if self.location:
                    self.set_footer(
                        self.location[0], self.location[1], self.location[2], self.location[3], self.location[4])
                self.start_btn['state'] = tk.NORMAL

            self.loc_btn['state'] = tk.NORMAL
            del nabat_db

        self.root.update_idletasks()

    def start_classification(self):

        if not len(self.files):
            return
        self.file_count = len(self.files)

        count = 0

        # GUI updates
        self.title_var.set("Processing...{}/{}".format(count, len(self.files)))
        self.progress['value'] = (count/len(self.files)) * 100
        self.progress.grid(row=1, column=0, columnspan=6, padx=10, pady=5)
        self.root.update_idletasks()

        spectrogram = Spectrogram()
        predictor = Prediction(spectrogram.img_height,
                               spectrogram.img_width, spectrogram.img_channels)

        nabat_db = NABat_DB(
            self.directory)

        nabat_db.set_location(
            self.location[0], self.location[1], self.location[2], self.location[3], self.location[4])
        grts_id = self.location[0]

        species = nabat_db.set_species_list(grts_id)
        species_id_lookup = [''] * 100
        for s in species:
            species_id_lookup[s.id] = s.species_code

        # sl = nabat_db.get_full_sl(grts_id)

        processed_files = [f[0] for f in nabat_db.get_file()]
        elapsed = 0
        remaining = 5 * len(self.files)
        t = _time.perf_counter()

        while len(self.files):
            file = self.files.pop()
            count += 1
            if file not in processed_files:
                d = spectrogram.process_file(file)
                if d is not None:
                    _t = _time.perf_counter()
                    elapsed += _t - t
                    t = _t
                    remaining = (elapsed/count) * len(self.files)
                    file_id = nabat_db.add_file(
                        d.name, d.duration, d.sample_rate, grts_id)
                    if len(d.metadata) == 0:
                        os.remove(file)

                    to_predict = ([], [])
                    for i, m in enumerate(d.metadata):
                        pulse_id = nabat_db.add_pulse(file_id, m.frequency,
                                                      m.amplitude, m.snr, m.offset, m.time, m.window)

                        img = spectrogram.make_spectrogram(
                            m.window, d.sample_rate)

                        #to_predict[0].append((img, sl))
                        to_predict[0].append(img)
                        to_predict[1].append(pulse_id)

                    all_predictions = predictor.predict_images(
                        to_predict[0])
                    db_insert = []
                    for k, p in enumerate(all_predictions):
                        for j, prediction in enumerate(p):
                            db_insert.append((
                                int(to_predict[1][k]), int(species_id_lookup.index(predictor.CLASS_NAMES[j])), float(prediction)))

                    nabat_db.add_predictions(db_insert)

            # GUI updates
            self.title_var.set(
                "Processing...{}/{}  {:.1f}s Remaining".format(count, self.file_count, remaining))
            self.progress['value'] = (count/self.file_count) * 100
            self.root.update()

        del nabat_db

        self.title_var.set("Done. Processed {}/{} files.".format(
            count, self.file_count))
        # nabat_db.to_csv('file')
        # nabat_db.to_csv('species')
        # nabat_db.to_csv('pulse')
        # nabat_db.to_csv('prediction')
        self.root.update()
        self.update()

    def plot(self, canvas, ax, window, windows, sr, offset, time, frequency, frequency_list, centers, time_list, predictions, species_summary, species_predictions, confidence_thresh):
        try:
            for a in ax:
                a.clear()

            ylim_high = 100000
            colors = ['purple', 'blue', 'yellow', 'orange']

            ax[0].set_ylim(5000, ylim_high)
            for i, c in enumerate(centers):
                fl, tl = zip(*[(f, time_list[j]) for j, f in enumerate(
                    frequency_list) if centers[(np.abs(np.asarray(centers) - f)).argmin()] == c])
                facecolors = [colors[i] if p == species_summary[i]
                              [0][0] and p is not None else 'None' for p in species_predictions[i]]

                if colors[i] in facecolors:
                    cfl, ctl = zip(*[(fl[j], tl[j]) for j, c in enumerate(facecolors
                                                                          ) if c == colors[i]])
                    ax[0].scatter(ctl, cfl, c=colors[i])
                if 'None' in facecolors:
                    cfl, ctl = zip(*[(fl[j], tl[j]) for j, c in enumerate(facecolors
                                                                          ) if c != colors[i]])
                    ax[0].scatter(ctl, cfl, c='w', edgecolors=colors[i])

                ax[0].hlines(c, 0, max(time_list), linestyle='dotted',
                             alpha=1, lw=1, color=colors[i], label=' {} ({}/{}) - {:0.1f} kHz'.format(species_summary[i][0][0], species_summary[i][0][1], len(fl), c/1000))

                if frequency > 30000:
                    ax[0].annotate("",
                                   xy=(time + offset, frequency-2000), xycoords='data',
                                   xytext=(time + offset, frequency - 20000), textcoords='data',
                                   arrowprops=dict(arrowstyle="->",
                                                   connectionstyle="arc3"),
                                   )
                else:
                    ax[0].annotate("",
                                   xy=(time + offset, frequency + 2000), xycoords='data',
                                   xytext=(time + offset, frequency + 20000), textcoords='data',
                                   arrowprops=dict(arrowstyle="->",
                                                   connectionstyle="arc3"),
                                   )

            ax[0].set_ylabel('Frequency')
            ax[0].set_xlabel('Time (ms)')
            ax[0].legend(prop={'weight': 'bold'})
            ax[0].set_title('Suspected Bat Pulses Within File ')

            # Plot
            librosa.display.specshow(
                window, sr=sr, hop_length=int(0.001 * sr / 4), x_axis='s', y_axis='linear', ax=ax[1])

            # center the pulse in the frame
            #ax[1].set_xlim(time/1000 - 0.0175, time/1000 + 0.0175)
            ax[1].set_ylim(5000, ylim_high)
            ax[1].axis('off')
            ax[1].set_title('Pulse Image at {} ms & {:0.1f} kHz'.format(
                offset + time, frequency/1000))

            labels = [p[1] for p in predictions]
            confidence = [p[2] * 100 for p in predictions]
            # sum_c = sum(confidence)
            # confidence = [(c / sum_c) * 100 for c in confidence]

            ax[2].barh(labels, confidence)
            ax[2].vlines(confidence_thresh, 0, len(predictions), linestyle='dashdot',
                         color='red', alpha=0.5, lw=0.5, label='Min Confidence: {}%'.format(confidence_thresh))

            ax[2].set_xlabel('Confidence %')
            ax[2].legend()
            ax[2].set_title('Pulse Confidence Distribution')

            librosa.display.specshow(
                windows, sr=sr, hop_length=int(0.001 * sr / 4), x_axis='s', y_axis='linear', ax=ax[3])

            # center the pulse in the frame
            ax[3].set_ylim(5000, ylim_high)
            # Create a Rectangle patch
            rect = patches.Rectangle((self.pulse_display * 0.05 + 0.005, 10000), 0.05 - 0.01,
                                     ylim_high - 15000, linewidth=1, edgecolor='r', facecolor='none')
            # Add the patch to the Axes
            ax[3].add_patch(rect)
            ax[3].axis('off')

            canvas.draw()

        except Exception as e:
            self.handel_error(str(e))

    def show_results(self):

        pulse = None
        file = None

        nabat_db = NABat_DB(self.directory)

        if 'files' not in self.display_cache:
            self.display_cache['files'] = nabat_db.get_files()

        files = self.display_cache['files']

        if files and len(files):
            if self.file_display >= len(files):
                self.file_display = 0
            elif self.file_display < 0:
                self.file_display = len(files) - 1
            file = files[self.file_display]
            file_name = file[1]

            if file_name not in self.display_cache['pulses']:
                self.display_cache['pulses'][file_name] = nabat_db.get_pulses(
                    file[0])

            pulses = self.display_cache['pulses'][file_name]

            if pulses and len(pulses):
                if self.pulse_display >= len(pulses) or self.pulse_display < 0:
                    self.pulse_display = 0
                elif self.pulse_display < 0:
                    self.pulse_display = len(pulses) - 1
                pulse = pulses[self.pulse_display]
                pulse_predictions = nabat_db.get_predictions(pulse[0], None)

        if pulse:

            file_id = file[0]
            duration = file[2]
            sample_rate = file[3]
            pulse_id = pulse[0]
            frequency = pulse[2]
            amplitude = pulse[3]
            snr = pulse[4]
            offset = pulse[5]
            time = pulse[6]
            window = pulse[7]
            windows = None
            for m in pulses:
                if windows is None:
                    windows = m.window
                else:
                    windows = np.concatenate((windows, m.window), axis=1)

            if not self.chart_frame:
                self.chart_frame = tk.LabelFrame(self.root, relief='sunken')
                self.chart_frame.grid(
                    row=4, column=0, columnspan=6, rowspan=1, padx=5, pady=20)

                ttk.Button(self.chart_frame, padding=[
                    35, 10], text='Previous File', command=self.file_minus).grid(
                    row=0, column=0, columnspan=1, padx=5, pady=5)

                ttk.Button(self.chart_frame, padding=[
                    35, 10], text='Next File', command=self.file_plus).grid(
                    row=0, column=5, columnspan=1, padx=5, pady=5)

                ttk.Button(self.chart_frame, padding=[
                    35, 10], text='Previous Pulse', command=self.pulse_minus).grid(
                    row=0, column=1, columnspan=1, padx=5, pady=5)

                ttk.Button(self.chart_frame, padding=[
                    35, 10], text='Next Pulse', command=self.pulse_plus).grid(
                    row=0, column=4, columnspan=1, padx=5, pady=5)

                self.chart_text = tk.StringVar(
                    self.chart_frame, '')

                tk.Label(self.chart_frame, textvariable=self.chart_text).grid(
                    row=0, column=2, columnspan=2, padx=5, pady=1)

                tk.Scale(
                    self.chart_frame, variable=self.sensitivity, command=self.update, length=800, from_=1, to=100, orient=tk.HORIZONTAL).grid(
                        row=2, column=0, columnspan=6, padx=5)
                tk.Label(
                    self.chart_frame, text='Minimum Confidence - Reduce False Postives').grid(
                        row=1, column=0, columnspan=6, padx=5)

                figure = plt.figure(figsize=(14, 6), dpi=100,
                                    facecolor='#EBEDED')
                ax0 = figure.add_axes(
                    [0.06, .35, .325, .6], facecolor='#EBEDED')
                ax1 = figure.add_axes([.40, .35, .25, .6], facecolor='#EBEDED')
                ax2 = figure.add_axes([.70, .35, .29, .6], facecolor='#EBEDED')
                ax3 = figure.add_axes([0, .05, 1, .20], facecolor='#EBEDED')

                chart = tk.Frame(self.chart_frame)
                chart.grid(
                    row=3, column=0, columnspan=6, rowspan=3, padx=10, pady=5)

                self.canvas = FigureCanvasTkAgg(figure, chart)
                self.canvas.get_tk_widget().grid(
                    row=0, column=0, columnspan=1, rowspan=1, padx=10, pady=10)

                figure.suptitle(file_name, y=0.0, x=0.5)

                self.ax = [ax0, ax1, ax2, ax3]

                spectrogram = Spectrogram()
                self.predictor = Prediction(spectrogram.img_height,
                                            spectrogram.img_width, spectrogram.img_channels)

              # frequency plot
            frequency_list = [p[2] for p in pulses]
            k_means, centers = self.predictor.frequency_k_means(frequency_list)

            time_list = [p[6] + p[5] for p in pulses]

            all_predictions = nabat_db.get_predictions(None, file_id)
            confidence_thresh = self.sensitivity.get()
            species_summary, species_predictions = self.predictor.predict_file(
                all_predictions, k_means, confidence_thresh=confidence_thresh)

            self.plot(self.canvas, self.ax, window, windows, sample_rate, offset,
                      time, frequency, frequency_list, centers, time_list, pulse_predictions, species_summary, species_predictions, confidence_thresh)

            self.chart_text.set('File: {}/{}  Pulse: {}/{}'.format(
                self.file_display+1, len(files), self.pulse_display+1, len(pulses)))

            del nabat_db
            self.root.update_idletasks()

    def update(self, x=None):
        self.show_results()

    def file_plus(self):
        self.pulse_display = 0
        self.file_display += 1
        self.update()

    def file_minus(self):
        self.pulse_display = 0
        self.file_display -= 1
        self.update()

    def pulse_plus(self):
        self.pulse_display += 1
        self.update()

    def pulse_minus(self):
        self.pulse_display -= 1
        self.update()

    def set_recording_location(self, handler, hooks):

        self.footer_var.set('Loading...')
        self.root.update()

        try:
            location_fields = {
                'latitude': float(hooks[0].get()) if hooks[0].get() else None,
                'longitude': float(hooks[1].get()) if hooks[1].get() else None,
                'identifier': str(hooks[2].get())
            }
            handler.destroy()
        except:
            self.handel_error('Unable to read Inputs. Data is not numeric.')

        self.root.update_idletasks()
        try:
            if location_fields['latitude'] and location_fields['longitude']:

                r = self.api.search_lat_long(
                    location_fields['latitude'], location_fields['longitude'])

                self.set_footer(r['grtsId'], r['grtsId'],
                                r['sampleFrame'], r['county'], r['state'])
            elif location_fields['identifier']:
                r = self.api.get_survey_event_by_identifier(
                    location_fields['identifier'])
                self.set_footer(r['grtsId'], r['grtsId'],
                                r['sampleFrame'], r['startTime'], r['locationName'])
            self.root.update_idletasks()

        except Exception as e:
            self.handel_error(str(e))

    def set_footer(self, grtsId, grtsCellId, sampleFrame, county, state):
        self.start_btn['state'] = tk.NORMAL
        self.location = (grtsId, grtsCellId, sampleFrame, county, state)
        self.footer_var.set('{} GRTS Cell: {} - {}, {}'.format(
            sampleFrame, grtsCellId, county, state))

        if self.directory and self.predictor:
            nabat_db = NABat_DB(
                self.directory, class_list=self.predictor.CLASS_NAMES)
            nabat_db.set_species_list(self.location[0])
            nabat_db.set_location(
                self.location[0], self.location[1], self.location[2], self.location[3], self.location[4])
            self.root.update_idletasks()

            del nabat_db

    def reset(self):
        location_root = tk.Tk()
        location_root.resizable(False, False)
        location_root.title('Reset Directory')
        tk.Button(location_root,
                  text='Cancel',
                  command=location_root.destroy).grid(row=1,
                                                      column=0,
                                                      sticky=tk.W,
                                                      pady=4)
        tk.Button(location_root,
                  text='Reset',
                  command=partial(self._reset, location_root)).grid(row=1,
                                                                    column=1,
                                                                    sticky=tk.W,
                                                                    pady=4)

    def _reset(self, location_root):
        location_root.destroy()
        nabat_db = NABat_DB(self.directory)
        nabat_db.delete()
        del nabat_db
        if self.chart_frame:
            for child in self.chart_frame.winfo_children():
                child.destroy()
            self.chart_frame.destroy()

        self.title_var.set('Click \'Choose Directory\' to load WAV files.')
        self.progress['value'] = 0
        self.directory = None
        self.pulse_display = 0
        self.file_display = 0
        self.root.update_idletasks()

    def select_recording_location(self):

        location_root = tk.Tk()
        location_root.resizable(False, False)
        location_root.title('Set Recording Location')
        tk.Label(location_root, text="Latitude").grid(row=0)
        tk.Label(location_root, text="Longitude").grid(row=1)
        tk.Label(location_root,
                 text="---------- OR ----------").grid(row=2, columnspan=2)
        tk.Label(location_root, text="NABat Survey Identifier").grid(row=3)

        e1 = tk.Entry(location_root)
        e2 = tk.Entry(location_root)
        e3 = tk.Entry(location_root)

        e1.grid(row=0, column=1)
        e2.grid(row=1, column=1)
        e3.grid(row=3, column=1)

        tk.Button(location_root,
                  text='Quit',
                  command=location_root.destroy).grid(row=4,
                                                      column=0,
                                                      sticky=tk.W,
                                                      pady=4)
        tk.Button(location_root,
                  text='Set Location', command=partial(self.set_recording_location, location_root, [e1, e2, e3])).grid(row=4,
                                                                                                                       column=1,
                                                                                                                       sticky=tk.W,
                                                                                                                       pady=4)
        location_root.mainloop()

    def handel_error(self, error):

        error_root = tk.Tk()
        error_root.title('Error!')
        tk.Label(error_root, text=error).grid(row=0)

        tk.Button(error_root,
                  text='Okay',
                  command=error_root.destroy).grid(row=2,
                                                   column=2,
                                                   sticky=tk.W,
                                                   pady=4)
        error_root.mainloop()


if __name__ == '__main__':
    root = tk.Tk()
    Nabat_Gui(root)
    root.mainloop()
