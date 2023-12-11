import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import beat
import get_mp3

file_name = ""


def process_mp3(_file_name, option):
    # Placeholder for your function that processes the MP3 file
    global file_name
    file_name = _file_name
    print(f"Processing {file_name} with option '{option}'")


def open_file_dialog():
    file_name = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
    if file_name:
        selected_option = dropdown_var.get()
        process_mp3(file_name, selected_option)


# Create the main window
root = tk.Tk()
root.title("MP3 File Processor")

# Create a dropdown menu
dropdown_var = tk.StringVar()

color_means_melodic, color_vars_melodic = [[150, 10, 200], [20, 150, 200], [
    255, 0, 0], [10, 10, 10]], [[20, 2, 50], [10, 40, 50], [50, 20, 20], [2, 2, 2]]
color_means_triumphant, color_vars_triumphant = [[250, 10, 10], [200, 10, 200], [
    255, 128, 0], [10, 10, 10]], [[10, 30, 30], [30, 40, 30], [2, 20, 1], [2, 2, 2]]

color_means_transcendant, color_vars_transcendant = [[25, 25, 112], [230, 190, 255], [
    255, 215, 0], [72, 209, 204], [10, 10, 10]], [[10, 10, 10], [10, 10, 10], [10, 10, 10], [10, 10, 10], [10, 10, 10]]

color_means_joyous, color_vars_joyous = [[255, 255, 0], [255, 127, 80], [
    30, 144, 255], [50, 205, 50], [10, 10, 10]], [[10, 10, 10], [10, 10, 10], [10, 10, 10], [10, 10, 10], [10, 10, 10]]

colors = {
    "melodic": [color_means_melodic, color_vars_melodic],
    "triumphant": [color_means_triumphant, color_vars_triumphant],
    "transcendant": [color_means_transcendant, color_vars_transcendant],
    "joyous": [color_means_joyous, color_vars_joyous]
}

dropdown_options = list(colors.keys())  # Replace with your options
dropdown = ttk.Combobox(root, textvariable=dropdown_var,
                        values=dropdown_options)
dropdown.current(0)  # Set the default value
dropdown.pack(pady=10)

input_frame = tk.Frame(root)
input_frame.pack(pady=10)


# Create a button that opens the file dialog
open_file_button = tk.Button(
    input_frame, text="Open MP3 File", command=open_file_dialog)
open_file_button.pack(pady=20)

# Label for "or"
or_label = tk.Label(input_frame, text="or give a Youtube URL:")
or_label.pack(side=tk.LEFT, padx=5)

# Text entry box
input_entry = tk.Entry(input_frame)
input_entry.pack(side=tk.LEFT)

time_stamp_frame = tk.Frame(root)
time_stamp_frame.pack(pady=10)
start_time_label = tk.Label(time_stamp_frame, text="Start Time (e.g., 00:00):")
start_time_label.pack(side=tk.LEFT)
start_time_entry = tk.Entry(time_stamp_frame, width=10)
start_time_entry.pack(side=tk.LEFT, padx=5)

# End time entry
end_time_label = tk.Label(time_stamp_frame, text="End Time (e.g., 05:00):")
end_time_label.pack(side=tk.LEFT)
end_time_entry = tk.Entry(time_stamp_frame, width=10)
end_time_entry.pack(side=tk.LEFT, padx=5)


def on_submit():

    selected_option = dropdown_var.get()
    yt = False
    if input_entry.get().startswith("https://www.youtube.com/"):
        yt = True
        start_time = start_time_entry.get()
        end_time = end_time_entry.get()
        print(f"Start time: {start_time}, End time: {end_time}")
        start_time_seconds = int(start_time.split(":")[0]) * 60 + \
            int(start_time.split(":")[1])
        end_time_seconds = int(end_time.split(":")[0]) * 60 + \
            int(end_time.split(":")[1])
        get_mp3.get_mp3(input_entry.get(),
                        start_time_seconds, end_time_seconds)
        _file_name = get_mp3.yt_download_name + ".trim.mp3"
    else:
        # global file_name
        _file_name = file_name
    # process_mp3(file_name, selected_option)
    print(f"Processing {_file_name} with option '{selected_option}'")
    beat.do_it(_file_name, colors[selected_option]
               [0], colors[selected_option][1])


submit_button = tk.Button(root, text="Submit", command=on_submit)
submit_button.pack(pady=20)

# Run the application
root.mainloop()
