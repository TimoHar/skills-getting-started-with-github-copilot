"""
Test suite for Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    global activities
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    })


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirects_to_static_index(self, client):
        """Test that root path redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_all_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
        # Verify structure of an activity
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)

    def test_activities_have_correct_participants(self, client):
        """Test that activities contain the correct participants"""
        response = client.get("/activities")
        data = response.json()
        
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]
        assert "emma@mergington.edu" in data["Programming Class"]["participants"]


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_new_participant(self, client):
        """Test signing up a new participant"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" in activities_data["Chess Club"]["participants"]

    def test_signup_duplicate_participant(self, client):
        """Test signing up a participant who is already registered"""
        # First signup
        client.post("/activities/Chess%20Club/signup?email=test@mergington.edu")
        
        # Duplicate signup
        response = client.post(
            "/activities/Chess%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_nonexistent_activity(self, client):
        """Test signing up for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_when_activity_is_full(self, client):
        """Test signing up when activity has reached max participants"""
        # Create an activity at max capacity
        activities["Small Club"] = {
            "description": "A small club",
            "schedule": "Mondays",
            "max_participants": 2,
            "participants": ["student1@mergington.edu", "student2@mergington.edu"]
        }
        
        response = client.post(
            "/activities/Small%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 400
        assert "full" in response.json()["detail"].lower()


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_existing_participant(self, client):
        """Test unregistering a participant who is registered"""
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "michael@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]

    def test_unregister_nonexistent_participant(self, client):
        """Test unregistering a participant who is not registered"""
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregistering from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent%20Club/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_allows_signup_again(self, client):
        """Test that after unregistering, a participant can sign up again"""
        # Unregister
        client.delete(
            "/activities/Chess%20Club/unregister?email=michael@mergington.edu"
        )
        
        # Sign up again
        response = client.post(
            "/activities/Chess%20Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 200


class TestIntegrationScenarios:
    """Integration tests for common user workflows"""

    def test_full_signup_and_unregister_workflow(self, client):
        """Test complete workflow: check activities, signup, verify, unregister, verify"""
        # Check initial state
        activities_response = client.get("/activities")
        initial_count = len(activities_response.json()["Programming Class"]["participants"])
        
        # Sign up
        signup_response = client.post(
            "/activities/Programming%20Class/signup?email=newstudent@mergington.edu"
        )
        assert signup_response.status_code == 200
        
        # Verify signup
        activities_response = client.get("/activities")
        after_signup_count = len(activities_response.json()["Programming Class"]["participants"])
        assert after_signup_count == initial_count + 1
        assert "newstudent@mergington.edu" in activities_response.json()["Programming Class"]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            "/activities/Programming%20Class/unregister?email=newstudent@mergington.edu"
        )
        assert unregister_response.status_code == 200
        
        # Verify unregistration
        activities_response = client.get("/activities")
        final_count = len(activities_response.json()["Programming Class"]["participants"])
        assert final_count == initial_count
        assert "newstudent@mergington.edu" not in activities_response.json()["Programming Class"]["participants"]

    def test_multiple_participants_signup_to_same_activity(self, client):
        """Test multiple different participants signing up to the same activity"""
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(f"/activities/Gym%20Class/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all were added
        activities_response = client.get("/activities")
        participants = activities_response.json()["Gym Class"]["participants"]
        for email in emails:
            assert email in participants
