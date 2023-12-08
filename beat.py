import time
import librosa
import math
import threading
import librosa.display
import numpy as np
import sounddevice as sd
import soundfile as sf
import serial

N_PIXELS = 100
DEBUG = True

ser = serial.Serial('/dev/ttyUSB0', 115200)
# serLights = serial.Serial('/dev/ttyUSB1', 115200)
serLights  = ser

i = 0

def sendSerData(data):
    data += "\r\n"
    if DEBUG:
        global i
        i += 1
        print("SENDING DATA", i, data)
    ser.write(data.encode())

def sendSerLights(data):
    data += "\r\n"
    if DEBUG:
        global i
        i += 1
        print("SENDING DATA", i, data)
    serLights.write(data.encode())



def formatAngleMove(angle, delayMicroSec=500):
    dir = "+" if angle > 0 else "-"
    angle = abs(angle)
    angle = str(angle).zfill(6)[:6]
    delayMicroSec = str(delayMicroSec).zfill(5)[:5]
    return f"{dir}:{angle}:{delayMicroSec}"

def formatPixelSet(pixel, R, G, B):
    return f"L:{str(pixel).zfill(3)}:{str(R).zfill(3)}:{str(G).zfill(3)}:{str(B).zfill(3)}"


def save_wav_file(y, sr, file_path):
    sf.write(file_path, y, sr)

def generateGaussianRandomDownwardLight(time_steps: int, volumes: list[int], gaussian_means: list[list[float]], gaussian_stds: list[list[float]],
                                        n_lights=N_PIXELS, top_pixel_is_max = True):
    """
        Sample from a Gaussian distribution which should have width to around 255ish.
        We will re-sample until we get a value that is within the range of 0-255.
    """
    assert len(gaussian_means) == len(gaussian_stds), "Must have same number of means and stds"
    print(max(volumes), min(volumes))
    def sample():
        idx = np.random.choice(len(gaussian_means))
        normal_samp = np.random.normal(gaussian_means[idx], gaussian_stds[idx])
        if normal_samp.max() > 255 or normal_samp.min() < 0:
            return sample()
        return normal_samp.round().astype(int)
    cmds = []

    if not top_pixel_is_max:
        raise NotImplementedError("Only top pixel is max is implemented")
    for i in range(time_steps):
        # TODO:: idk
        pixel = (n_lights - i % n_lights) - 1
        # if pixel 
        cmd = formatPixelSet(pixel, *sample())
        print("Color command", cmd)
        cmds.append(cmd)
    return cmds
    # Start

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

def get_sample_moments(y, sr, downbeat_subdivisions=16):
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
    for i in range(1, len(beats)):
        # Dynamically adjust the expected measure interval based on adjacent beat intervals
        INTERV = 1
        if (i - 1) % INTERV == 0:
            downbeats.append(beats[i])
        
    def add_downbeat_time_steps(mul_fact=16):
        volumes = []
        steps = []
        for i, _ in enumerate(downbeats):
            if i >= 1:
                period = downbeats[i] - downbeats[i - 1]
                for j in range(mul_fact):
                    steps.append(int(round(downbeats[i - 1] + (period / mul_fact) * j)))
                    start_index = max(beats[i] - 10, 0)  # Ensuring the start index is not negative
                    end_index = min(beats[i] + 10, len(y))  # Ensuring the end index does not exceed the length of y
                    average_volume = np.mean(np.abs(y[start_index:end_index]))
                    volumes.append(average_volume)
        return steps, volumes

    sample_timestamps, volumes = add_downbeat_time_steps()
    return sample_timestamps, volumes


def send_serial_commands_at_downbeats(downbeat_times, sr):
    for i, downbeat_time in enumerate(downbeat_times):
        # Calculate the time to wait until the next downbeat
        wait_time = downbeat_time / sr
        direction = 1 if i % 2 == 0 else -1
        threading.Timer(wait_time, sendSerData, args=[
                        formatAngleMove(direction * 100)]).start()

def send_light_commands_at_downbeats(downbeat_times, sr, cmds):
    for i, downbeat_time in enumerate(downbeat_times):
        # print(volumes[i], i)
        # Calculate the time to wait until the next downbeat
        wait_time = downbeat_time / sr
        threading.Timer(wait_time, sendSerData, args=[cmds[i]]).start()

def clearLights():
    sendSerData("C")

def do_it(filename, window_length=0.2, amplification_factor=1.2):
    # Load the audio file
    y, sr = librosa.load(filename)
    time_steps, volumes = get_sample_moments(y, sr)

    # y_amplified = amplify_on_downbeats(
    #     y, sr, downbeat_times, amplification_factor=amplification_factor, window=window_length)

    clearLights()
    time.sleep(1)
    # Save the modified file
    # save_wav_file(y, sr, "out.wav")

    lightCmds = generateGaussianRandomDownwardLight(len(time_steps), volumes, [[150, 10, 200], [20, 150, 200], [255, 0, 0], [10, 10, 10]], [[20, 2, 50], [10, 40, 50], [50, 20, 20], [2, 2, 2]])
    print("LEN LIGHTS", len(time_steps), len(lightCmds))

    # Create a thread for playing the music
    play_thread = threading.Thread(target=sd.play, args=(y, sr))

    # Start the play thread

    # Send serial commands at downbeats in a separate thread
    # send_motor_commands_thread = threading.Thread(
    #     target=send_serial_commands_at_downbeats, args=(time_steps, sr))

    send_light_commands_thread = threading.Thread(
        target=send_light_commands_at_downbeats, args=(time_steps, volumes, sr, lightCmds))

    play_thread.start()
    # send_motor_commands_thread.start()
    send_light_commands_thread.start()
    
    # Wait for the play thread to finish
    play_thread.join()
    # send_motor_commands_thread.join()
    send_light_commands_thread.join()

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
    filename = 'GirlFellTrimmed.mp3'
    # filename = 'raindrop.mp3'
    upbeats = do_it(filename)
    print(upbeats)
