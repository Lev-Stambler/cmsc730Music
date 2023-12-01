import librosa
import threading
import librosa.display
import numpy as np
import sounddevice as sd
import soundfile as sf
import serial

ser = serial.Serial('/dev/ttyUSB0', 115200)


def sendSerData(data):
    data += "\r\n"
    print("SENDING DATA", data)
    ser.write(data.encode())

def formatAngleMove(angle, delayMicroSec=500):
    dir = "+" if angle > 0 else "-"
    angle = abs(angle)
    angle = str(angle).zfill(6)[:6]
    delayMicroSec = str(delayMicroSec).zfill(5)[:5]
    return f"{dir}:{angle}:{delayMicroSec}"


def save_wav_file(y, sr, file_path):
    sf.write(file_path, y, sr)


def amplify_on_downbeats(y, sr, downbeat_times, window=0.1, amplification_factor=1.5):
    # Calculate the number of samples to mute based on mute_duration
    mute_samples = int(window * sr)

    # For each downbeat, mute the signal
    for downbeat_time in downbeat_times:
        start_sample = int(round(downbeat_time))
        end_sample = start_sample + mute_samples
        print(sr, start_sample, end_sample, len(y))
        y[start_sample:end_sample] *= amplification_factor
    return y


def get_downbeat_sample_moments(y, sr):
    # Calculate the onset envelope
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)

    # Use the librosa's beat tracker with modified tightness
    # Adjust the tightness parameter for more flexibility in tempo variations
    tempo, beats = librosa.beat.beat_track(
        y=y, sr=sr, onset_envelope=onset_env, tightness=100, units='samples')

    # If you expect frequent tempo changes, you might divide the audio into segments and track beats segment-wise
    # But in this simple example, we'll just try to identify downbeats from the tracked beats

    downbeats = [beats[0]]
    # measures = int(tempo) # Initial assumption

    print(len(beats))
    new_tempo = 0
    for i in range(1, len(beats)):
        # Dynamically adjust the expected measure interval based on adjacent beat intervals
        if (i - 1) % 2 == 0:
            downbeats.append(beats[i])
        if i >= 2:
            interv = (beats[i] - beats[i-2]) / (2 * sr)
            # print(interv)
            new_tempo = 60 / (interv)
        # print(new_tempo)

        # if measures != 0 and (i % measures) == 0:
        #     print("ADDING DOWNBEAT", len(downbeats))
        #     downbeats.append(beats[i])

        # TODO: wjat these frames?
    # downbeat_times = librosa.frames_to_time(downbeats, sr=sr)
    return downbeats


def send_serial_commands_at_downbeats(downbeat_times, sr):
    for downbeat_time in downbeat_times:
        # Calculate the time to wait until the next downbeat
        wait_time = downbeat_time / sr
        threading.Timer(wait_time, sendSerData, args=[
                        formatAngleMove(100)]).start()


def do_it(filename, window_length=0.2, amplification_factor=1.5):
    # Load the audio file
    y, sr = librosa.load(filename)
    downbeat_times = get_downbeat_sample_moments(y, sr)
    y_amplified = amplify_on_downbeats(
        y, sr, downbeat_times, amplification_factor=amplification_factor, window=window_length)

    # Save the modified file
    save_wav_file(y_amplified, sr, "out.wav")

    # Create a thread for playing the music
    play_thread = threading.Thread(target=sd.play, args=(y_amplified, sr))

    # Start the play thread
    play_thread.start()

    # Send serial commands at downbeats in a separate thread
    send_serial_commands_thread = threading.Thread(
        target=send_serial_commands_at_downbeats, args=(downbeat_times, sr))
    send_serial_commands_thread.start()

    # Wait for the play thread to finish
    play_thread.join()
    send_serial_commands_thread.join()

# def do_it(filename, window_length=0.2, amplification_factor=.1):
#     # Load the audio file
#     y, sr = librosa.load(filename)
#     downbeat_times = get_downbeat_sample_moments(y, sr)
#     y_amplified = amplify_on_downbeats(y, sr, downbeat_times, amplification_factor=amplification_factor, window=window_length)

#     save_wav_file(y, sr, "out.wav")
#     sd.play(y_amplified, samplerate=sr)
#     sd.wait()


if __name__ == "__main__":
    # Example:
    filename = 'EtudeC.mp3'
    # filename = 'raindrop.mp3'
    upbeats = do_it(filename)
    print(upbeats)
