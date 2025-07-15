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

Task:
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

---

### Prerequisites:
- Docker & Docker Compose installed
- Ports 5000, 8080 available
- stable internet connection avalible

### Run instrtuctions
- Run 'docker-compose down -v' if conflicting containers exist
- Run 'docker-compose up --build' in the root of the directory
- Access 'http://127.0.0.1:5000' for the web interface
- Submit a Command in the field 'Send New Command'
- Watch the console to see the pipeline in action!

---

### Communication Flow:

Operator -> Creates telecommand via ground web interface
Ground -> Stores telecommand in shared database (Status: Ready)
Command-sender -> Polls shared database, finds Ready commands
Command-sender -> Updates status to Transmitted in database
Command-sender -> Sends HTTP to spacecraft
Spacecraft -> Sends HTTP response to trigger achnowledged
Command-sender -> Updates status progression in database
Ground -> Reads live updated status from database for web interface

NOTE: All communication is HTTP or database-mediated

┌─────────────┐    Database    ┌─────────────────┐    HTTP    ┌─────────────┐
│   GROUND    │◄──────────────►│ COMMAND-SENDER  │───────────►│ SPACECRAFT  │
│  (port 5000)│  (SQLite File) │  (background)   │ (commands) │ (port 8080) │
└─────────────┘                └─────────────────┘            └─────────────┘

### Justifications
All six of the Telecommand states (Ready, Transmitted, Acknowledged, Executed, Failed, Cancelled) are hard coded into a models.py file as a class object. This models.py is redundantly placed in each microservice file. This redundancy I felt was better than abstracting it into a shared python package (which was a considered alternative) because of its use in spaceflight and the separation of the services caused by this use case (spacecraft tend to be pretty far away). It did not seem appropriate or realistic to assume ANY shared communication between any of the microservices other than in the cases of database-mediated communication between the ground_station microservice and the command_sender and the HTTP communication between command_sender and spacecraft. While I recognize this is a bit at conflict with using any imports, I attempted to stay in what I felt was the spirit of the project and all imports are packaged into the Docker image build.

The requirement for the RESTful API (standard use of HTTP methods) mission operator telecommand interface is fulfilled by the ground_station microservice. 
	-New Telecommand: A POST endpoint is provided in api/telecommands under the create_telecommand() function, which expects a JSON payload containing the command_name field (captured from the user in the web interface in this project). This fulfills the acceptance of new telecommands requirement.
	-Cancel Telecommand: A PUT endpoint is provided at /api/telecommands/<command_id>/cancel under the cancel_telecommand(command_id) function. Here we pass the uuid4 primary key used in the shared TECChallenege SQL database as a parameter to be used as a dynamic path to cancel/delete a specific telecommand. This is accessible through the web interface as well and follows RESTful API standards by using HTTP communication for the operation. Notably we use PUT here instead of DELETE to better signal that this is a modification to an existing record rather than the removal of a record from the database.
	-Status of Telecommands: A GET endpoint is provided in /api/telecommands/<command_id> to retrieve the current stored status of any individual telecommand record. We again use a dynamic path with the uuid4 primary key to identify which record it is we want the status of.

The requirements for the command sender microservice are met as follows:
	-Pick up new READY telecommands: New telecommands are discovered by the command_sender microservice via a database-mediated communication protocol. The command_sender class connects to the shared TECChallenge sqlite database and makes a query every 5 seconds (or 1 second if left to default fallback). This is run by the main loop of the object oriented CommandSender class which is the primary reason for this OOP design.
	-Random Delay Transmission: I built the random delay into each stage of the status pipeline. Within the CommandSender class (in the process_command fuunction) we establish a variable delay which selects a uniformly random integer between 3 and 8 to serve as the delay in seconds. This is used to simulate realworld delay in transmission over long distances and highlights the functionality of our status pipeline. I selected 3 to 8 seconds simi at random because it is enough to highlight the consequence of the delay but not enough to cause practical testing issues (it got really annoying waiting up to 3min to see if we get Executed or Failed).
	-Automatic advancement: Initially, each record has a READY status when stored in the database by the ground_station microservice. From here, we transition to the TRANSMITTED status after it is sent by command_sender. We then go to ACKNOWLEDGED only when we receive a 200 (successful) HTTP response from the spacecraft microservice. If any exception occurs, the Telecommand is set to a failed status at this point. We then have a hardcoded (for demo purposes) random failure 15% of the time. The other 85% of the time, we continue to the executed stage. Each record through this operation ALWAYS is either FAILED or EXECUTED in normal runtime or CANCELLED with user input.

### TECH STACK
	Flask
	SQLite
	Docker

  I chose this tech stack for a variety of reasons. Keeping the requirements aligned with those listed in the prompt, I began by selecting a Python framework in which to opperate. Due to my use of it in university, Flask was a logical choice. I am familiar with the Flask framework and decided it allowed me to leverage the full Python toolkit compared to a more boilerplate option like FastAPI. Although I knew the Flask implementation would come to be slightly larger in terms of storage, I minimize this downside by using the python:3.11-slim image as a base. I then decided on a backend storage system for the telecommands. I felt that a heavily structured relational database like SQL or SQLite in my case provided the rigid schema demanded by the requirements. I did briefly consider a non-relational database for the project, but quickly decided the query functionality was too important to sacrifice compared to the minor advantage of flexibility provided by a non-relational database. Finally, after a basic design of the project was established, I transitioned to using Docker to manage the microservices. Docker is a modern container management system which allowed me to create very lightweight and scalable microservices. Additionally, since Docker utilizes a Linux kernel, the TECChallenge nessisarily is able to run on a Linux OS. This was a very large advantage since I program on a Windows native machine and interactions between Linux and Windows can quickly become very complex and very bloated.

### File Structure:
	command-sender/
		Dockerfile
		requirements.txt
		shared/
			init.py
			models.py
		command_sender.py
	ground/
		Dockerfile
		requirements.txt
		shared/
			init.py
			models.py
		ground_station.py
	spacecraft/
		Dockerfile
		requirements.txt
		shared/
			init.py
			models.py
		spacecraft.py

### URL Routes
	GROUND
		/
        The root entrance for the web app hosted on http://127.0.0.1:5000
		/health
        A route to check the health of the microservice.
		/api/telecommands (GET)
        Lists all current telecommands in the SQLite shared TECChallenge.db
		/api/telecommands (POST)
        Accepts new Telecommands via HTTP POST.
		/api/telecommands/<command_id>
        Returns the status of a specific telecommand using a dynamic route.
		/api/telecommands/<command_id>/cancel (PUT)
        Updates a specific telecommand (again via dynamic route) to the CANCELLED status.
	SENDER
		CommandSender
			wait_for_database(self)
          Used to ensure the TECCHallenge.db is defined before attempting to access it. Only used on initial startup
			pick_up_ready_commands(self)
          Used to find new READY telecommands in TECChallenge.db every POLL_INTERVAL seconds
			update_command_status(self, command_id, new_status, error_message=None)
          Updates the status of a specific telecommand (using the uuid4 passed as a parameter)
			process_command(self, command_id)
          This function is the main driver for telecommand status advancement and catches the SPACECRAFT HTTP response. (we also simulate 15% failure here)
			run(self)
	SPACECRAFT
		/
		/health
		/commands