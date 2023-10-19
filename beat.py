import librosa
import librosa.display
import numpy as np
import sounddevice as sd

def amplify_on_downbeats(y, sr, downbeat_times, window=0.1, amplification_factor=1.5):
  # Calculate the number of samples to mute based on mute_duration
  mute_samples = int(window * sr)
    
  # For each downbeat, mute the signal
  for downbeat_time in downbeat_times:
    start_sample = downbeat_time
    end_sample = start_sample + mute_samples
    y[start_sample:end_sample] *= amplification_factor
  return y

def get_downbeat_times(y, sr):
  # Calculate the onset envelope
  onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    
  # Use the librosa's beat tracker with modified tightness
  # Adjust the tightness parameter for more flexibility in tempo variations
  tempo, beats = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env, tightness=100, units='samples')
    
  # If you expect frequent tempo changes, you might divide the audio into segments and track beats segment-wise
  # But in this simple example, we'll just try to identify downbeats from the tracked beats

  downbeats = [beats[0]]
  # measures = int(tempo) # Initial assumption

  print(len(beats))
  new_tempo = 0
  for i in range(1, len(beats)):
        # Dynamically adjust the expected measure interval based on adjacent beat intervals
        if i % 4 == 0:
          downbeats.append(beats[i])
        if i >= 2:
            interv = (beats[i] - beats[i-2]) / (2 * sr)
            print(interv)
            new_tempo = 60 / (interv)
        print(new_tempo)

        # if measures != 0 and (i % measures) == 0:
        #     print("ADDING DOWNBEAT", len(downbeats))
        #     downbeats.append(beats[i])

  downbeat_times = librosa.frames_to_time(downbeats, sr=sr)
  return downbeat_times

def do_it(filename, window_length=0.2, amplification_factor=0):
    # Load the audio file
    y, sr = librosa.load(filename)
    downbeat_times = get_downbeat_times(y, sr)
    y_amplified = amplify_on_downbeats(y, sr, downbeat_times, amplification_factor=amplification_factor, window=window_length)

    
    # Extract the onset envelope
    # onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    
    # # Detect beats
    # times = librosa.times_like(onset_env, sr=sr)
    # temp, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, tightness=100) 
    # # Amplify the region around each beat
    # for beat in beats:
    #     start_sample = int(max(0, beat - window_length/2) * sr)
    #     end_sample = int(min(len(y), beat + window_length/2) * sr)
    #     y[start_sample:end_sample] *= amplification_factor

    # Play back the modified audio
    sd.play(y_amplified, samplerate=sr)
    sd.wait()
    
# Example:
# filename = 'EtudeC.mp3'
filename = 'raindrop.mp3'
upbeats = do_it(filename)
print(upbeats)
