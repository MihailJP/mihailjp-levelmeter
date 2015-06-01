#!/usr/bin/env python

import alsaaudio as alsa
import struct
from optparse import OptionParser
from sys import stdout, exit
import math

parser = OptionParser()
parser.add_option('-c', '--channels', dest='ch', type='int', default=2, help="numbers of channels [default: %default]")
parser.add_option('-r', '--rate', dest='rate', type='int', default=44100, help="sampling rate [default: %default]")
(options, args) = parser.parse_args()

PCMCHANNEL = options.__dict__['ch']
PCMRATE    = options.__dict__['rate']

WaveDat = [[]] * PCMCHANNEL
Peak = [0] * PCMCHANNEL

Fullscale = (1 << 15) - 1
LogFS = math.log10(Fullscale)

pcm = alsa.PCM(type=alsa.PCM_CAPTURE, mode=alsa.PCM_NONBLOCK)
pcm.setchannels(PCMCHANNEL)
pcm.setrate(PCMRATE)
pcm.setformat(alsa.PCM_FORMAT_S16_LE)
pcm.setperiodsize(int(PCMRATE/50))

def parsePCM(WaveDat, pcmDat):
	dat = struct.unpack('<' + 'h' * PCMCHANNEL * pcmdat[0], pcmDat[1])
	for ch in range(0, PCMCHANNEL):
		WaveDat[ch] += dat[ch::PCMCHANNEL]
		WaveDat[ch] = WaveDat[ch][-int(PCMRATE * 3 / 10):]

def getRMS(WaveDat):
	rms = []
	for ch in range(0, PCMCHANNEL):
		rms += [math.sqrt(sum(map(lambda x: x * x, WaveDat[ch])) / len(WaveDat[ch]))]
	return tuple(rms)

def updatePeak(WaveDat):
	global Peak
	for ch in range(0, PCMCHANNEL):
		tmppeak = max(map(abs, WaveDat[ch]))
		if tmppeak >= Peak[ch]:
			Peak[ch] = tmppeak
		else:
			Peak[ch] = math.floor(Peak[ch] * 0.9)

def corr(WaveDat):
	if PCMCHANNEL == 2:
		try:
			avg = map(lambda x: sum(x) / len(x), WaveDat)
			varVector = map(lambda x, a: map(lambda p: p - a, x), WaveDat, avg)
			samples = min(len(varVector[0]), len(varVector[1]))
			return sum(map(lambda x, y: x * y, varVector[0][0:samples], varVector[1][0:samples])) \
				/ (math.sqrt(sum(map(lambda x: x * x, varVector[0]))) * math.sqrt(sum(map(lambda x: x * x, varVector[1]))))
		except ZeroDivisionError:
			return float('nan')
	else:
		return None

def dbFS(val):
	global LogFS
	if val == 0:
		return float('-inf')
	else:
		return 20 * (math.log10(val) - LogFS)

correlation = 0; corrTiming = 0
stdout.write("\n" * PCMCHANNEL)
if PCMCHANNEL == 2:
	stdout.write("\n")
try:
	while True:
		pcmdat = pcm.read()
		if pcmdat[0] > 0:
			parsePCM(WaveDat, pcmdat)
			updatePeak(WaveDat)
			rmsVal = map(dbFS, getRMS(WaveDat))
			peakVal = map(dbFS, Peak)
			corrTiming += 1
			if corrTiming >= 10:
				correlation = corr(WaveDat)
				corrTiming = 0
			if PCMCHANNEL == 2:
				stdout.write("\x1b[3A")
			else:
				stdout.write("\x1b["+str(PCMCHANNEL)+"A")
			for ch in range(0, PCMCHANNEL):
				dRange = peakVal[ch] - rmsVal[ch]
				stdout.write("[Ch{0}] RMS:{1:6.1f} Peak:{2:6.1f} DRange: {3:6.1f}\n".format(ch+1, rmsVal[ch], peakVal[ch], dRange))
			if PCMCHANNEL == 2:
				stdout.write("[Corr] {0:6.3f}\n".format(correlation))
			stdout.flush()
except KeyboardInterrupt:
	print ""
	stdout.flush()
	exit(0)
