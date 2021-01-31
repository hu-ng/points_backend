# Fetch Rewards - Points

## Setup
- Have Python 3.8 installed
- Install the `virtualenv` package: `python3 -m pip install virtualenv`
- Clone the project with `git clone`
- Navigate to the root of the project with `cd points_backend`
- Create a virtual Python environment in the current folder with `python3 -m virtualenv .`
- Install all dependencies: `pip install -r requirements.txt`

## Run the project
- To start the dev server: `python backend/main.py`
- To run the tests: `pytest backend/testing`
- Thanks to FastAPI, documentation for the endpoints is provided by going to `0.0.0.0:8000/docs`
    - For each endpoint, inputs (query params, path params, and request body) and response formats are automatically provided.

## Thought process
Let's recap the primary constraint:

1. Deduct the oldest points first
2. Do not let any payer's balance go negative
3. Transaction records can be positive or negative

Because of (3), when we add a negative transaction, we can treat this as deducting the points from that specific payer, applying (1) and (2) in the process. When this is applied successfully to all payers and all transactions, what we have left is a timeline of non-negative points for all payers. Take the original example:

- add [DANNON, 300 points, 10/31 10AM] to user
- add [UNILEVER, 200 points, 10/31 11AM] to user
- add [DANNON, -200 points, 10/31 3PM] to user
- add [MILLER COORS, 10,000 points , 11/1 2PM] to user
- add [DANNON, 1000 points 11/2 2PM] to user

The third transaction is negative, so we deduct 200 points from DANNON, prioritizing the oldest points first. Because there's only one previous DANNON transaction, what we end up with is:
- add [DANNON, **100 points**, 10/31 10AM] to user
- add [UNILEVER, 200 points, 10/31 11AM] to user
- ~~add [DANNON, -200 points, 10/31 3PM] to user~~
- add [MILLER COORS, 10,000 points , 11/1 2PM] to user
- add [DANNON, 1000 points 11/2 2PM] to user

With this timeline of positive points, we can deduct points and track how many points are used for each payer.

In this project, I have decided to include two additional constraints:
- No negative transactions that deduct more than what the payer has at the time of transaction.
- Transactions must follow a chronological order - no adding past transactions.

While the first constraint is a derivative of constraint (2), the second constraint is added to simplify the project. Consider the sign of a new transaction if the transaction date is not the most recent.

If it's positive, then to adhere to constraint (1), we need to check following calls to `/deduct` to see if we need to "reimburse" any transactions that shouldn't have been deducted. A more relaxed solution that won't satisfy constraint (1) is just giving the users the points right now because the total balance won't change anyway.

If the sign is negative, then we might run into the case where the resulting balance at that timestamp is not enough to fulfill a call to `/deduct` that we already made.

The resolution to both of these cases requires more business context, so instead of writing extra checks to deal with these cases, I decided to nip them in the bud and not allow adding past transactions altogether.