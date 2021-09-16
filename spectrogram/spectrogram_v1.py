# classes and methods for extracting pulses form wav file and saving them as spectrogram images

import colorsys
import io
import math
from collections import namedtuple

import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

Metadata = namedtuple(
    "Metadata", "offset, frequency, amplitude, time, snr, window, img")
Data = namedtuple('Data', 'name, duration, sample_rate, metadata')


class Spectrogram():

    def __init__(self, overlap=0.008, amp_thresh=21, sn_thresh=7):

        self.colors = []
        self.img_height = 250  # in px
        self.img_width = 50  # in px
        self.img_channels = 3
        self.window_length = 50  # in ms
        self.maximum_file_length = 45000  # in ms
        # advance the window start postion by (1 - overlap)%
        self.overlap = (overlap * self.window_length)
        # minimum ratio of max amplitude to mean amplitude in a window that will create a spectrogram
        self.sn_thresh = sn_thresh
        # minimum of the max amplitude in a window that will create a spectrogram
        self.amp_thresh = amp_thresh

        # create color options used to scale frequency markers
        for i in range(101):
            rgb = colorsys.hsv_to_rgb(i / 300., 1.0, 1.0)
            ll = [round(255*x) for x in rgb]
            for i in range(0, len(ll)):
                ll[i] = ll[i]/255
            self.colors.append(tuple(ll))

    def process_file(self, wav_file_name):
        # function to load wav file and split into windows
        # file could be corrupt, surround with try except
        try:
            sig, sr = librosa.load(wav_file_name, sr=None)  # read the wav file
            duration = (len(sig)/sr)
            data = Data(wav_file_name, duration, sr, [])

        except Exception as e:
            print(e)
            return None

        # loop over file and create windows
        for i in range(self.window_length, min(math.ceil((len(sig) / float(sr)) * 1000), self.maximum_file_length), int(self.window_length * (1 - self.overlap))):

            start = (i - self.window_length) / \
                1000  # where to start in seconds
            end = i/1000  # where to end in seconds
            # get the portion of the signal we are interested in
            fsig = sig[int((start * sr)):int((end * sr))]

            # Unique name for the spectrogram image
            metadata = self._process_window(
                fsig, sr, i)
            if metadata is not None:
                data.metadata.append(metadata)

        return data

    def _process_window(self, sig, sr, window_offset):
        # Function to take a signal and return a spectrogram.

        root_size = int(0.001 * sr)  # 1.0ms resolution
        hop_length = int(root_size/4)

        # Short-time Fourier transform
        stft_spec_window = librosa.stft(sig, n_fft=root_size, hop_length=hop_length, win_length=root_size,
                                        window='hamming')

        # Calculating the spectrogram
        stft_spec_window = np.abs(stft_spec_window) ** 2
        stft_spec_window = librosa.power_to_db(stft_spec_window)

        frequency_bands = librosa.fft_frequencies(sr=sr, n_fft=root_size)

        # band pass filter between 5-100 kHz
        for i, b in enumerate(frequency_bands):
            if b <= 5000 or b >= min(100000, (sr / 2) - 2000):
                stft_spec_window[i] = [-500] * len(stft_spec_window[i])

        # find the index of the loudest sound in the spectrogram, hopefully a bat pulse
        index = np.unravel_index(
            stft_spec_window.argmax(), stft_spec_window.shape)
        time_index = index[1]  # time
        frequency_index = index[0]  # frequency

        # convert them to real values, seconds, Hz
        peak_frequency = frequency_bands[frequency_index]
        peak_time = time_index/4

        # make sure the peak frequency within the spectrogram is not on the edges
        # and make sure the peak frequency is within bat frequency ranges
        if peak_time < self.window_length * 0.2 or peak_time > self.window_length * 0.8:
            return None
        elif peak_frequency <= 5000 or peak_frequency >= min(100000, (sr / 2) - 2000):
            return None

        # denoise after finding peak time and frequency
        stft_spec_window = self._denoise_spec(stft_spec_window)

        # compute a ratio of the loudness of the peak frequency to the average loudness of the whole window
        freq_amp = stft_spec_window[frequency_index]
        r_other = np.sum(stft_spec_window) / \
            (len(stft_spec_window) * len(stft_spec_window[0]))
        rsig = sum(freq_amp[time_index - 4: time_index + 6]) / 10
        signal_noise_ratio = rsig/r_other
        amplitude = freq_amp[time_index]

        # Using signal_noise_ratio and amplitude to filter out low quality pulses
        if signal_noise_ratio >= self.sn_thresh and amplitude >= self.amp_thresh:
            # create the image
            img, buf = self._make_spectrogram(
                stft_spec_window, sr, hop_length, pt=peak_time/1000, pf=peak_frequency)
            img = np.array(img)
            img = img[..., :3].astype('float32')
            img /= 255.0
            buf.close()

            stft_spec_window = stft_spec_window.astype('float16')
            return Metadata(window_offset, peak_frequency, float(amplitude), peak_time, signal_noise_ratio, stft_spec_window, img)

    def _make_spectrogram(self, sig, sr, hop_length, pf=0, pt=0, low=5000, high=125000):
        # plot the spectrogram using matplotlib

        try:

            fig = plt.figure(figsize=(1, 5), facecolor='black',
                             dpi=50)
            ax0 = fig.add_axes([0, 0, 1, 1], facecolor='black')
            ax = [ax0]
            plt.margins(0)

            # Plot
            librosa.display.specshow(
                sig, sr=sr, hop_length=hop_length, x_axis='s', y_axis='linear', ax=ax[0])

            # draw the frequency targeting line with color scale
            color_i = int(pf/(high - low) * len(self.colors))
            ax[0].hlines(pf, pt - 0.01, pt + 0.01,
                         color=self.colors[color_i], lw=1)

            # center the pulse in the frame
            ylim_high = min(pf + 55000, high, sr/2)
            ax[0].set_ylim(max(pf - 25000, low), ylim_high)
            ax[0].axis('off')

            buf = io.BytesIO()
            fig.savefig(buf, facecolor='black', dpi=self.img_width,
                        bbox_inches='tight', pad_inches=0)
            buf.seek(0)
            im = Image.open(buf)

            return im, buf

        except Exception as e:
            print(e)
        finally:
            # clean up figure and release memory, if you dont do this matplotlib causes instance to crash
            fig.clf()
            plt.close()

    def _denoise_spec(self, spec):
        # subtract the row and then the column median from evey pixel then clip all values less then 0

        spec = spec - np.median(spec, axis=1, keepdims=True)
        spec = spec - np.median(spec, axis=0, keepdims=True)
        spec.clip(min=0, out=spec)
        return spec
