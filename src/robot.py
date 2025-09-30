from src.movement import Movement
from src.voice import Voice


class Robot:
    def __init__(self):
        self.movement = Movement()
        self.voice = Voice()

    def start(self):
        self.voice.speak("Robot is starting.")
        # Additional initialization code can go here

    def move(self, direction):
        if direction == "forward":
            self.movement.move_forward()
        elif direction == "backward":
            self.movement.move_backward()
        elif direction == "left":
            self.movement.turn_left()
        elif direction == "right":
            self.movement.turn_right()
        else:
            self.voice.speak("Invalid direction.")

    def listen(self):
        command = self.voice.listen()
        self.process_command(command)

    def process_command(self, command):
        # Process the command received from voice
        if not command:
            return
        # normalize
        cmd = command.strip().lower()
        if cmd in ("move forward", "forward"):
            self.move("forward")
        elif cmd in ("move backward", "move back", "backward", "back"):
            self.move("backward")
        elif cmd in ("turn left", "left"):
            self.move("left")
        elif cmd in ("turn right", "right"):
            self.move("right")
        else:
            self.voice.speak("Command not recognized.")
