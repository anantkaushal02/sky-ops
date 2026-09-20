from flight_ops.mcp import data
from flight_ops.mcp.server import (
    book_flight,
    cancel_booking,
    get_aircraft_maintenance_status,
    get_flight_status,
    get_weather_briefing,
    search_flights,
)


def test_search_flights_finds_known_route():
    results = search_flights("jfk", "lax")
    assert len(results) == 2
    assert {flight["flight_number"] for flight in results} == {"SK101", "SK202"}


def test_get_flight_status_unknown_flight_returns_error():
    result = get_flight_status("SK999")
    assert "error" in result


def test_get_weather_briefing_known_airport():
    briefing = get_weather_briefing("ord")
    assert briefing["conditions"] == "thunderstorms"


def test_get_aircraft_maintenance_status_flags_unairworthy_aircraft():
    status = get_aircraft_maintenance_status("N303SK")
    assert status["airworthy"] is False


def test_book_then_cancel_round_trip():
    data.BOOKINGS.clear()
    booking = book_flight("SK101", "Jane Doe", "jane@example.com")
    assert booking["status"] == "confirmed"
    confirmation_number = booking["confirmation_number"]

    cancellation = cancel_booking(confirmation_number)
    assert cancellation["status"] == "cancelled"
    assert data.BOOKINGS[confirmation_number]["status"] == "cancelled"
