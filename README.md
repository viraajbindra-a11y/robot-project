# Robot Project

## Overview
This project is designed to control a robot using movement and voice functionalities. It serves as a foundation for building more complex robotic applications.

## Project Structure
```
robot-project
├── src
│   ├── robot.py          # Main entry point for the robot application
│   ├── movement.py       # Contains the Movement class for robot control
│   ├── voice.py          # Contains the Voice class for interaction
│   └── utils
│       └── __init__.py   # Initializes the utils package
├── tests
│   ├── movement_test.py   # Unit tests for the Movement class
│   └── voice_test.py      # Unit tests for the Voice class
├── scripts
│   └── sync_to_pi.sh      # Script to synchronize files to Raspberry Pi
├── .gitignore              # Specifies files to ignore in Git
├── requirements.txt        # Lists Python dependencies
└── README.md               # Documentation for the project
```

## Setup Instructions
1. Clone the repository from GitHub:
   ```
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```
   cd robot-project
   ```
3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage
- To run the robot application, execute the following command:
  ```
  python src/robot.py
  ```

## Testing
- To run the tests for the Movement class:
  ```
  python -m unittest tests/movement_test.py
  ```
- To run the tests for the Voice class:
  ```
  python -m unittest tests/voice_test.py
  ```

## Synchronization with Raspberry Pi
- Use the provided script `sync_to_pi.sh` to synchronize your project files with the Raspberry Pi. Make sure to configure the script with the correct paths and credentials.

## Contributing
Feel free to fork the repository and submit pull requests for any improvements or features you would like to add.