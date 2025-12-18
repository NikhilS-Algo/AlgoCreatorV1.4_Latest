import csv
from passlib.context import CryptContext
import os

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dictionary of users with username and plain password
USERS = {
    "user1": "user1@algo",
    "user2": "user2@algo",
    "user3": "user3@algo",
    "sahil": "sahil@algo"

}

# CSV file path
CSV_FILE_PATH = "./utils/user_data.csv"

# Function to hash a plain password
def get_password_hash(password):
    return pwd_context.hash(password)

# Function to generate the CSV with hashed passwords
def generate_csv_from_dict(file_path: str):
    headers = ["username", "hashed_password"]
    file_exists = os.path.isfile(file_path)

    with open(file_path, mode="a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)

        # Write header only if the file is new
        if not file_exists:
            writer.writeheader()

        # Iterate through USERS dictionary and write each user to CSV
        for username, password in USERS.items():
            hashed_password = get_password_hash(password)
            user_data = {"username": username, "hashed_password": hashed_password}
            writer.writerow(user_data)
            

    print(f"CSV file generated/updated at {file_path}")

# Run the function to create or update the CSV
generate_csv_from_dict(CSV_FILE_PATH)
