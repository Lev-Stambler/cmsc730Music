import time
import librosa
import matplotlib.pyplot as plt
import math
import threading
import librosa.display
import numpy as np
import sounddevice as sd
import soundfile as sf
import serial
# from bluetooth import *

N_PIXELS = 100
DEBUG = True

ser = serial.Serial('/dev/ttyUSB1', 115200)
serLights = serial.Serial('/dev/ttyUSB0', 115200)
# serLights  = ser
# serLights = serial.Serial('/dev/ttyUSB1', 115200)

i = 0

def sendSerMotor(data: str):
    datas = data.split("\n")
    for data in datas:
        data += "\r\n"
        if DEBUG:
            global i
            i += 1
            print("SENDING DATA MOTOR", i, data)
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


def formatPixelSet(pixels: list[int], Rs: list[int], Gs: list[int], Bs: list[int]):
    extra_str = ""
    for i in range(len(pixels)):
        extra_str += f":{str(pixels[i]).zfill(3)}:{str(Rs[i]).zfill(3)}:{str(Gs[i]).zfill(3)}:{str(Bs[i]).zfill(3)}"
    return f"L" + extra_str
    # return f"L:{str(pixel).zfill(3)}:{str(R).zfill(3)}:{str(G).zfill(3)}:{str(B).zfill(3)}"


def save_wav_file(y, sr, file_path):
    sf.write(file_path, y, sr)


def generateGaussianRandomMotorMovement(time_steps: int, volumes_diffs: list[int]):
    # TODO:
    # Max spin time
    N_ZONES = 6
    spin_per_zone = [0, 20, 40, 60, 120, 200]
    prob_spin = [0, 0.08, 0.2, 0.3, 0.4, 0.4]
    diff_min, diff_max = min(volumes_diffs), max(volumes_diffs)
    diff_separation = (diff_max - diff_min) / N_ZONES

    MAX_TOTAL_RET = 400
    MIN_TOTAL_RET = -400

    
    def sample(idx):
        # print(idx, N_ZONES)
        if np.random.random() < prob_spin[idx]:
            return spin_per_zone[idx], 3_000
        else:
            return 0, 0
    cmds: list[str] = []

    def get_volume_diff_partition(i):
        # TODO: WHAT
        return min(int((volumes_diffs[i] - diff_min) // diff_separation), N_ZONES - 1)

    N_STEPS_PER_MOVE = 8
    N_STEPS_PER_BREAK = 8
    last_change = 0
    curr_angle = 0
    curr_dir = 1
    change_period = False
    for i in range(time_steps):
        # TODO:: idk
        # if pixel
        # print("Color command", cmd)
        if i % N_STEPS_PER_MOVE == 0 and change_period == False:
            angle_samp, delay_samp = sample(get_volume_diff_partition(i))
            if curr_angle > MAX_TOTAL_RET and curr_dir == 1:
                change_period = True
                last_change = i
                curr_dir = -1
            elif curr_angle < MIN_TOTAL_RET and curr_dir == -1:
                change_period = True
                last_change = i
                curr_dir = 1
            angle_samp = curr_dir * angle_samp
            cmds.append(formatAngleMove(angle_samp, delay_samp))
            curr_angle += angle_samp
        elif i % N_STEPS_PER_MOVE == 0 and change_period == True and i - last_change > N_STEPS_PER_BREAK:
            change_period = False
            cmds.append("")
        else:
            cmds.append("")
    return cmds


def generateGaussianRandomDownwardLight(time_steps: int, volumes: list[int], gaussian_means: list[list[float]], gaussian_stds: list[list[float]],
                                        n_lights=N_PIXELS, top_pixel_is_max=True):
    """
        Sample from a Gaussian distribution which should have width to around 255ish.
        We will re-sample until we get a value that is within the range of 0-255.
    """
    assert len(gaussian_means) == len(
        gaussian_stds), "Must have same number of means and stds"

    N_VOLUME_SEPARATIONS = 6
    vol_min, vol_max = min(volumes), max(volumes)
    vol_separation = (vol_max - vol_min) / N_VOLUME_SEPARATIONS

    def sample():
        idx = np.random.choice(len(gaussian_means))
        normal_samp = np.random.normal(gaussian_means[idx], gaussian_stds[idx])
        if normal_samp.max() > 255 or normal_samp.min() < 0:
            return sample()
        return normal_samp.round().astype(int)
    cmds: list[str] = []

    if not top_pixel_is_max:
        raise NotImplementedError("Only top pixel is max is implemented")
    curr_light_step = 0

    def get_volume_partition(i):
        return int((volumes[i] - vol_min) // vol_separation)

    for i in range(time_steps):
        # TODO:: idk
        # if pixel
        # print("Color command", cmd)
        n_pixel_step = int(round(1.7 ** get_volume_partition(i)))
        # TODO: progromatting
        pixels = []
        Rs = []
        Gs = []
        Bs = []
        for j in range(n_pixel_step):
            pixel = (n_lights - curr_light_step % n_lights) - 1
            pixels.append(pixel)
            R, G, B = sample()
            Rs.append(R)
            Gs.append(G)
            Bs.append(B)
            curr_light_step += 1
        s = formatPixelSet(pixels, Rs, Gs, Bs)
        cmds.append(s)
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
    print(sr)
    # exit()

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
        volumes_diffs = []
        steps = []
        y_abs = np.abs(y)
        for i, _ in enumerate(downbeats):
            if i >= 1:
                period = downbeats[i] - downbeats[i - 1]
                for j in range(mul_fact):
                    steps.append(
                        int(round(downbeats[i - 1] + (period / mul_fact) * j)))

                    # Make it 1 second for now?
                    window_size = sr * 2
                    avg = sum(y_abs[beats[i] - window_size //
                              2:beats[i] + window_size // 2]) / window_size
                    if i == 1 and j == 0:
                        volumes_diffs.append(0)
                    else:
                        diff = avg - volumes[-1]
                        volumes_diffs.append(diff)
                    volumes.append(avg)
        return steps, volumes, volumes_diffs

    sample_timestamps, volumes, volume_diffs = add_downbeat_time_steps()
    # Plotting the volumes
    plt.figure(figsize=(10, 6))
    plt.plot(sample_timestamps, volumes, marker='o')
    plt.title('Average Volume at Downbeats')
    plt.xlabel('Sample Index')
    plt.ylabel('Average Volume')
    plt.grid(True)
    plt.savefig("test_vol.png")

    plt.figure(figsize=(10, 6))
    plt.plot(sample_timestamps, volume_diffs, marker='o')
    plt.title('Average Volume Diff at Downbeats')
    plt.xlabel('Sample Index')
    plt.ylabel('Average Volume Diff')
    plt.grid(True)
    plt.savefig("test_vol_diff.png")

    return sample_timestamps, volumes, volume_diffs


def send_motor_commands_at_downbeats(downbeat_times, sr, cmds):
    for i, downbeat_time in enumerate(downbeat_times):
        # Calculate the time to wait until the next downbeat
        wait_time = downbeat_time / sr
        # direction = 1 if i % 2 == 0 else -1
        threading.Timer(wait_time, sendSerMotor, args=[cmds[i]]).start()


def send_light_commands_at_downbeats(downbeat_times, sr, cmds):
    for i, downbeat_time in enumerate(downbeat_times):
        # print(cmds[i], i)
        # Calculate the time to wait until the next downbeat
        wait_time = downbeat_time / sr
        threading.Timer(wait_time, sendSerLights, args=[cmds[i]]).start()


def clearLights():
    sendSerMotor("C")


def do_it(filename, color_means, color_vars, window_length=0.2, amplification_factor=1.2):
    # Load the audio file
    y, sr = librosa.load(filename)
    time_steps, volumes, volumes_diffs = get_sample_moments(y, sr)

    # y_amplified = amplify_on_downbeats(
    #     y, sr, downbeat_times, amplification_factor=amplification_factor, window=window_length)

    clearLights()
    time.sleep(1)
    # Save the modified file
    # save_wav_file(y, sr, "out.wav")

    lightCmds = generateGaussianRandomDownwardLight(
        len(time_steps), volumes, color_means, color_vars)
    # motorCmds = generateGaussianRandomMotorMovement(
    #     len(time_steps), volumes_diffs)
    motorCmds = generateGaussianRandomMotorMovement(
        len(time_steps), volumes)
    # print("LEN LIGHTS", len(time_steps), len(lightCmds))

    # Create a thread for playing the music
    play_thread = threading.Thread(target=sd.play, args=(y, sr))

    # Start the play thread

    # Send serial commands at downbeats in a separate thread
    # send_motor_commands_thread = threading.Thread(
    #     target=send_serial_commands_at_downbeats, args=(time_steps, sr))

    send_light_commands_thread = threading.Thread(
        target=send_light_commands_at_downbeats, args=(time_steps, sr, lightCmds))

    send_motor_commands_thread = threading.Thread(
        target=send_motor_commands_at_downbeats, args=(time_steps, sr, motorCmds))

    play_thread.start()
    # send_motor_commands_thread.start()
    send_light_commands_thread.start()
    send_motor_commands_thread.start()

    # Wait for the play thread to finish
    play_thread.join()
    # send_motor_commands_thread.join()
    send_light_commands_thread.join()
    send_motor_commands_thread.join()

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
    color_means_melodic, color_vars_melodic = [[150, 10, 200], [20, 150, 200], [
        255, 0, 0], [10, 10, 10]], [[20, 2, 50], [10, 40, 50], [50, 20, 20], [2, 2, 2]]
    color_means_triumphant, color_vars_triumphant = [[250, 10, 10], [200, 10, 200], [
        255, 128, 0], [10, 10, 10]], [[10, 30, 30], [30, 40, 30], [2, 20, 1], [2, 2, 2]]
    # filename = 'EtudeC.mp3'
    filename = 'GirlFellTrimmed.mp3'
    # filename = 'Canon_in_F_minor.mp3'
    # filename = 'GirlFellTrimmed.mp3 '
    # filename = 'raindrop.mp3'
    upbeats = do_it(filename, color_means_melodic, color_vars_melodic)
    # print(upbeats)
