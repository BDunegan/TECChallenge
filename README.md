### Prompt
A mission control center usually contains a telemetry and telecommand interface to monitor and command a spacecraft.
The telecommand interface sends commands to the spacecraft, e.g., to perform a specific maneuver.
The telemetry interface displays data points received from the spacecraft, such as information on sensors like temperature.
During mission operation, the operator selects telecommands that should be sent to the spacecraft via a web-based telecommand interface.  
The issued telecommands are logged in a database and sent to the spacecraft on the next contact with a ground station.

Every telecommand has a current status. A telecommand usually goes through multiple stages:
    Ready (for Transmission)
    Transmitted
    Acknowledged
    Executed
    Failed (to Execute)


RESTful API microservice (telecommand interface)
A command sender that sends issued commands to the ground station interface

### Response
Microservices Design Pattern

Service 1: RESTful API Service (Port 5000)
Service 2: Command Sender Service (Port 5001)
Shared Database: PostgreSQL with shared models
Communication: Database-mediated async communication
Deployment: Docker containers with docker-compose orchestration


/telecommands:
  POST:    # Accept new telecommands
    summary: Create new telecommand
    request_body: TelecommandCreateSchema
    responses:
      201: Created telecommand
      400: Validation error
  GET:     # Additional: List telecommands
    summary: List all telecommands
    parameters: [status, priority, limit, offset]
    responses:
      200: List of telecommands

/telecommands/{id}:
  GET:     # Return status of selected telecommand
    summary: Get telecommand details
    responses:
      200: Telecommand details
      404: Telecommand not found

/telecommands/{id}/cancel:
  DELETE:  # Cancel queued telecommands
    summary: Cancel telecommand (Ready state only)
    responses:
      200: Successfully cancelled
      400: Cannot cancel (wrong state)
      404: Telecommand not found

/telecommands/{id}/status:
  GET:     # Additional: Status-only endpoint
    summary: Get telecommand status only
    responses:
      200: Status information

/health:
  GET:     # Operational: Health check
    summary: Service health status
    responses:
      200: Service healthy