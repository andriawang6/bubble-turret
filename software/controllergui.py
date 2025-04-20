import serial
import time
import tkinter as tk
import threading
import json
import os

class ControllerGUI:
    def __init__(self, root):
        self.last_direction = ''
        self.hold_active = False
        self.hold_interval = 100

        self.root = root
        self.root.title("Arduino Servo Controller")
        self.root.geometry("1280x720")
        self.root.resizable(True, True)

        self.port = '/dev/tty.DSDTECHHC-05'
        self.bluetooth = None
        self.is_connected = False
        self.connection_thread = None

        self.is_recording = False
        self.recording = []
        self.playback_thread = None
        self.is_playing = False
        self.saved_recordings = {}
        self.recordings_dir = "recordings"

        if not os.path.exists(self.recordings_dir):
            os.makedirs(self.recordings_dir)

        self.load_recordings()

        self.main_frame = tk.Frame(root, padx=20, pady=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.setup_connection_section()
        self.setup_controls_section()
        self.setup_recording_section()
        self.setup_playback_section()
        self.setup_console_section()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.toggle_control_buttons(False)

    def setup_connection_section(self):
        self.connection_frame = tk.LabelFrame(self.main_frame, text="Connection", padx=10, pady=10)
        self.connection_frame.pack(fill=tk.X, pady=10)

        self.port_label = tk.Label(self.connection_frame, text="Port:")
        self.port_label.grid(row=0, column=0, padx=5, pady=5)

        self.port_entry = tk.Entry(self.connection_frame, width=20)
        self.port_entry.insert(0, self.port)
        self.port_entry.grid(row=0, column=1, padx=5, pady=5)

        self.connect_button = tk.Button(self.connection_frame, text="Connect", command=self.connect)
        self.connect_button.grid(row=0, column=2, padx=5, pady=5)

        self.disconnect_button = tk.Button(self.connection_frame, text="Disconnect", command=self.disconnect, state=tk.DISABLED)
        self.disconnect_button.grid(row=0, column=3, padx=5, pady=5)

        self.status_label = tk.Label(self.connection_frame, text="Status: Disconnected", fg="red")
        self.status_label.grid(row=0, column=4, padx=5, pady=5)

    def setup_controls_section(self):
        self.controls_frame = tk.LabelFrame(self.main_frame, text="Controls", padx=10, pady=10)
        self.controls_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.joystick_frame = tk.Frame(self.controls_frame, width=300, height=300)
        self.joystick_frame.pack(side=tk.LEFT, padx=20, pady=20)

        self.canvas = tk.Canvas(self.joystick_frame, width=200, height=200, bg="lightgray")
        self.canvas.pack()

        self.base_radius = 80
        self.canvas.create_oval(100 - self.base_radius, 100 - self.base_radius, 100 + self.base_radius, 100 + self.base_radius, fill="gray", outline="black", width=2)

        self.handle_radius = 20
        self.handle = self.canvas.create_oval(100 - self.handle_radius, 100 - self.handle_radius, 100 + self.handle_radius, 100 + self.handle_radius, fill="red", outline="black", width=2)

        self.canvas.bind("<Button-1>", self.start_move)
        self.canvas.bind("<ButtonRelease-1>", self.stop_move)
        self.canvas.bind("<B1-Motion>", self.move_joystick)
        self.canvas.bind("<ButtonRelease-1>", self.reset_joystick)

        self.buttons_frame = tk.Frame(self.controls_frame)
        self.buttons_frame.pack(side=tk.RIGHT, padx=20, pady=20)

        self.up_button = tk.Button(self.buttons_frame, text="Up", width=8, command=lambda: self.send_command('u'))
        self.up_button.grid(row=0, column=1, padx=5, pady=5)

        self.left_button = tk.Button(self.buttons_frame, text="Left", width=8, command=lambda: self.send_command('l'))
        self.left_button.grid(row=1, column=0, padx=5, pady=5)

        self.center_button = tk.Button(self.buttons_frame, text="Center", width=8, command=self.reset_position)
        self.center_button.grid(row=1, column=1, padx=5, pady=5)

        self.right_button = tk.Button(self.buttons_frame, text="Right", width=8, command=lambda: self.send_command('r'))
        self.right_button.grid(row=1, column=2, padx=5, pady=5)

        self.down_button = tk.Button(self.buttons_frame, text="Down", width=8, command=lambda: self.send_command('d'))
        self.down_button.grid(row=2, column=1, padx=5, pady=5)

        self.up_left_button = tk.Button(self.buttons_frame, text="↖", width=4, command=lambda: self.send_diagonal('ul'))
        self.up_left_button.grid(row=0, column=0, padx=5, pady=5)

        self.up_right_button = tk.Button(self.buttons_frame, text="↗", width=4, command=lambda: self.send_diagonal('ur'))
        self.up_right_button.grid(row=0, column=2, padx=5, pady=5)

        self.down_left_button = tk.Button(self.buttons_frame, text="↙", width=4, command=lambda: self.send_diagonal('dl'))
        self.down_left_button.grid(row=2, column=0, padx=5, pady=5)

        self.down_right_button = tk.Button(self.buttons_frame, text="↘", width=4, command=lambda: self.send_diagonal('dr'))
        self.down_right_button.grid(row=2, column=2, padx=5, pady=5)

    def setup_recording_section(self):
        self.recording_frame = tk.LabelFrame(self.main_frame, text="Recording Controls", padx=10, pady=10)
        self.recording_frame.pack(fill=tk.X, pady=10)

        self.record_button = tk.Button(self.recording_frame, text="Start Recording", fg="black", command=self.toggle_recording, width=15)
        self.record_button.grid(row=0, column=0, padx=5, pady=5)

        self.save_name_label = tk.Label(self.recording_frame, text="Recording Name:", fg="white")
        self.save_name_label.grid(row=0, column=1, padx=5, pady=5)

        self.save_name_entry = tk.Entry(self.recording_frame, width=20, fg="black", bg="white")
        self.save_name_entry.insert(0, "New Recording")
        self.save_name_entry.grid(row=0, column=2, padx=5, pady=5)

        self.save_button = tk.Button(self.recording_frame, text="Save Recording", fg="black", command=self.save_recording, width=15, state=tk.DISABLED)
        self.save_button.grid(row=0, column=3, padx=5, pady=5)

    def setup_playback_section(self):
        self.playback_frame = tk.LabelFrame(self.main_frame, text="Playback Controls", padx=10, pady=10)
        self.playback_frame.pack(fill=tk.X, pady=10)

        self.recording_label = tk.Label(self.playback_frame, text="Select Recording:", fg="white")
        self.recording_label.grid(row=0, column=0, padx=5, pady=5)

        self.recording_var = tk.StringVar(self.root)
        self.recording_dropdown = tk.OptionMenu(self.playback_frame, self.recording_var, "")
        self.recording_dropdown.config(width=20, fg="black", bg="white")
        self.recording_dropdown.grid(row=0, column=1, padx=5, pady=5)
        self.update_recording_dropdown()

        self.play_button = tk.Button(self.playback_frame, text="Play", fg="black", command=self.play_recording, width=10)
        self.play_button.grid(row=0, column=2, padx=5, pady=5)

        self.stop_button = tk.Button(self.playback_frame, text="Stop", fg="black", command=self.stop_playback, width=10, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=3, padx=5, pady=5)

        self.delete_button = tk.Button(self.playback_frame, text="Delete Recording", fg="black", command=self.delete_recording, width=15)
        self.delete_button.grid(row=0, column=4, padx=5, pady=5)

        self.loop_var = tk.BooleanVar()
        self.loop_check = tk.Checkbutton(self.playback_frame, text="Loop Playback", fg="white", variable=self.loop_var)
        self.loop_check.grid(row=0, column=5, padx=5, pady=5)

    def setup_console_section(self):
        self.console_frame = tk.LabelFrame(self.main_frame, text="Console", padx=10, pady=10)
        self.console_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.console = tk.Text(self.console_frame, height=5, width=50)
        self.console.pack(fill=tk.BOTH, expand=True)
        self.console.config(state=tk.DISABLED)

    def toggle_control_buttons(self, state):
        state_value = tk.NORMAL if state else tk.DISABLED
        self.up_button.config(state=state_value)
        self.down_button.config(state=state_value)
        self.left_button.config(state=state_value)
        self.right_button.config(state=state_value)
        self.center_button.config(state=state_value)
        self.up_left_button.config(state=state_value)
        self.up_right_button.config(state=state_value)
        self.down_left_button.config(state=state_value)
        self.down_right_button.config(state=state_value)

    def toggle_recording_buttons(self, state):
        state_value = tk.NORMAL if state else tk.DISABLED
        self.record_button.config(state=state_value)
        self.recording_dropdown.config(state=state_value)
        self.play_button.config(state=state_value)
        self.delete_button.config(state=state_value)
        self.loop_check.config(state=state_value)

    def log_to_console(self, message):
        self.console.config(state=tk.NORMAL)
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)
        self.console.config(state=tk.DISABLED)

    def connect(self):
        port = self.port_entry.get()
        self.connection_thread = threading.Thread(target=self.connect_thread, args=(port,))
        self.connection_thread.daemon = True
        self.connection_thread.start()

    def connect_thread(self, port):
        try:
            self.log_to_console(f"Connecting to {port}...")
            self.bluetooth = serial.Serial(port, 9600, timeout=5)
            time.sleep(1)
            self.root.after(0, self.connection_successful)
        except serial.SerialException as e:
            self.root.after(0, lambda: self.connection_failed(f"Serial port error: {e}"))
        except FileNotFoundError:
            self.root.after(0, lambda: self.connection_failed(f"Error: Serial port '{port}' not found."))
        except Exception as e:
            self.root.after(0, lambda: self.connection_failed(f"An unexpected error occurred: {e}"))

    def connection_successful(self):
        self.is_connected = True
        self.status_label.config(text="Status: Connected", fg="green")
        self.connect_button.config(state=tk.DISABLED)
        self.disconnect_button.config(state=tk.NORMAL)
        self.port_entry.config(state=tk.DISABLED)
        self.toggle_control_buttons(True)
        self.toggle_recording_buttons(True)
        self.log_to_console("Bluetooth connected successfully.")

    def connection_failed(self, message):
        self.log_to_console(message)
        self.is_connected = False
        self.status_label.config(text="Status: Connection Failed", fg="red")

    def disconnect(self):
        if self.is_connected and self.bluetooth is not None:
            try:
                self.bluetooth.close()
                self.log_to_console("Bluetooth connection closed.")
            except Exception as e:
                self.log_to_console(f"Error closing connection: {e}")
            self.is_connected = False
            self.status_label.config(text="Status: Disconnected", fg="red")
            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.NORMAL)
            self.toggle_control_buttons(False)
            self.reset_joystick()

    def send_command(self, cmd):
        if self.is_connected and self.bluetooth is not None:
            try:
                self.bluetooth.write(cmd.encode())
                self.log_to_console(f"Sent command: {cmd}")
                if self.is_recording:
                    timestamp = time.time()
                    if not self.recording:
                        self.recording_start_time = timestamp
                        relative_time = 0
                    else:
                        relative_time = timestamp - self.recording_start_time
                    self.recording.append({'command': cmd, 'time': relative_time})
                    self.log_to_console(f"Recorded command: {cmd} at {relative_time:.2f}s")
            except Exception as e:
                self.log_to_console(f"Error sending command: {e}")
                self.disconnect()
        else:
            self.log_to_console("Not connected. Cannot send command.")

    def send_diagonal(self, direction):
        if direction == 'ul':
            self.send_command('u')
            time.sleep(0.1)
            self.send_command('l')
        elif direction == 'ur':
            self.send_command('u')
            time.sleep(0.1)
            self.send_command('r')
        elif direction == 'dl':
            self.send_command('d')
            time.sleep(0.1)
            self.send_command('l')
        elif direction == 'dr':
            self.send_command('d')
            time.sleep(0.1)
            self.send_command('r')

    def reset_position(self):
        self.send_command('c')
        self.reset_joystick()

    def start_move(self, event):
        self.last_x = event.x
        self.last_y = event.y
        self.move_joystick(event)

    def stop_move(self, event):
        self.reset_joystick()

    def reset_joystick(self, event=None):
        self.canvas.coords(self.handle, 100 - self.handle_radius, 100 - self.handle_radius, 100 + self.handle_radius, 100 + self.handle_radius)
        self.last_direction = ''
        self.hold_active = False
        if hasattr(self, 'repeat_task'):
            try:
                self.root.after_cancel(self.repeat_task)
            except:
                pass

    def move_joystick(self, event):
        center_x, center_y = 100, 100
        dx = event.x - center_x
        dy = event.y - center_y
        distance = (dx ** 2 + dy ** 2) ** 0.5

        if distance > self.base_radius - self.handle_radius:
            scale = (self.base_radius - self.handle_radius) / distance
            dx *= scale
            dy *= scale

        new_x = center_x + dx
        new_y = center_y + dy

        coords = self.canvas.coords(self.handle)
        current_x = (coords[0] + coords[2]) / 2
        current_y = (coords[1] + coords[3]) / 2
        self.canvas.move(self.handle, new_x - current_x, new_y - current_y)

        threshold = 20
        direction = ''
        if dy < -threshold:
            direction += 'u'
        elif dy > threshold:
            direction += 'd'
        if dx < -threshold:
            direction += 'l'
        elif dx > threshold:
            direction += 'r'

        if direction != self.last_direction:
            self.last_direction = direction
            if direction:
                self.send_command(direction)
            self.hold_active = bool(direction)

        self.send_command(direction)

    def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.recording = []
            self.recording_start_time = time.time()
            self.record_button.config(text="Stop Recording", bg="darkred")
            self.save_button.config(state=tk.DISABLED)
            self.log_to_console("Recording started. Move the joystick or press buttons.")
        else:
            self.is_recording = False
            self.record_button.config(text="Start Recording", bg="red")
            self.save_button.config(state=tk.NORMAL)
            self.log_to_console(f"Recording stopped. {len(self.recording)} commands recorded.")

    def save_recording(self):
        if not self.recording:
            self.log_to_console("Nothing to save. Recording is empty.")
            return

        name = self.save_name_entry.get().strip()
        if not name:
            self.log_to_console("Please enter a name for the recording.")
            return

        self.saved_recordings[name] = self.recording

        try:
            filepath = os.path.join(self.recordings_dir, f"{name}.json")
            with open(filepath, 'w') as f:
                json.dump(self.recording, f, indent=2)
            self.log_to_console(f"Recording '{name}' saved successfully with {len(self.recording)} commands.")
            self.save_button.config(state=tk.DISABLED)
            self.update_recording_dropdown()
        except Exception as e:
            self.log_to_console(f"Error saving recording: {e}")

    def load_recordings(self):
        try:
            if not os.path.exists(self.recordings_dir):
                return

            for filename in os.listdir(self.recordings_dir):
                if filename.endswith('.json'):
                    name = filename[:-5]
                    filepath = os.path.join(self.recordings_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            self.saved_recordings[name] = json.load(f)
                    except Exception as e:
                        self.log_to_console(f"Error loading recording {name}: {e}")
        except Exception as e:
            self.log_to_console(f"Error scanning recordings directory: {e}")

    def update_recording_dropdown(self):
        menu = self.recording_dropdown["menu"]
        menu.delete(0, "end")

        recordings = sorted(list(self.saved_recordings.keys()))
        if recordings:
            for name in recordings:
                menu.add_command(label=name, command=lambda n=name: self.recording_var.set(n))
            self.recording_var.set(recordings[0])
        else:
            menu.add_command(label="No recordings available")
            self.recording_var.set("")

    def play_recording(self):
        name = self.recording_var.get()
        if not name or name not in self.saved_recordings:
            self.log_to_console("No recording selected or recording not found.")
            return

        if self.is_playing:
            self.log_to_console("Already playing a recording.")
            return

        self.log_to_console(f"Playing recording: {name}")
        self.is_playing = True
        self.play_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.record_button.config(state=tk.DISABLED)

        self.playback_thread = threading.Thread(target=self.playback_thread_func, args=(name,))
        self.playback_thread.daemon = True
        self.playback_thread.start()

    def playback_thread_func(self, name):
        recording = self.saved_recordings.get(name, [])
        loop = self.loop_var.get()

        try:
            while self.is_playing:
                if recording:
                    last_time = 0
                    for cmd_data in recording:
                        if not self.is_playing:
                            break

                        cmd_time = cmd_data['time']
                        delay = cmd_time - last_time
                        if delay > 0:
                            time.sleep(delay)

                        cmd = cmd_data['command']
                        self.root.after(0, lambda c=cmd: self.send_command_from_playback(c))

                        last_time = cmd_time

                    if not loop:
                        break
                else:
                    break

            self.root.after(0, self.playback_completed)

        except Exception as e:
            self.root.after(0, lambda: self.log_to_console(f"Playback error: {e}"))
            self.root.after(0, self.playback_completed)

    def send_command_from_playback(self, cmd):
        if self.is_connected and self.bluetooth is not None:
            try:
                self.bluetooth.write(cmd.encode())
                self.log_to_console(f"Playback: {cmd}")
            except Exception as e:
                self.log_to_console(f"Error during playback: {e}")
                self.stop_playback()

    def playback_completed(self):
        self.is_playing = False
        self.play_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.record_button.config(state=tk.NORMAL)
        self.log_to_console("Playback completed.")

    def stop_playback(self):
        if self.is_playing:
            self.is_playing = False
            self.log_to_console("Stopping playback...")
            self.reset_position()

    def delete_recording(self):
        name = self.recording_var.get()
        if not name or name not in self.saved_recordings:
            self.log_to_console("No recording selected or recording not found.")
            return

        if name in self.saved_recordings:
            del self.saved_recordings[name]

        try:
            filepath = os.path.join(self.recordings_dir, f"{name}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
            self.log_to_console(f"Recording '{name}' deleted.")
            self.update_recording_dropdown()
        except Exception as e:
            self.log_to_console(f"Error deleting recording: {e}")

    def repeat_command(self, direction):
        if self.hold_active and direction == self.last_direction:
            self.send_command(direction)
            interval = int(self.hold_interval * (1.5 if hasattr(self, 'first_repeat') and not self.first_repeat else 1.0))
            self.first_repeat = False
            self.repeat_task = self.root.after(interval, lambda: self.repeat_command(direction))

    def schedule_repeat(self):
        if self.hold_active and self.last_direction:
            self.send_command(self.last_direction)

    def on_closing(self):
        if self.is_connected:
            self.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ControllerGUI(root)
    root.mainloop()