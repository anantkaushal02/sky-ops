"""MCP server exposing flight-operations tools over stdio.

Run standalone for manual testing:
    python -m flight_ops.mcp.server

In the real system this is spawned as a subprocess by MultiServerMCPClient
(see agents.py) and never invoked directly by a human.
"""

from mcp.server.fastmcp import FastMCP

from flight_ops.mcp import data

mcp = FastMCP(name="flight-ops")


@mcp.tool()
def search_flights(origin: str, destination: str) -> list[dict]:
    """Search available flights between two three-letter airport codes."""
    origin = origin.upper()
    destination = destination.upper()
    matches = []
    for flight in data.FLIGHTS:
        if flight["origin"] == origin and flight["destination"] == destination:
            matches.append(flight)
    return matches


@mcp.tool()
def get_flight_status(flight_number: str) -> dict:
    """Get the current status, route, and timing for one flight number."""
    flight = data.find_flight(flight_number.upper())
    if flight is None:
        return {"error": f"No flight found with number {flight_number}"}
    return flight


@mcp.tool()
def get_weather_briefing(airport_code: str) -> dict:
    """Get a weather briefing (conditions, visibility, wind, advisory) for an airport."""
    airport_code = airport_code.upper()
    briefing = data.WEATHER_BY_AIRPORT.get(airport_code)
    if briefing is None:
        return {"error": f"No weather data for airport {airport_code}"}
    return {"airport_code": airport_code, **briefing}


@mcp.tool()
def get_aircraft_maintenance_status(tail_number: str) -> dict:
    """Get airworthiness, open maintenance squawks, and last inspection date for a tail number."""
    tail_number = tail_number.upper()
    record = data.MAINTENANCE_BY_TAIL_NUMBER.get(tail_number)
    if record is None:
        return {"error": f"No maintenance record for tail number {tail_number}"}
    return {"tail_number": tail_number, **record}


@mcp.tool()
def book_flight(flight_number: str, passenger_name: str, passenger_email: str) -> dict:
    """Book a passenger onto a flight. This makes a real, sensitive change to booking records."""
    flight = data.find_flight(flight_number.upper())
    if flight is None:
        return {"error": f"No flight found with number {flight_number}"}
    confirmation_number = data.generate_confirmation_number()
    data.BOOKINGS[confirmation_number] = {
        "flight_number": flight["flight_number"],
        "passenger_name": passenger_name,
        "passenger_email": passenger_email,
        "status": "confirmed",
    }
    return {"confirmation_number": confirmation_number, "status": "confirmed"}


@mcp.tool()
def cancel_booking(confirmation_number: str) -> dict:
    """Cancel an existing booking by confirmation number. This makes a real, sensitive change."""
    booking = data.BOOKINGS.get(confirmation_number)
    if booking is None:
        return {"error": f"No booking found with confirmation number {confirmation_number}"}
    booking["status"] = "cancelled"
    return {"confirmation_number": confirmation_number, "status": "cancelled"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
