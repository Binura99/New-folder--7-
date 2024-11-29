import streamlit as st
import requests
import time
import mysql.connector
from mysql.connector import Error
from datetime import datetime

# Your YouTube Data API Key
API_KEY = 'AIzaSyBSlNLP8OYcW5gADinil4ad7V0-dbhXJE4'

# Base URL for YouTube Data API
BASE_URL = "https://www.googleapis.com/youtube/v3"

# MySQL Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Update with your MySQL username
    'password': 'Pabyg@1999',  # Update with your MySQL password
    'database': 'youtube_live_chat'  # Database name
}


def create_database_and_table():
    """
    Create the database and table for storing live chat messages.
    """
    try:
        # Connect to MySQL server without selecting a database
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = connection.cursor()

        # Create the database if it doesn't exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS youtube_live_chat")
        cursor.execute("USE youtube_live_chat")

        # Create the table for live chat messages
        create_table_query = """
        CREATE TABLE IF NOT EXISTS live_chat_messages (
            id VARCHAR(255) PRIMARY KEY,
            author VARCHAR(255),
            message TEXT,
            timestamp DATETIME
        )
        """
        cursor.execute(create_table_query)
        connection.commit()
        print("Database and table created successfully.")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


def save_message_to_database(message_id, author, message, timestamp):
    """
    Save a live chat message to the database.
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        insert_query = """
        INSERT INTO live_chat_messages (id, author, message, timestamp)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE message=VALUES(message)
        """
        cursor.execute(insert_query, (message_id, author, message, timestamp))
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Error saving message to database: {err}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


def get_live_chat_id(video_id):
    """
    Fetch the live chat ID for a given live video ID.
    """
    url = f"{BASE_URL}/videos"
    params = {
        'part': 'liveStreamingDetails',
        'id': video_id,
        'key': API_KEY
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Extract the live chat ID
        if data.get('items'):
            live_stream_details = data['items'][0].get('liveStreamingDetails', {})
            live_chat_id = live_stream_details.get('activeLiveChatId')
            if live_chat_id:
                return live_chat_id
            print("No active live chat found for the given video.")
        else:
            print("Invalid video ID or no live stream found.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching live chat ID: {e}")
    return None


def is_valid_message(message):
    """
    Check if the message is valid (not a single word and not empty).
    """
    # Remove leading/trailing whitespaces
    message = message.strip()
    
    # Check if the message is empty or consists of only one word
    if not message or len(message.split()) == 1:
        return False
    return True


def fetch_live_chat_messages(live_chat_id):
    """
    Fetch real-time live chat messages for a given live chat ID and save them to the database.
    """
    url = f"{BASE_URL}/liveChat/messages"
    params = {
        'liveChatId': live_chat_id,
        'part': 'snippet,authorDetails',
        'key': API_KEY
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Store and display live chat messages
        messages = []
        for item in data.get('items', []):
            message_id = item['id']
            author = item['authorDetails']['displayName']
            message = item['snippet']['textMessageDetails']['messageText']
            timestamp = item['snippet']['publishedAt']

            # Check if the message is valid before saving it
            if is_valid_message(message):
                save_message_to_database(message_id, author, message, timestamp)
                messages.append((timestamp, author, message))

        return messages
    except requests.exceptions.RequestException as e:
        print(f"Error fetching live chat messages: {e}")
        return []


def track_live_chat(video_id, polling_interval=5):
    """
    Continuously fetch and display live chat messages for a live video and save them to the database.
    """
    live_chat_id = get_live_chat_id(video_id)
    if not live_chat_id:
        return []

    print(f"Tracking live chat for video ID: {video_id}")
    messages = []
    try:
        while True:
            new_messages = fetch_live_chat_messages(live_chat_id)
            messages.extend(new_messages)
            time.sleep(polling_interval)
            if new_messages:
                break  # Exit after fetching the first set of messages
    except KeyboardInterrupt:
        print("\nStopped tracking live chat.")
    return messages


# Streamlit UI Setup
def main():
    # Set page title and description
    st.title("YouTube Live Chat Tracker")
    st.write("Enter the YouTube video ID to track live chat messages.")

    # Input widget for the YouTube Video ID
    video_id = st.text_input("Enter Video ID", "jfKfPfyJRdk")  # Default ID for testing

    # Button to start the live chat tracking
    if st.button("Start Tracking"):
        if not video_id:
            st.error("Please enter a valid video ID!")
        else:
            st.write("Fetching live chat messages...")

            # Ensure the database and table are set up
            create_database_and_table()

            # Track live chat and display results
            messages = track_live_chat(video_id)
            if messages:
                st.write("Live Chat Messages:")
                for timestamp, author, message in messages:
                    st.markdown(f"**{author}**: {message}  *{timestamp}*")
            else:
                st.write("No messages found or the live stream may not be active.")

if __name__ == "__main__":
    main()
