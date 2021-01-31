from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from backend import get_db
from backend.app import app
from backend.database.config import Base
from backend.models.user import User


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Change the DB dependency injection of the app
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# This sets up and tear down the DB so we get a fresh db every test
@pytest.fixture
def db():
    # Setup
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    yield db

    # Teardown
    db.close()
    Base.metadata.drop_all(bind=engine)


def test_create_user(db):
    response = client.post("/users/", json={"name": "Hung", "email":"hung@mail.com"})
    user_json = response.json()
    user_in_db = db.query(User).filter(User.id == user_json["id"]).first()
    assert response.status_code == 200
    assert user_in_db.id == user_json["id"]
    

# -------- Transaction tests ---------------
def test_negative_transaction_affects_oldest(db):
    user = client.post("/users/", json={"name": "Hung", "email":"hung@mail.com"}).json()

    # A transaction_date is automatically generated at object creation, so no need to manually identify it here.
    new_transactions = [
        {
            "payer": "DANNON",
            "points": 300,
        },
        {
            "payer": "DANNON",
            "points": 200,
        },
        {
            "payer": "DANNON",
            "points": -300,
        }
    ]
    for t in new_transactions:
        client.post(f"/transactions/{user['id']}", json=t)
    
    transactions = client.get(f"/transactions/{user['id']}").json()
    
    assert transactions[0]["used_points"] == 300
    assert transactions[1]["used_points"] == 0

    balance = client.get(f"/users/{user['id']}/balance").json()

    assert balance == {"DANNON": 200}


def test_negative_transaction_affects_multiple(db):
    user = client.post("/users/", json={"name": "Hung", "email":"hung@mail.com"}).json()
    new_transactions = [
        {
            "payer": "DANNON",
            "points": 300,
        },
        {
            "payer": "DANNON",
            "points": 200,
        },
        {
            "payer": "DANNON",
            "points": -400,
        }
    ]
    for t in new_transactions:
        client.post(f"/transactions/{user['id']}", json=t)
    
    transactions = client.get(f"/transactions/{user['id']}").json()
    
    assert transactions[0]["used_points"] == 300
    assert transactions[1]["used_points"] == 100


def test_negative_transaction_only_affects_payer(db):
    user = client.post("/users/", json={"name": "Hung", "email":"hung@mail.com"}).json()
    new_transactions = [
        {
            "payer": "DANNON",
            "points": 300,
        },
        {
            "payer": "COORS",
            "points": 200,
        },
        {
            "payer": "DANNON",
            "points": -200,
        }
    ]
    for t in new_transactions:
        client.post(f"/transactions/{user['id']}", json=t)
    
    transactions = client.get(f"/transactions/{user['id']}").json()
    
    assert transactions[0]["used_points"] == 200
    assert transactions[1]["used_points"] == 0


def test_invalid_transaction_with_negative_points(db):
    user = client.post("/users/", json={"name": "Hung", "email":"hung@mail.com"}).json()
    new_transactions = [
        {
            "payer": "DANNON",
            "points": 300,
        },
        {
            "payer": "COORS",
            "points": 200,
        },
        {
            "payer": "DANNON",
            "points": -600,
        }
    ]
    for t in new_transactions:
        res = client.post(f"/transactions/{user['id']}", json=t)
    
    transactions = client.get(f"/transactions/{user['id']}").json()
    
    # The last POST call fails, and there are only 2 transactions in the db
    assert res.status_code == 400
    assert len(transactions) == 2


# -------- Deduction and balance tests ---------------
def test_example_deduct(db):
    user = client.post("/users/", json={"name": "Hung", "email":"hung@mail.com"}).json()
    new_transactions = [
        {
            "payer": "DANNON",
            "points": 300,
        },
        {
            "payer": "UNILEVER",
            "points": 200,
        },
        {
            "payer": "DANNON",
            "points": -200,
        },
        {
            "payer": "COORS",
            "points": 10000,
        },
        {
            "payer": "DANNON",
            "points": 1000,
        }
    ]
    for t in new_transactions:
        client.post(f"/transactions/{user['id']}", json=t)
    
    result = client.post(f"/users/{user['id']}/deduct", params={"deduct_amount": 5000}).json()

    assert result == {
        "DANNON": -100,
        "UNILEVER": -200,
        "COORS": -4700
    }

    balance = client.get(f"/users/{user['id']}/balance").json()

    assert balance == {
        "DANNON": 1000,
        "UNILEVER": 0,
        "COORS": 5300
    }


def test_example_deduct_different_amount(db):
    user = client.post("/users/", json={"name": "Hung", "email":"hung@mail.com"}).json()
    new_transactions = [
        {
            "payer": "DANNON",
            "points": 1000,
        },
        {
            "payer": "UNILEVER",
            "points": 500,
        },
        {
            "payer": "DANNON",
            "points": -700,
        },
        {
            "payer": "COORS",
            "points": 8000,
        },
        {
            "payer": "DANNON",
            "points": 2000,
        }
    ]
    for t in new_transactions:
        client.post(f"/transactions/{user['id']}", json=t)
    
    result = client.post(f"/users/{user['id']}/deduct", params={"deduct_amount": 6000}).json()

    assert result == {
        "DANNON": -300,
        "UNILEVER": -500,
        "COORS": -5200
    }

    balance = client.get(f"/users/{user['id']}/balance").json()

    assert balance == {
        "DANNON": 2000,
        "UNILEVER": 0,
        "COORS": 2800
    }


def test_adding_negative_transactions_similar_to_deduct(db):
    user = client.post("/users/", json={"name": "Hung", "email":"hung@mail.com"}).json()
    new_transactions = [
        {
            "payer": "DANNON",
            "points": 300,
        },
        {
            "payer": "UNILEVER",
            "points": 200,
        },
        {
            "payer": "DANNON",
            "points": -200,
        },
        {
            "payer": "COORS",
            "points": 10000,
        },
        {
            "payer": "DANNON",
            "points": 1000,
        },
        {
            "payer": "DANNON",
            "points": -100,
        },
        {
            "payer": "UNILEVER",
            "points": -200,
        },
        {
            "payer": "COORS",
            "points": -4700,
        }

    ]
    for t in new_transactions:
        client.post(f"/transactions/{user['id']}", json=t)
    
    balance = client.get(f"/users/{user['id']}/balance").json()

    assert balance == {
        "DANNON": 1000,
        "UNILEVER": 0,
        "COORS": 5300
    }


def test_deduct_oldest_first(db):
    user = client.post("/users/", json={"name": "Hung", "email":"hung@mail.com"}).json()
    new_transactions = [
        {
            "payer": "DANNON",
            "points": 300,
        },
        {
            "payer": "UNILEVER",
            "points": 300,
        },
        {
            "payer": "DANNON",
            "points": -200,
        },
    ]

    for t in new_transactions:
        client.post(f"/transactions/{user['id']}", json=t)

    client.post(f"/users/{user['id']}/deduct", params={"deduct_amount": 300}).json()

    transactions = client.get(f"/transactions/{user['id']}").json()

    assert transactions[0]["used_points"] == 300  # use Dannon's 100 first
    assert transactions[1]["used_points"] == 200  # use Unilever's 200 second
