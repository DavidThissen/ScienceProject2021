import pyaudio
import wave
import struct
import math
#import pylab
import scipy
import numpy
import os
import scipy.io.wavfile
import threading
import datetime
import time
import matplotlib.pyplot
from tkinter import *


class Sonar:

    # Mic initialization and audio recording code was taken from this example on StackOverflow: http://stackoverflow.com/questions/4160175/detect-tap-with-pyaudio-from-live-mic
    # Playback code based on Pyaudio documentation

    def callback(self, in_data, frame_count, time_info, status):
        data = self.wf.readframes(frame_count)
        return (data, pyaudio.paContinue)

    def __init__(self):
        self.FORMAT = pyaudio.paInt16
        self.SHORT_NORMALIZE = (1.0 /32768.0)
        CHANNELS = 2
        self.RATE = 48000
        INPUT_BLOCK_TIME = 0.2
        self.INPUT_FRAMES_PER_BLOCK = int(self.RATE * INPUT_BLOCK_TIME)
        WAVFILE = "test.wav"

        print("Initializing sonar object...")
        # Load chirp wavefile
        self.wf = wave.open(WAVFILE, 'rb')
        # init pyaudio
        self.pa = pyaudio.PyAudio()

        # identify mic device
        self.device_index = None
        for i in range( self.pa.get_device_count() ):
            devinfo = self.pa.get_device_info_by_index(i)
            print( "Device %d: %s " %(i ,devinfo["name"]) )

            for keyword in ["polycom"]:
                if keyword in devinfo["name"].lower():
                    print( "Found an input: device %d - %s " %(i ,devinfo["name"]) )
                    self.device_index = i    # I selected a specific mic - I needed the USB mic. You can select an input device from the list that prints.

        if self.device_index == None:
            print( "No preferred input found; using default input device." )

        # open output stream using callback
        self.stream = self.pa.open(format=self.pa.get_format_from_width(self.wf.getsampwidth()),
                                   channels=self.wf.getnchannels(),
                                   rate=self.wf.getframerate(),
                                   output=True,
                                   stream_callback=self.callback)

        notNormalized = []
        self.chirp = []

        # read in chirp wav file to correlate against
        srate, notNormalized = scipy.io.wavfile.read(WAVFILE)

        for sample in notNormalized:
            # sample is a signed short in +/- 32768.
            # normalize it to 1.0
            n = sample * self.SHORT_NORMALIZE
            self.chirp.append(n)


    def ping(self):
        # send ping of sound

        # set up input stream
        self.istream = self.pa.open(format = self.FORMAT,
                                    channels = 1,  # The USB mic is only mono
                                    rate = self.RATE,
                                    input = True,
                                    input_device_index = self.device_index,
                                    frames_per_buffer = self.INPUT_FRAMES_PER_BLOCK)


        # start the stream
        self.stream.start_stream()

        # wait for stream to finish
        while self.stream.is_active():
            pass

        self.stream.stop_stream()
        # reset wave file for next ping
        self.wf.rewind()

    def listen(self):
        # record a sort section of sound to record the returned echo

        self.samples = []

        try:
            block = self.istream.read(self.INPUT_FRAMES_PER_BLOCK)
        except (IOError) as e:
            # Something bad happened during recording
            print( "(%d) Error recording: %s " %(self.errorcount ,e) )

        count = len(block ) /2
        print("Count:", count)
        format = "%dh " %(count)
        shorts = struct.unpack( format, block )
        for sample in shorts:
            # sample is a signed short in +/- 32768.
            # normalize it to 1.0
            n = sample * self.SHORT_NORMALIZE
            self.samples.append(n)

        self.istream.close()
        print("Samples:", len(self.samples))
        # Uncomment these lines to graph the samples. Useful for debugging.
        # matplotlib.pyplot.plot(self.samples)
        # matplotlib.pyplot.show()
        self.pinged = 0
        maxsample = max(self.samples)
        if (maxsample > 0.9):
            self.pinged = 1


    def correlate(self):

        # perform correlation by multiplying the signal by the chirp, then shifting over one sample and doing it again. Highest peaks correspond to best matches of original signal.
        # Highest peak will be when the mic picks up the speaker sending the pings. Then secondary peaks represent echoes.

        junkThreshold = 5000
        self.samples = self.samples[junkThreshold:]

        self.result = []

        for offset in range(0, len(self.samples ) -len(self.chirp)):
            temp = 0
            for a in range(0, len(self.chirp)):
                temp = temp + (self.chirp[a] * self.samples[a + offset])


            self.result.append(temp)


    def clip(self):
        # highest peak is the primary pulse. We don't need the audio before that, or the chirp itself. Strip it + chirpLength off. Remaining highest peaks are echoes.
        largest = 0
        peak1 = 0
        for c in range(len(self.result)):
            if (self.result[c] > largest):
                largest = self.result[c]
                peak1 = c

        self.result = self.result[peak1:]
        #return self.result
        return peak1

    def find_echo(self):
        largest = 0
        peak2 = -1
        for c in range(len(self.result)):

            if (self.result[c] > largest and c>770 and c<820):
#            if (self.result[c] > largest and c>400):
                largest = self.result[c]
#                peak2 = c
                peak2 = c//2

        return peak2

def countX(lst, x):
    count = 0
    for ele in lst:
        if (ele == x):
            count = count + 1
    return count

DistanceFt = 4.6
DistanceSoundTravelsFt = DistanceFt * 2
DistanceSoundTravels = DistanceSoundTravelsFt * 0.3048

#Loop 100 times

OutList = []
RecordedResult = []
for n in range(60):
  # Send and Recieve a ping
  sonar = Sonar()
  sonar.ping()
  sonar.listen()
  sonar.correlate()

  # Find initial ping in recording (this is the ping)
  result = sonar.clip()

  # Find the next largest sample in the recording (this is the echo)
  EchoFrame = sonar.find_echo()
  print("EchoFrame:", EchoFrame)

  # Multiplying by the inverse of the frame rate gives the time of the echo
  TimeInSeconds = EchoFrame / sonar.RATE
  SpeedOfSound = DistanceSoundTravels/TimeInSeconds

  print("Distance:", DistanceSoundTravels, "Time:", TimeInSeconds, "Speed:", SpeedOfSound)
  RecordedResult = []
  RecordedResult.append(DistanceSoundTravels)
  RecordedResult.append(TimeInSeconds)
  RecordedResult.append(SpeedOfSound)
  if (sonar.pinged == 1):
      OutList.append(RecordedResult)

  time.sleep(0.25)

print("Distance Time Speed:")
for n in range(len(OutList)):
  print(n, " ", OutList[n][0], " ", OutList[n][1], " ", OutList[n][2])
