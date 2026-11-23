from app.models import User

def test_user_authentication(client, app):
    # Test valid login
    response = client.post('/auth/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back" in response.data

    # Logout before testing invalid credentials
    client.get('/auth/logout')

    # Test invalid password
    response = client.post('/auth/login', data={'username': 'admin', 'password': 'wrongpassword'}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data

def test_role_based_access(client, app):
    # Login as salesman
    client.post('/auth/login', data={'username': 'salesman', 'password': 'sales123'})
    
    # Attempt to access admin dashboard
    response = client.get('/dashboard/admin', follow_redirects=True)
    assert b"Access Denied" in response.data
