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
        if command in ["move forward", "move back", "turn left", "turn right"]:
            self.move(command.split()[-1])
        else:
            self.voice.speak("Command not recognized.")