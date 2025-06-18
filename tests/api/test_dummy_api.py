import requests

def test_dummy_api_status():
    response = requests.get("https://jsonplaceholder.typicode.com/posts/1")
    assert response.status_code == 200
    assert "userId" in response.json()
