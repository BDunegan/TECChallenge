### Prompt
Assignment
A mission control center usually contains a telemetry and telecommand interface to monitor and command a spacecraft. The telecommand interface sends commands to the spacecraft, e.g., to perform a specific maneuver. The telemetry interface displays data points received from the spacecraft, such as information on sensors like temperature.
During mission operation, the operator selects telecommands that should be sent to the spacecraft via a web-based telecommand interface.  The issued telecommands are logged in a database and sent to the spacecraft on the next contact with a ground station.

Every telecommand has a current status. A telecommand usually goes through multiple stages:
  Ready (for Transmission)
  Transmitted
  Acknowledged
  Executed
  Failed (to Execute)
Depending on the mission, there may be more and/or different states.

Task
Your task is to develop two microservices:
A RESTful API for the mission operator's telecommand interface
A command sender that sends issued commands to the ground station interface

The API service should support the following:
Accept new telecommands
Cancel queued telecommands (only in "Ready" state)
Return status of a selected telecommand

The command sender service should do the following:
Pick up issued telecommands
Transmit telecommands after a random delay (up to 30 seconds)
Automatically advance telecommand status after a random delay until either "Executed" or "Failed"

Hints:
The focus of the task is software architecture, interaction of components, code quality, and how it is executed.
If you are unclear about some instructions, go ahead with your best guess and explain your reasoning in comments.
You can introduce logs/prints as needed to illustrate execution flow.
You do not have to provide the generated logfiles or binaries.

Constraints:
Microservices are written in Python
Select modern technologies (API framework, database, etc.), any pip package is allowed
Your code should come with instructions on how to execute it, it should run under Linux. 
Use any common build system if necessary.

### Prerequisites:
- Docker & Docker Compose installed
- Ports 5000, 8080 available
- docker-compose down -v
- docker system prune -f
- docker-compose up --build


### Response

┌─────────────┐    Database    ┌─────────────────┐    HTTP    ┌─────────────┐
│   GROUND    │◄──────────────►│ COMMAND-SENDER  │───────────►│ SPACECRAFT  │
│  (port 5000)│  (SQLite File) │  (background)   │ (commands) │ (port 8080) │
└─────────────┘                └─────────────────┘            └─────────────┘

Communication Flow:

Operator → Creates telecommand via ground web interface
Ground → Stores telecommand in shared database (Status: Ready)
Command-sender → Polls shared database, finds Ready commands
Command-sender → Updates status to Transmitted in database
Command-sender → Sends HTTP to spacecraft
Command-sender → Updates status progression in database
Ground → Reads updated status from database for web interface
NO direct HTTP between ground ↔ command-sender