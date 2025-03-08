import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import sqlite3
import time
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Path to database file
DB_PATH = os.path.join(os.path.dirname(__file__), 'net.db')

# Ensure the database directory exists
db_dir = os.path.dirname(DB_PATH)
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

API_TOKEN = '7537659042:AAG8ZdvWIt1EkYEfoy2q7vZHBFm89NtnFrE'  # Replace with your actual bot token
bot = telebot.TeleBot(API_TOKEN)

# In-memory user progress cache
user_progress = {}
user_names = {}

# Database initialization
def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS progress (
                                user_id INTEGER PRIMARY KEY,
                                question_index INTEGER,
                                completed_questions TEXT,
                                correct_answers INTEGER,
                                question_sequence TEXT,
                                selected_answers TEXT,
                                username TEXT)''')
            conn.commit()
            logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Error initializing database: {e}")
    except Exception as e:
        logging.error(f"Unexpected error during database initialization: {e}")

# Save progress to the database
def save_progress(user_id, username, progress):
    """
    Save the user's progress to the database.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            completed_questions = ','.join(map(str, progress['completed_questions']))
            question_sequence = ','.join(map(str, progress['question_sequence']))
            selected_answers = ','.join([f"{k}:{v}" for k, v in progress['selected_answers'].items()])
            
            cursor.execute('''INSERT OR REPLACE INTO progress 
                              (user_id, username, question_index, completed_questions, correct_answers, question_sequence, selected_answers)
                              VALUES (?, ?, ?, ?, ?, ?, ?)''',
                           (user_id, username, progress['question_index'], completed_questions, progress['correct_answers'], question_sequence, selected_answers))
            conn.commit()
            logging.info(f"Progress saved for user {user_id}.")
    except sqlite3.Error as e:
        logging.error(f"Database error while saving progress for user {user_id}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error while saving progress for user {user_id}: {e}")
        
# Load user progress from database
def load_progress(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM progress WHERE user_id = ?', (user_id,))
        data = cursor.fetchone()

    if data:
        completed_questions = set(map(int, data[2].split(','))) if data[2] else set()
        question_sequence = list(map(int, data[4].split(','))) if data[4] else []
        
        # Fix: Correctly parse the selected_answers column
        selected_answers = {}
        if data[5]:  # Check if selected_answers is not empty
            for pair in data[5].split(','):
                if ':' in pair:
                    key, value = pair.split(':', 1)  # Split on the first occurrence of ':'
                    selected_answers[key] = value

        return {
            'question_index': data[1],
            'completed_questions': completed_questions,
            'correct_answers': data[3],
            'question_sequence': question_sequence,
            'selected_answers': selected_answers
        }
    return None

@bot.message_handler(commands=['start', 'resume'])
def ask_username(message):
    user_id = message.chat.id

    try:
        # Load user progress from the database
        progress = load_progress(user_id)
        if progress:
            user_progress[user_id] = progress  # Load progress into memory

        # Check if the user already has a username in the database
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM progress WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()

        if result and result[0]:  # If the user already has a username
            user_names[user_id] = result[0]  # Load the username into memory
            show_main_menu(user_id)  # Skip the username prompt and show the main menu
        else:
            # Send the image with the welcome message as the caption
            image_url = "https://i.postimg.cc/PfVRwmqR/image.png"
            caption = "<b>Welcome to NETWORK+ N10-009 PRACTICE Quiz</b>  \n\nPlease enter <b>Username:</b>"
            bot.send_photo(user_id, image_url, caption=caption, parse_mode='HTML')
            bot.register_next_step_handler(message, store_username)  # Ask for a new username
    except sqlite3.Error as e:
        logging.error(f"Database error while fetching username for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while fetching your data. Please try again.")
    except Exception as e:
        logging.error(f"Unexpected error in ask_username for user {user_id}: {e}")
        bot.send_message(user_id, "An unexpected error occurred. Please try again.")

def load_progress(user_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM progress WHERE user_id = ?', (user_id,))
            data = cursor.fetchone()

        if data:
            completed_questions = set(map(int, data[2].split(','))) if data[2] else set()
            question_sequence = list(map(int, data[4].split(','))) if data[4] else []
            
            # Fix: Correctly parse the selected_answers column
            selected_answers = {}
            if data[5]:  # Check if selected_answers is not empty
                for pair in data[5].split(','):
                    if ':' in pair:
                        key, value = pair.split(':', 1)  # Split on the first occurrence of ':'
                        selected_answers[key] = value

            logging.info(f"Loaded progress for user {user_id}: {data}")
            return {
                'question_index': data[1],
                'completed_questions': completed_questions,
                'correct_answers': data[3],
                'question_sequence': question_sequence,
                'selected_answers': selected_answers
            }
        else:
            logging.info(f"No progress found for user {user_id}.")
            return None
    except sqlite3.Error as e:
        logging.error(f"Database error while loading progress for user {user_id}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error while loading progress for user {user_id}: {e}")
        return None

# Function to create the users table if it doesn't exist
def create_users_table():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT
                )
            """)
            conn.commit()
    except Exception as e:
        print(f"Error creating users table: {e}")

# Call the function to ensure the table exists when the bot starts
create_users_table()

def store_username(message):
    user_id = message.chat.id
    username = message.text.strip()

    try:
        # Validation: Check if the username starts with "/"
        if username.startswith('/'):
            bot.send_message(user_id, "Username cannot start with '/'. Please enter a valid username.")
            bot.register_next_step_handler(message, store_username)  # Ask for the username again
            return

        # Validation: Check if the username contains emojis
        emoji_pattern = re.compile("[" 
                                   u"\U0001F600-\U0001F64F"  # emoticons
                                   u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                   u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                   u"\U0001F700-\U0001F77F"  # alchemical symbols
                                   u"\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
                                   u"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
                                   u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
                                   u"\U0001FA00-\U0001FA6F"  # Chess Symbols
                                   u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
                                   u"\U00002702-\U000027B0"  # Dingbats
                                   u"\U000024C2-\U0001F251"
                                   "]+", flags=re.UNICODE)

        if emoji_pattern.search(username):
            bot.send_message(user_id, "Username cannot contain emojis. Please enter a valid username.")
            bot.register_next_step_handler(message, store_username)  # Ask for the username again
            return

        # Validation: Check if the username contains any numbers or non-letter characters
        if not username.isalpha():  # Check if the username contains only alphabetic characters (A-Z, a-z)
            bot.send_message(user_id, "Username can only contain letters (A-Z). Please enter a valid username.")
            bot.register_next_step_handler(message, store_username)  # Ask for the username again
            return

        # If all validations pass, store the username in your database or proceed with the next step
        # For example:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
            conn.commit()


        # Save the username to the database
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO progress (user_id, username, question_index, completed_questions, correct_answers, question_sequence, selected_answers)
                VALUES (?, ?, COALESCE((SELECT question_index FROM progress WHERE user_id = ?), 0),
                        COALESCE((SELECT completed_questions FROM progress WHERE user_id = ?), ''),
                        COALESCE((SELECT correct_answers FROM progress WHERE user_id = ?), 0),
                        COALESCE((SELECT question_sequence FROM progress WHERE user_id = ?), ''),
                        COALESCE((SELECT selected_answers FROM progress WHERE user_id = ?), ''))
            """, (user_id, username, user_id, user_id, user_id, user_id, user_id))
            conn.commit()
        bot.send_message(user_id, f"<b>Username</b>: {username}\n<code>Successfully stored!</code>✅\n\n", parse_mode="HTML")
        user_names[user_id] = username  # Save the username in memory
        time.sleep (2)
        show_main_menu(user_id)  # Show the main menu
    except sqlite3.Error as e:
        logging.error(f"Database error while storing username for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while saving your username. Please try again.")
    except Exception as e:
        logging.error(f"Unexpected error in store_username for user {user_id}: {e}")
        bot.send_message(user_id, "An unexpected error occurred. Please try again.")

# Other functions (e.g., show_main_menu, start_quiz_callback, etc.) go below
def show_main_menu(user_id):
    try:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("START NETWORK+ QUIZ️📶", callback_data="start_quiz"),
            InlineKeyboardButton("VIEW HIGHSCORES🔥", callback_data="view_scores")
        )
        start_message = (
            "<b>Welcome to the Network+ N10-009 Quiz Bot!</b> 🎉\n\n"
           
            "Test your knowledge, challenge yourself.\n\n"
            "<b>Are you ready to prove your networking skills? Let's get started!</b> "
        )
        bot.send_message(user_id, start_message, reply_markup=markup, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Error in show_main_menu for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while displaying the main menu. Please try again.")

@bot.callback_query_handler(func=lambda call: call.data == "start_quiz")
def start_quiz_callback(call):
    user_id = call.message.chat.id
    try:
        bot.answer_callback_query(call.id, "Starting quiz...")

        if user_id not in user_progress:
            user_progress[user_id] = {
                'question_index': 0,
                'completed_questions': set(),
                'correct_answers': 0,
                'question_sequence': random.sample(range(len(questions)), len(questions)),
                'selected_answers': {}
            }
            # Pass both user_id and progress to save_progress
            save_progress(user_id, user_names.get(user_id, "Unknown"), user_progress[user_id])

        send_next_question(call.message)
    except Exception as e:
        logging.error(f"Error in start_quiz_callback for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while starting the quiz. Please try again.")


def delete_all_previous_messages(user_id, current_message_id, leaderboard_message_id=None):
    """
    Delete all previous messages in the chat up to the current message.
    Optionally delete the leaderboard message if provided.
    """
    try:
        # Delete only the last 10 messages to avoid delays
        for i in range(current_message_id - 1, max(0, current_message_id - 15), -1):
            try:
                bot.delete_message(user_id, i)
            except telebot.apihelper.ApiTelegramException as e:
                if "message to delete not found" in str(e):
                    # Ignore if the message is not found
                    continue
                else:
                    # Raise other errors
                    logging.error(f"Error deleting message {i} for user {user_id}: {e}")
                    raise e

        # If a leaderboard message ID is provided, delete that message as well
        if leaderboard_message_id:
            try:
                bot.delete_message(user_id, leaderboard_message_id)
            except telebot.apihelper.ApiTelegramException as e:
                if "message to delete not found" in str(e):
                    # Ignore if the message is not found
                    pass
                else:
                    logging.error(f"Error deleting leaderboard message for user {user_id}: {e}")
                    raise e
    except Exception as e:
        logging.error(f"Error in delete_all_previous_messages for user {user_id}: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "view_scores")
def view_scores_callback(call):
    user_id = call.message.chat.id  # Fixed typo: `rat.id` -> `chat.id`
    try:
        bot.answer_callback_query(call.id, "Fetching top scores...")

        # Fetch total number of questions (Replace this with dynamic fetching if possible)
        total_questions = 975  # Set this to match the actual total questions count

        # Fetch top scores from the database, excluding users without a username
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, correct_answers 
                FROM progress 
                WHERE username IS NOT NULL AND username != ''
                ORDER BY correct_answers DESC 
                LIMIT 10
            """)
            scores = cursor.fetchall()

        # Format the leaderboard
        leaderboard = "<code>[CompTIA N+ N10 009]</code>\n<blockquote>🏆 <b>[LEADERBOARD]</b> 🏆</blockquote>\n\n"
        for rank, (username, correct) in enumerate(scores, 1):
            percentage_correct = (correct / total_questions) * 100 if total_questions else 0
            if rank == 1:
                leaderboard += f"🥇 <b>{username}: [ {percentage_correct:.0f}% ]</b>\n"
            elif rank == 2:
                leaderboard += f"🥈 <b>{username}: [ {percentage_correct:.0f}% ]</b>\n"
            elif rank == 3:
                leaderboard += f"🥉 <b>{username}: [ {percentage_correct:.0f}% ]</b>\n\n"
            else:
                leaderboard += f"<code>{rank}. {username}: {correct} [{percentage_correct:.0f}%]</code>\n"

        bot.send_message(user_id, leaderboard, parse_mode="HTML")
    except Exception as e:
        bot.send_message(user_id, f"Error retrieving leaderboard: {str(e)}")

        # Send the image along with the leaderboard as the caption
        image_url = "https://i.postimg.cc/gJ9ZrPdj/123222.png"
        bot.send_photo(user_id, image_url, caption=leaderboard, parse_mode="HTML")

        # Add a "Resume Quiz" button below the leaderboard
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("Resume Quiz", callback_data="resume_quiz"))

        # Send the button after the image
        bot.send_message(user_id, "Click to resume your quiz:", reply_markup=markup)

    except Exception as e:
        bot.send_message(user_id, f"Error retrieving leaderboard: {str(e)}")




        # Save the leaderboard message id for later deletion
        call.message.reply_markup = None  # Clear the "view_scores" button
    except sqlite3.Error as e:
        logging.error(f"Database error in view_scores_callback for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while fetching the leaderboard. Please try again.")
    except Exception as e:
        logging.error(f"Unexpected error in view_scores_callback for user {user_id}: {e}")
        bot.send_message(user_id, "An unexpected error occurred. Please try again.")

@bot.callback_query_handler(func=lambda call: call.data == "resume_quiz")
def resume_quiz_callback(call):
    user_id = call.message.chat.id
    try:
        bot.answer_callback_query(call.id, "Resuming quiz...")

        # Delete leaderboard and previous messages
        delete_all_previous_messages(user_id, call.message.message_id, leaderboard_message_id=call.message.message_id)

        # Check if the user's progress exists
        if user_id not in user_progress:
            # Initialize progress if it doesn't exist
            user_progress[user_id] = {
                'question_index': 0,
                'completed_questions': set(),
                'correct_answers': 0,
                'question_sequence': random.sample(range(len(questions)), len(questions)),
                'selected_answers': {}
            }
            # Save the progress to the database
            save_progress(user_id, user_names.get(user_id, "Unknown"), user_progress[user_id])

        # Send the next question
        send_next_question(call.message)
    except Exception as e:
        logging.error(f"Error in resume_quiz_callback for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while resuming the quiz. Please try again.")

@bot.message_handler(commands=['score'])
def score_command_handler(message):
    user_id = message.chat.id
    try:
        bot.send_chat_action(user_id, 'typing')  # Show "typing" action

        # Fetch total number of questions (Replace this with dynamic fetching if possible)
        total_questions = 975  # Set this to match the actual total questions count

        # Fetch top scores from the database, excluding users without a username
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, correct_answers 
                FROM progress 
                WHERE username IS NOT NULL AND username != ''
                ORDER BY correct_answers DESC 
                LIMIT 10
            """)
            scores = cursor.fetchall()

        # Format the leaderboard
        leaderboard = "<code>[CompTIA N+ N10 009]</code>\n<blockquote>🏆 <b>[LEADERBOARD]</b> 🏆</blockquote>\n\n"
        for rank, (username, correct) in enumerate(scores, 1):
            percentage_correct = (correct / total_questions) * 100 if total_questions else 0
            if rank == 1:
                leaderboard += f"🥇 <b>{username}: [ {percentage_correct:.0f}% ]</b>\n"
            elif rank == 2:
                leaderboard += f"🥈 <b>{username}: [ {percentage_correct:.0f}% ]</b>\n"
            elif rank == 3:
                leaderboard += f"🥉 <b>{username}: [ {percentage_correct:.0f}% ]</b>\n\n"
            else:
                leaderboard += f"<code>{rank}. {username}: {correct} [{percentage_correct:.0f}%]</code>\n"

        bot.send_message(user_id, leaderboard, parse_mode="HTML")
    except Exception as e:
        bot.send_message(user_id, f"Error retrieving leaderboard: {str(e)}")


         

        # Add a "Resume Quiz" button below the leaderboard
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("Resume Quiz", callback_data="resume_quiz"))

        # Send the leaderboard message
        bot.send_message(user_id, leaderboard, parse_mode="HTML", reply_markup=markup)
    except sqlite3.Error as e:
        logging.error(f"Database error in score_command_handler for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while fetching the leaderboard. Please try again.")
    except Exception as e:
        logging.error(f"Unexpected error in score_command_handler for user {user_id}: {e}")
        bot.send_message(user_id, "An unexpected error occurred. Please try again.")
    
# Define the quiz questions
questions = [
    
{
    "question": "Which of the following is a characteristic of Software-Defined Networking (SDN)?",
    "options": [
        "A. Network control is distributed across all devices",
        "B. Network intelligence is centralized in the controller",
        "C. Devices perform all routing and switching decisions",
        "D. The network relies on physical infrastructure for flexibility"
    ],
    "answer": "B. Network intelligence is centralized in the controller"
},
{
    "question": "In SD-WAN, which of the following allows a network administrator to automate network deployment across multiple branch locations?",
    "options": [
        "A. Centralized policy management",
        "B. Zero-touch provisioning",
        "C. Hybrid routing",
        "D. Transport agnosticism"
    ],
    "answer": "B. Zero-touch provisioning"
},
{
    "question": "What is the main advantage of using SD-WAN over traditional WAN solutions?",
    "options": [
        "A. Increased bandwidth",
        "B. Application-aware routing for optimizing performance",
        "C. Requires no infrastructure management",
        "D. It only uses MPLS for connectivity"
    ],
    "answer": "B. Application-aware routing for optimizing performance"
},
{
    "question": "How does Zero Trust Architecture enhance security?",
    "options": [
        "A. By trusting all internal network traffic",
        "B. By requiring authentication at every layer of the network",
        "C. By only allowing authorized users to connect to the network",
        "D. By creating a demilitarized zone between the LAN and WAN"
    ],
    "answer": "B. By requiring authentication at every layer of the network"
},
{
    "question": "Which of the following encapsulation methods is used by VXLAN to provide Layer 2 connectivity over a Layer 3 network?",
    "options": [
        "A. MPLS",
        "B. GRE tunnels",
        "C. VXLAN headers",
        "D. IPsec tunnels"
    ],
    "answer": "C. VXLAN headers"
},
{
    "question": "What does SDN offer in terms of network automation?",
    "options": [
        "A. It eliminates the need for manual network configuration",
        "B. It automates physical layer management only",
        "C. It allows automated device firmware updates",
        "D. It does not allow automation of network tasks"
    ],
    "answer": "A. It eliminates the need for manual network configuration"
},
{
    "question": "Which of the following is an advantage of SD-WAN in terms of traffic management?",
    "options": [
        "A. It allows automatic failover between different transport links",
        "B. It reduces the need for security policies",
        "C. It optimizes traffic based on physical location",
        "D. It restricts routing based on the application layer"
    ],
    "answer": "A. It allows automatic failover between different transport links"
},
{
    "question": "In Zero Trust Architecture, what is the primary focus of the 'least privilege' access principle?",
    "options": [
        "A. Users should have full access to all internal resources",
        "B. Devices should be trusted based on their location within the network",
        "C. Users and devices should only have access to the resources they need to perform their roles",
        "D. Resources are open to all authenticated users"
    ],
    "answer": "C. Users and devices should only have access to the resources they need to perform their roles"
},
{
    "question": "How does SD-WAN improve performance for branch office users?",
    "options": [
        "A. By increasing the bandwidth between branch offices",
        "B. By optimizing routing based on application needs and network conditions",
        "C. By using MPLS exclusively for all traffic",
        "D. By eliminating the need for centralized management"
    ],
    "answer": "B. By optimizing routing based on application needs and network conditions"
},
{
    "question": "In SDN, which plane is responsible for forwarding data between devices?",
    "options": [
        "A. Application plane",
        "B. Data plane",
        "C. Control plane",
        "D. Management plane"
    ],
    "answer": "B. Data plane"
},
{
    "question": "What is the function of VXLAN in terms of data center architecture?",
    "options": [
        "A. It encapsulates Layer 3 traffic over Layer 2 networks",
        "B. It provides scalability for large-scale Layer 2 networks over Layer 3 infrastructure",
        "C. It encrypts traffic between data centers",
        "D. It replaces the need for traditional Layer 3 routing"
    ],
    "answer": "B. It provides scalability for large-scale Layer 2 networks over Layer 3 infrastructure"
},
{
    "question": "Which of the following is a common application for SD-WAN in a distributed network?",
    "options": [
        "A. Connecting only on-premise devices",
        "B. Optimizing network traffic for cloud applications",
        "C. Using only MPLS for secure traffic",
        "D. Disabling dynamic routing protocols"
    ],
    "answer": "B. Optimizing network traffic for cloud applications"
},
{
    "question": "What does Zero Trust Architecture assume about internal network traffic?",
    "options": [
        "A. It is inherently safe and does not need additional validation",
        "B. It should be treated as potentially compromised and must be verified",
        "C. It should always be encrypted",
        "D. It is always trustworthy if it comes from within the network"
    ],
    "answer": "B. It should be treated as potentially compromised and must be verified"
},
{
    "question": "What feature of SD-WAN enhances security by enabling encrypted connections across different transport links?",
    "options": [
        "A. Application-level security",
        "B. Site-to-site encryption",
        "C. Centralized traffic monitoring",
        "D. Direct connection to cloud services"
    ],
    "answer": "B. Site-to-site encryption"
},
{
    "question": "What is one of the main benefits of using SDN for network management?",
    "options": [
        "A. It requires no configuration changes at the network level",
        "B. It allows for real-time monitoring and control of network resources",
        "C. It restricts network access based on physical location only",
        "D. It requires multiple network management systems"
    ],
    "answer": "B. It allows for real-time monitoring and control of network resources"
},
{
    "question": "Which of the following is true about Zero Trust Architecture in terms of authentication?",
    "options": [
        "A. It requires minimal authentication steps once inside the network",
        "B. Authentication is required at every point of access, including device and user levels",
        "C. Authentication is only needed at the perimeter",
        "D. It assumes that all users inside the network are trusted"
    ],
    "answer": "B. Authentication is required at every point of access, including device and user levels"
},
{
    "question": "Which SD-WAN feature allows it to support a wide range of transport options?",
    "options": [
        "A. Hybrid connectivity",
        "B. Zero-touch provisioning",
        "C. Application-aware routing",
        "D. Transport agnosticism"
    ],
    "answer": "D. Transport agnosticism"
},
{
    "question": "What is one of the primary use cases for VXLAN in modern data centers?",
    "options": [
        "A. Providing layer 2 connectivity over a Layer 3 network",
        "B. Ensuring strict network access control",
        "C. Using Ethernet for high-speed transmission",
        "D. Replacing the need for traditional IP routing"
    ],
    "answer": "A. Providing layer 2 connectivity over a Layer 3 network"
},
{
    "question": "What does centralized policy management in SD-WAN enable?",
    "options": [
        "A. Automatic network troubleshooting",
        "B. The enforcement of security policies across all branches from a single location",
        "C. Direct device-to-device communication",
        "D. The use of static IP addresses only"
    ],
    "answer": "B. The enforcement of security policies across all branches from a single location"
},
{
    "question": "In SD-WAN, which of the following optimizes application traffic?",
    "options": [
        "A. Direct-to-cloud connectivity",
        "B. Dynamic path selection based on performance metrics",
        "C. Static routing protocols",
        "D. Dedicated leased lines for every application"
    ],
    "answer": "B. Dynamic path selection based on performance metrics"
},
{
    "question": "What does VXLAN stand for?",
    "options": [
        "A. Virtual Extensible Local Area Network",
        "B. Virtual Extended Layer Network",
        "C. Virtual Exchange Network",
        "D. Virtual Ethernet Extensible Network"
    ],
    "answer": "A. Virtual Extensible Local Area Network"
},
{
    "question": "In Zero Trust Architecture, why is access limited by the 'least privilege' principle?",
    "options": [
        "A. To prevent internal attackers from escalating privileges",
        "B. To ensure that only administrators can access sensitive resources",
        "C. To limit access based on the user's device security posture",
        "D. To enforce strict user authentication"
    ],
    "answer": "A. To prevent internal attackers from escalating privileges"
},
{
    "question": "What is the key difference between SD-WAN and traditional WAN?",
    "options": [
        "A. SD-WAN uses MPLS exclusively for routing traffic",
        "B. SD-WAN allows for automated network optimization and traffic routing based on performance metrics",
        "C. Traditional WANs are cloud-based",
        "D. SD-WAN requires manual configuration for each branch location"
    ],
    "answer": "B. SD-WAN allows for automated network optimization and traffic"
},
{
    "question": "In a Software-Defined Network (SDN), which component is responsible for controlling network traffic flows?", 
    "options": [
        "A. Application plane", 
        "B. Control plane", 
        "C. Data plane", 
        "D. Management plane"
    ], 
    "answer": "B. Control plane"
},
{
    "question": "What is the primary benefit of using Software-Defined Wide Area Network (SD-WAN) over traditional WAN solutions?", 
    "options": [
        "A. Increased physical hardware requirements", 
        "B. Application-aware routing and improved performance", 
        "C. Lower cost of service for users", 
        "D. Enhanced security through static routing"
    ], 
    "answer": "B. Application-aware routing and improved performance"
},
{
    "question": "How does SD-WAN simplify network management for distributed organizations?", 
    "options": [
        "A. By offering a direct connection to cloud services", 
        "B. By allowing for centralized control of the network through a single interface", 
        "C. By creating a mesh network between branch offices", 
        "D. By reducing the need for WAN optimization"
    ], 
    "answer": "B. By allowing for centralized control of the network through a single interface"
},
{
    "question": "What is 'zero-touch provisioning' in SD-WAN?", 
    "options": [
        "A. A manual setup process for devices at remote locations", 
        "B. A process that automates device configuration and deployment", 
        "C. A method of securing devices remotely", 
        "D. A process that requires device resets on first connection"
    ], 
    "answer": "B. A process that automates device configuration and deployment"
},
{
    "question": "Which of the following is a feature of SD-WAN that makes it transport agnostic?", 
    "options": [
        "A. It requires specific MPLS circuits for operation", 
        "B. It supports both public internet and private connections without restriction", 
        "C. It operates only on leased-line connections", 
        "D. It can only work with fiber-optic connections"
    ], 
    "answer": "B. It supports both public internet and private connections without restriction"
},
{
    "question": "What does centralized policy management in SD-WAN allow administrators to do?", 
    "options": [
        "A. Manage routing protocols independently for each device", 
        "B. Define and enforce network policies across the entire WAN from a single interface", 
        "C. Only manage user access to specific network segments", 
        "D. Restrict traffic flow based on physical location of devices"
    ], 
    "answer": "B. Define and enforce network policies across the entire WAN from a single interface"
},
{
    "question": "What is the primary use of VXLAN in data centers?", 
    "options": [
        "A. To support Layer 3 routing protocols", 
        "B. To provide an encapsulation method for Layer 2 communication over Layer 3 networks", 
        "C. To replace physical Ethernet cables", 
        "D. To provide higher-speed data transmission over fiber optics"
    ], 
    "answer": "B. To provide an encapsulation method for Layer 2 communication over Layer 3 networks"
},
{
    "question": "What is a key benefit of Virtual Extensible LAN (VXLAN) in terms of data center interconnect (DCI)?", 
    "options": [
        "A. It allows for data centers to operate in separate IP subnets", 
        "B. It allows for seamless communication between different data centers by encapsulating Layer 2 traffic", 
        "C. It requires less bandwidth than traditional VPNs", 
        "D. It offers encryption for Layer 2 traffic"
    ], 
    "answer": "B. It allows for seamless communication between different data centers by encapsulating Layer 2 traffic"
},
{
    "question": "What type of architecture does Zero Trust Architecture (ZTA) rely on?", 
    "options": [
        "A. Perimeter security", 
        "B. Implicit trust of all internal network traffic", 
        "C. Trust only after continuous verification and authentication", 
        "D. Only authentication at the network perimeter"
    ], 
    "answer": "C. Trust only after continuous verification and authentication"
},
{
    "question": "In Zero Trust Architecture, which principle is used to restrict access to resources?", 
    "options": [
        "A. Role-based access control (RBAC)", 
        "B. Least privilege access", 
        "C. Full access for internal users", 
        "D. User-defined access policies"
    ], 
    "answer": "B. Least privilege access"
},
{
    "question": "Which of the following is the primary purpose of policy-based authentication in Zero Trust Architecture?", 
    "options": [
        "A. To allow users access based solely on their network segment", 
        "B. To enforce authentication at multiple layers of the network", 
        "C. To trust all users from internal networks", 
        "D. To manage devices by software version"
    ], 
    "answer": "B. To enforce authentication at multiple layers of the network"
},
{
    "question": "Which of the following is a key feature of Zero Trust Architecture regarding user access?", 
    "options": [
        "A. Trust is granted automatically based on the user's network address", 
        "B. Authentication is only required during initial login", 
        "C. Access is granted after continuous verification and validation of the user’s identity", 
        "D. Only devices with specific IP addresses can access sensitive resources"
    ], 
    "answer": "C. Access is granted after continuous verification and validation of the user’s identity"
},
{
    "question": "Which of the following best describes the concept of least privilege access in Zero Trust Architecture?", 
    "options": [
        "A. Users and devices are only granted the minimum permissions necessary to complete their tasks", 
        "B. Users and devices are granted full access to all resources within the network", 
        "C. Access is unrestricted as long as a user is authenticated", 
        "D. Access is based on the role of the user alone"
    ], 
    "answer": "A. Users and devices are only granted the minimum permissions necessary to complete their tasks"
},
{
    "question": "Which of the following is a key principle of Zero Trust Architecture in the context of device management?", 
    "options": [
        "A. Devices must pass continuous validation to access network resources", 
        "B. Devices are trusted once they pass the initial authentication", 
        "C. Devices only require authentication at the network perimeter", 
        "D. Devices must be manually configured to comply with security policies"
    ], 
    "answer": "A. Devices must pass continuous validation to access network resources"
},
{
    "question": "What is the main goal of application-aware SD-WAN?", 
    "options": [
        "A. To route traffic based on the application type for optimized performance", 
        "B. To prevent unauthorized applications from entering the network", 
        "C. To monitor and log all network applications", 
        "D. To prioritize certain types of traffic over others regardless of application"
    ], 
    "answer": "A. To route traffic based on the application type for optimized performance"
},
{
    "question": "Which of the following is a benefit of Zero Trust Architecture in network security?", 
    "options": [
        "A. It requires less authentication for internal traffic", 
        "B. It assumes all users inside the network are trustworthy", 
        "C. It reduces the attack surface by restricting access at multiple levels", 
        "D. It only relies on perimeter security"
    ], 
    "answer": "C. It reduces the attack surface by restricting access at multiple levels"
},
{
    "question": "How does VXLAN provide scalability in a data center environment?", 
    "options": [
        "A. By reducing the size of the Layer 2 broadcast domain", 
        "B. By enabling the creation of multiple virtual networks on a physical network", 
        "C. By replacing traditional Layer 3 routing", 
        "D. By enhancing the security of Layer 2 traffic"
    ], 
    "answer": "B. By enabling the creation of multiple virtual networks on a physical network"
},
{
    "question": "In an SD-WAN, which type of application traffic is prioritized in an application-aware routing model?", 
    "options": [
        "A. HTTP and FTP traffic", 
        "B. VoIP and video conferencing traffic", 
        "C. All traffic is routed equally", 
        "D. Only encrypted traffic is prioritized"
    ], 
    "answer": "B. VoIP and video conferencing traffic"
},
    {
        "question": "You are tasked with subnetting a network with the IP address 192.168.20.0/24 into subnets of 50 hosts each. What subnet mask would you use?",
        "options": [
            "A. 255.255.255.128",
            "B. 255.255.255.192",
            "C. 255.255.255.224",
            "D. 255.255.255.240"
        ],
        "answer": "B. 255.255.255.192"
    },
    {
        "question": "You need to allocate IP addresses for 300 hosts in a subnet. Which subnet mask would you use to meet the requirement?",
        "options": [
            "A. 255.255.254.0",
            "B. 255.255.252.0",
            "C. 255.255.248.0",
            "D. 255.255.240.0"
        ],
        "answer": "A. 255.255.254.0"
    },
    {
        "question": "Which IP address class would be appropriate for a network requiring more than 65,536 host addresses?",
        "options": [
            "A. Class A",
            "B. Class B",
            "C. Class C",
            "D. Class D"
        ],
        "answer": "A. Class A"
    },
    {
        "question": "For a network using the IP address 10.10.0.0/16, how many subnets can be created using a /18 subnet mask?",
        "options": [
            "A. 2",
            "B. 4",
            "C. 8",
            "D. 16"
        ],
        "answer": "B. 4"
    },
    {
        "question": "What is the last usable host IP address in the subnet 192.168.1.0/29?",
        "options": [
            "A. 192.168.1.7",
            "B. 192.168.1.6",
            "C. 192.168.1.5",
            "D. 192.168.1.4"
        ],
        "answer": "B. 192.168.1.6"
    },
    {
        "question": "You are configuring a network with a 192.168.0.0/24 address. What is the subnet mask for the network?",
        "options": [
            "A. 255.255.255.0",
            "B. 255.255.255.128",
            "C. 255.255.255.255",
            "D. 255.255.255.192"
        ],
        "answer": "A. 255.255.255.0"
    },
    {
        "question": "What is the maximum number of hosts that can be accommodated in a subnet with the subnet mask 255.255.254.0?",
        "options": [
            "A. 510",
            "B. 1,022",
            "C. 2,048",
            "D. 4,096"
        ],
        "answer":  "B. 1,022"
    },
    {
        "question": "You are using the IP address 172.16.0.0/12. Which of the following represents a valid host address within this subnet?",
        "options": [
            "A. 172.16.255.255",
            "B. 172.16.0.0",
            "C. 172.16.1.1",
            "D. 172.32.0.1"
        ],
        "answer": "C. 172.16.1.1"
    },
    {
        "question": "In a network with the IP address 192.168.10.0/24, what is the broadcast address?",
        "options": [
            "A. 192.168.10.255",
            "B. 192.168.10.0",
            "C. 192.168.10.1",
            "D. 192.168.10.127"
        ],
        "answer": "A. 192.168.10.255"
    },
    {
        "question": "Which subnet mask would be appropriate for 10 hosts in a subnet?",
        "options": [
            "A. 255.255.255.248",
            "B. 255.255.255.224",
            "C. 255.255.255.240",
            "D. 255.255.255.252"
        ],
        "answer": "C. 255.255.255.240"
    },
    {
        "question": "You are assigned the address range 192.168.5.0/27. What is the last valid host address in this subnet?",
        "options": [
            "A. 192.168.5.31",
            "B. 192.168.5.30",
            "C. 192.168.5.29",
            "D. 192.168.5.32"
        ],
        "answer": "B. 192.168.5.30"
    },
    {
        "question": "What is the network address for the IP range 10.10.4.16/28?",
        "options": [
            "A. 10.10.4.16",
            "B. 10.10.4.15",
            "C. 10.10.4.0",
            "D. 10.10.4.1"
        ],
        "answer": "A. 10.10.4.16"
    },
    {
        "question": "Given the IP address 172.16.45.0/28, how many subnets can be created using a /30 subnet mask?",
        "options": [
            "A. 1",
            "B. 2",
            "C. 4",
            "D. 8"
        ],
        "answer": "C. 4"
    },
    {
        "question": "Which of the following address ranges is used for private addresses as per RFC 1918?",
        "options": [
            "A. 10.0.0.0 - 10.255.255.255",
            "B. 172.16.0.0 - 172.31.255.255",
            "C. 192.168.0.0 - 192.168.255.255",
            "D. All of the above"
        ],
        "answer": "D. All of the above"
    },
    {
        "question": "For the IP range 192.168.1.0/26, what is the subnet mask in decimal notation?",
        "options": [
            "A. 255.255.255.192",
            "B. 255.255.255.224",
            "C. 255.255.255.248",
            "D. 255.255.255.0"
        ],
        "answer": "A. 255.255.255.192"
    },
    {
        "question": "How many host addresses are available in a subnet with the subnet mask 255.255.255.240?",
        "options": [
            "A. 16",
            "B. 14",
            "C. 30",
            "D. 62"
        ],
        "answer": "B. 14"
    },
    {
        "question": "You are given the IP address 10.0.0.0/8 and need to break it down into subnets for 100 hosts each. Which subnet mask should you use?",
        "options": [
            "A. 255.255.255.0",
            "B. 255.255.254.0",
            "C. 255.255.252.0",
            "D. 255.255.255.128"
        ],
        "answer": "D. 255.255.255.128"
    },
    {
        "question": "What is the first valid host address in the subnet 192.168.10.128/25?",
        "options": [
            "A. 192.168.10.129",
            "B. 192.168.10.127",
            "C. 192.168.10.130",
            "D. 192.168.10.0"
        ],
        "answer": "A. 192.168.10.129"
    },
    {
        "question": "What is the valid range of host addresses for the subnet 172.16.0.0/22?",
        "options": [
            "A. 172.16.0.1 - 172.16.3.254",
            "B. 172.16.0.0 - 172.16.1.255",
            "C. 172.16.0.1 - 172.16.1.0",
            "D. 172.16.2.1 - 172.16.3.0"
        ],
        "answer": "A. 172.16.0.1 - 172.16.3.254"
    },
    {
        "question": "Given the IP address 10.10.10.0/24, how many total host addresses are available?",
        "options": [
            "A. 254",
            "B. 256",
            "C. 512",
            "D. 128"
        ],
        "answer": "A. 254"
    },
    {
        "question": "You need to address 500 hosts within a subnet. Which subnet mask would you use to allow this number of hosts?",
        "options": [
            "A. 255.255.255.0",
            "B. 255.255.255.192",
            "C. 255.255.255.224",
            "D. 255.255.254.0"
        ],
        "answer": "D. 255.255.254.0"
    },
    {
        "question": "In a network using CIDR notation, the IP address 10.0.0.0/16 is assigned. How many total IP addresses are available in this subnet?",
        "options": [
            "A. 65,536",
            "B. 256",
            "C. 1,024",
            "D. 16,384"
        ],
        "answer": "A. 65,536"
    },
    {
        "question": "You need to allocate IP addresses for a subnet with 200 hosts. Which subnet mask will allow exactly 200 host addresses?",
        "options": [
            "A. 255.255.255.224",
            "B. 255.255.255.192",
            "C. 255.255.254.0",
            "D. 255.255.255.0"
        ],
        "answer": "C. 255.255.254.0"
    },
    {
        "question": "What is the largest number of hosts that can be addressed with a subnet mask of 255.255.252.0?",
        "options": [
            "A. 1,022",
            "B. 510",
            "C. 2,048",
            "D. 2,550"
        ],
        "answer": "A. 1,022"
    },
    {
        "question": "Which of the following IPv4 address classes is used to define private addresses that are not routable over the internet?",
        "options": [
            "A. Class A",
            "B. Class B",
            "C. Class C",
            "D. Class A, B and C"
            
        ],
        "answer": "D. Class A, B and C"
    },
    {
        "question": "A network administrator is given the network 192.168.10.0/27. How many usable IP addresses are available in this subnet?",
        "options": [
            "A. 30",
            "B. 32",
            "C. 62",
            "D. 128"
        ],
        "answer": "A. 30"
    },
    {
        "question": "You are troubleshooting a subnet with a Class C IP address of 192.168.1.0/28. What is the network address for the second subnet in this range?",
        "options": [
            "A. 192.168.1.16",
            "B. 192.168.1.32",
            "C. 192.168.1.48",
            "D. 192.168.1.64"
        ],
        "answer": "A. 192.168.1.16"
    },
    {
        "question": "You need to configure a loopback address for testing. What is the correct address to assign to the loopback interface?",
        "options": [
            "A. 127.0.0.1",
            "B. 0.0.0.0",
            "C. 192.168.1.1",
            "D. 10.0.0.1"
        ],
        "answer": "A. 127.0.0.1"
    },
    {
        "question": "In a network with the IP range 192.168.1.0/24, what is the first valid host IP address?",
        "options": [
            "A. 192.168.1.1",
            "B. 192.168.1.0",
            "C. 192.168.1.255",
            "D. 192.168.0.1"
        ],
        "answer": "A. 192.168.1.1"
    },
    {
        "question": "You are tasked with subnetting a network 192.168.10.0/24 into subnets with 30 hosts each. Which subnet mask should you use?",
        "options": [
            "A. 255.255.255.224",
            "B. 255.255.255.192",
            "C. 255.255.255.240",
            "D. 255.255.255.128"
        ],
        "answer": "A. 255.255.255.224"
    },
    {
        "question": "You have configured a network with a /28 subnet mask. What is the maximum number of hosts that can be assigned to this network?",
        "options": [
            "A. 14",
            "B. 16",
            "C. 30",
            "D. 62"
        ],
        "answer": "A. 14"
    },
    {
        "question": "You are implementing a network using CIDR notation and the IP address range 10.0.0.0/22. How many subnets will be available in this range?",
        "options": [
            "A. 4",
            "B. 8",
            "C. 16",
            "D. 64"
        ],
        "answer": "A. 4"
    },
    {
        "question": "Which of the following IP address classes is used for private networks, specifically for host addresses within large organizational networks?",
        "options": [
            "A. Class A",
            "B. Class B",
            "C. Class C",
            "D. Class D"
        ],
        "answer": "A. Class A"
    },
    {
        "question": "You are working with a network configuration of 10.0.0.0/8. What is the first available host address in this range?",
        "options": [
            "A. 10.0.0.1",
            "B. 10.0.0.0",
            "C. 10.0.0.255",
            "D. 10.0.1.0"
        ],
        "answer": "A. 10.0.0.1"
    },
    {
        "question": "You have a network with an IP address of 192.168.1.0/24. What is the broadcast address for this network?",
        "options": [
            "A. 192.168.1.255",
            "B. 192.168.1.0",
            "C. 192.168.0.255",
            "D. 192.168.1.1"
        ],
        "answer": "A. 192.168.1.255"
    },
    {
        "question": "A network uses the IP range 10.0.0.0/8. If the first octet is used for subnetting, what is the correct subnet mask for this configuration?",
        "options": [
            "A. 255.0.0.0",
            "B. 255.255.0.0",
            "C. 255.255.255.0",
            "D. 255.255.255.255"
        ],
        "answer": "A. 255.0.0.0"
},
    {
        "question": "You are configuring a network for an internal organization where you need to assign IP addresses to devices without the need for a DHCP server. Which method would allow devices to assign themselves an IP address automatically if a DHCP server is unavailable?",
        "options": [
            "A. APIPA",
            "B. RFC1918",
            "C. Loopback",
            "D. CIDR"
        ],
        "answer": "A. APIPA"
    },
    {
        "question": "Your company has a private network that spans multiple locations and needs to use a range of private IP addresses. Which range of IP addresses would be appropriate for internal use according to RFC1918?",
        "options": [
            "A. 10.0.0.0 - 10.255.255.255",
            "B. 192.168.0.0 - 192.168.255.255",
            "C. 172.16.0.0 - 172.31.255.255",
            "D. All of the above"
        ],
        "answer": "D. All of the above"
    },
    {
        "question": "You are troubleshooting a server that cannot communicate with other devices on the local network but can still access the local machine. What could be the likely cause of this issue?",
        "options": [
            "A. APIPA address",
            "B. VLSM misconfiguration",
            "C. CIDR misconfiguration",
            "D. Loopback address"
        ],
        "answer": "A. APIPA address"
    },
    {
        "question": "A device is configured with an IP address in the range of 172.16.0.0 to 172.31.255.255. This range is part of which address category?",
        "options": [
            "A. Public IP",
            "B. Private IP",
            "C. APIPA",
            "D. Loopback"
        ],
        "answer": "B. Private IP"
    },
    {
        "question": "You have been assigned a public IP address from your ISP. You need to configure your network in such a way that internal devices are assigned addresses from a private range. What is the best practice?",
        "options": [
            "A. Use a private address range like RFC1918 and NAT",
            "B. Use APIPA addresses for all internal devices",
            "C. Use only public IP addresses for all internal devices",
            "D. Use a Loopback address for all internal devices"
        ],
        "answer": "A. Use a private address range like RFC1918 and NAT"
    },
    {
        "question": "You are working on a subnetting project, and the IP range needs to be broken down into smaller subnets. Which technique would you use to do this efficiently?",
        "options": [
            "A. VLSM",
            "B. CIDR",
            "C. APIPA",
            "D. Subnetting with default subnet masks"
        ],
        "answer": "A. VLSM"
    },
    {
        "question": "Your organization has received a large block of IP addresses and you need to divide this block into smaller subnets of various sizes. Which subnetting technique would allow you to do this?",
        "options": [
            "A. CIDR",
            "B. APIPA",
            "C. VLSM",
            "D. RFC1918"
        ],
        "answer": "C. VLSM"
    },
    {
        "question": "You are planning to use a private IP address for your web server inside the corporate network. Which IP address class should you choose?",
        "options": [
            "A. Class A",
            "B. Class B",
            "C. Class C",
            "D. All of Them."
           
        ],
        "answer": "D.All of Them."
    },
    {
        "question": "You are configuring a network for a large enterprise. The network requires addressing from the 172.16.0.0 - 172.31.255.255 range. Which address class do these IP addresses belong to?",
        "options": [
            "A. Class A",
            "B. Class B",
            "C. Class C",
            "D. Class D"
        ],
        "answer": "B. Class B"
    },
    {
        "question": "Which IPv4 address class is used for multicasting, and is often reserved for specific network protocols?",
        "options": [
            "A. Class A",
            "B. Class B",
            "C. Class C",
            "D. Class D"
        ],
        "answer": "D. Class D"
    },
    {
        "question": "Which address class allows you to have a large number of host addresses and is commonly used in large private networks?",
        "options": [
            "A. Class A",
            "B. Class B",
            "C. Class C",
            "D. Class E"
        ],
        "answer": "A. Class A"
    },
    {
        "question": "You are tasked with setting up a loopback interface for testing purposes. Which IP address would you assign to the loopback interface?",
        "options": [
            "A. 192.168.1.1",
            "B. 172.16.0.1",
            "C. 127.0.0.1",
            "D. 10.0.0.1"
        ],
        "answer": "C. 127.0.0.1"
    },
    {
        "question": "You are implementing CIDR notation to allocate IP addresses. What does the '/24' represent in the CIDR notation?",
        "options": [
            "A. Number of subnets",
            "B. Number of host bits",
            "C. Subnet mask",
            "D. IP address range"
        ],
        "answer": "C. Subnet mask"
    },
    {
        "question": "You need to create a network with exactly 50 subnets. What is the minimum number of bits you should borrow from the host portion of an IPv4 address to accomplish this task?",
        "options": [
            "A. 5",
            "B. 6",
            "C. 7",
            "D. 8"
        ],
        "answer": "B. 6"
    },
    {
        "question": "You are tasked with configuring a network where the first 3 bits of the host portion need to be borrowed for subnetting. Which subnet mask will you use?",
        "options": [
            "A. 255.255.255.252",
            "B. 255.255.255.224",
            "C. 255.255.255.192",
            "D. 255.255.255.128"
        ],
        "answer": "B. 255.255.255.224"
    },
    {
        "question": "A network administrator assigns an IP address 192.168.10.5/28 to a network. What is the size of the subnet mask in this configuration?",
        "options": [
            "A. 255.255.255.248",
            "B. 255.255.255.240",
            "C. 255.255.255.255",
            "D. 255.255.255.192"
        ],
        "answer": "B. 255.255.255.240"
    },
    {
        "question": "You are working with a network where the classful subnetting method is not feasible due to the requirements of variable subnet sizes. Which method should you use to create flexible and efficient subnets?",
        "options": [
            "A. CIDR",
            "B. APIPA",
            "C. VLSM",
            "D. Loopback"
        ],
        "answer": "C. VLSM"
    },
    {
        "question": "A large organization requires more than 65,000 IP addresses. Which class of IP address would you recommend for this organization?",
        "options": [
            "A. Class A",
            "B. Class B",
            "C. Class C",
            "D. Class D"
        ],
        "answer": "A. Class A"
    },
    {
        "question": "Which IPv4 address class is used for experimental purposes and is not routable on the public internet?",
        "options": [
            "A. Class E",
            "B. Class D",
            "C. Class C",
            "D. Class B"
        ],
        "answer": "A. Class E"
    },
    {
        "question": "In a network that requires only a few hosts, which IPv4 address class would you most likely use for small networks, ensuring you have enough host addresses available?",
        "options": [
            "A. Class A",
            "B. Class B",
            "C. Class C",
            "D. Class D"
        ],
        "answer": "C. Class C"
    },
    {
        "question": "You are tasked with configuring a network where devices need to communicate with minimal latency. You must ensure that if one device fails, traffic can still flow efficiently between the remaining devices. Which topology do you choose and why?",
        "options": [
            "A. Mesh",
            "B. Star/Hub and Spoke",
            "C. Three-Tier Hierarchical Model",
            "D. Point to Point"
        ],
        "answer": "A. Mesh"
    },
    {
        "question": "Your company has expanded, and you now need to support multiple departments across several locations with high availability and scalability. How would you design the network to ensure both high availability and ease of expansion?",
        "options": [
            "A. Spine and Leaf",
            "B. Hybrid",
            "C. Mesh",
            "D. Star/Hub and Spoke"
        ],
        "answer": "A. Spine and Leaf"
    },
    {
        "question": "You are configuring a network for a small office with limited growth potential. Which topology would be easiest to implement and manage while ensuring low cost?",
        "options": [
            "A. Star/Hub and Spoke",
            "B. Mesh",
            "C. Hybrid",
            "D. Collapsed Core"
        ],
        "answer": "A. Star/Hub and Spoke"
    },
    {
        "question": "A data center requires high throughput and low-latency communication between multiple servers. You need to ensure efficient data transfer. Which network design would you implement?",
        "options": [
            "A. East-West Traffic Flow",
            "B. North-South Traffic Flow",
            "C. Point to Point",
            "D. Hybrid"
        ],
        "answer": "A. East-West Traffic Flow"
    },
    {
        "question": "You are designing a network that will experience frequent changes in terms of devices being added and removed. Which topology provides flexibility while ensuring ease of management?",
        "options": [
            "A. Hybrid",
            "B. Mesh",
            "C. Star/Hub and Spoke",
            "D. Spine and Leaf"
        ],
        "answer": "C. Star/Hub and Spoke"
    },
    {
        "question": "In a large enterprise, you need to ensure that traffic from the internet flows efficiently into your internal network, which topology and traffic flow should you prioritize?",
        "options": [
            "A. North-South Traffic Flow with Star/Hub and Spoke Topology",
            "B. East-West Traffic Flow with Mesh Topology",
            "C. North-South Traffic Flow with Spine and Leaf Topology",
            "D. East-West Traffic Flow with Three-Tier Hierarchical Model"
        ],
        "answer": "A. North-South Traffic Flow with Star/Hub and Spoke Topology"
    },
    {
        "question": "You are designing a network for a cloud-based application with large-scale traffic communication between internal servers. Which traffic flow is critical for optimal performance?",
        "options": [
            "A. East-West Traffic Flow",
            "B. North-South Traffic Flow",
            "C. Point to Point",
            "D. Hybrid"
        ],
        "answer": "A. East-West Traffic Flow"
    },
    {
        "question": "You are tasked with connecting two geographically separated offices. The network design must have a dedicated and reliable connection with minimal points of failure. Which topology do you implement?",
        "options": [
            "A. Point to Point",
            "B. Mesh",
            "C. Hybrid",
            "D. Star/Hub and Spoke"
        ],
        "answer": "A. Point to Point"
    },
    {
        "question": "A large-scale cloud data center needs to scale without downtime, with multiple servers communicating efficiently. Which network architecture best fits this requirement?",
        "options": [
            "A. Three-Tier Hierarchical Model",
            "B. Collapsed Core",
            "C. Spine and Leaf",
            "D. Hybrid"
        ],
        "answer": "C. Spine and Leaf"
    },
    {
        "question": "You are implementing a new network for a data center where performance and scalability are critical. Which network design ensures scalability and redundancy while minimizing network latency?",
        "options": [
            "A. Mesh",
            "B. Hybrid",
            "C. Spine and Leaf",
            "D. Star/Hub and Spoke"
        ],
        "answer": "C. Spine and Leaf"
    },
    {
        "question": "You have been asked to set up a network in a large organization that has multiple departments. Each department needs to be isolated but still able to communicate with others. What would be your approach to segmentation?",
        "options": [
            "A. Implement a Hybrid Network with VLANs",
            "B. Implement a Star/Hub and Spoke Topology",
            "C. Implement a Mesh Network with point-to-point connections",
            "D. Use a Three-Tier Hierarchical Model"
        ],
        "answer": "A. Implement a Hybrid Network with VLANs"
    },
    {
        "question": "Your company has recently expanded, and you are tasked with creating a new network to handle increased traffic. You need a topology that will grow with the company. Which topology will allow for future scalability?",
        "options": [
            "A. Mesh",
            "B. Three-Tier Hierarchical Model",
            "C. Collapsed Core",
            "D. Hybrid"
        ],
        "answer": "B. Three-Tier Hierarchical Model"
    },
    {
        "question": "A company needs a network with full redundancy and zero points of failure. Which topology should be used to meet these high availability requirements?",
        "options": [
            "A. Mesh",
            "B. Point to Point",
            "C. Hybrid",
            "D. Star/Hub and Spoke"
        ],
        "answer": "A. Mesh"
    },
    {
        "question": "You need to design a network for a business where each device has to be connected to a central point to simplify management. Which topology should you use?",
        "options": [
            "A. Star/Hub and Spoke",
            "B. Point to Point",
            "C. Hybrid",
            "D. Mesh"
        ],
        "answer": "A. Star/Hub and Spoke"
    },
    {
        "question": "You are tasked with building a network that will allow for devices to be added or removed easily. Which topology best supports this type of growth and flexibility?",
        "options": [
            "A. Star/Hub and Spoke",
            "B. Mesh",
            "C. Hybrid",
            "D. Spine and Leaf"
        ],
        "answer": "A. Star/Hub and Spoke"
    },
    {
        "question": "Your company needs to ensure that traffic between servers remains uninterrupted despite network failures. Which topology offers this level of redundancy?",
        "options": [
            "A. Mesh",
            "B. Point to Point",
            "C. Hybrid",
            "D. Star/Hub and Spoke"
        ],
        "answer": "A. Mesh"
    },
    {
        "question": "You are tasked with designing a network where you need to ensure that all devices in the network can communicate with each other even if one device goes down. Which topology would you choose?",
        "options": [
            "A. Mesh",
            "B. Star/Hub and Spoke",
            "C. Hybrid",
            "D. Collapsed Core"
        ],
        "answer": "A. Mesh"
    },
    {
        "question": "A network has been growing rapidly and requires more scalable architecture without needing to reconfigure the entire network. Which design would support easy growth?",
        "options": [
            "A. Three-Tier Hierarchical Model",
            "B. Point to Point",
            "C. Mesh",
            "D. Hybrid"
        ],
        "answer": "A. Three-Tier Hierarchical Model"
    },
    {
        "question": "You need to implement a network design that ensures servers in a data center can communicate efficiently with minimal traffic bottlenecks. Which topology will provide the best performance?",
        "options": [
            "A. Spine and Leaf",
            "B. Star/Hub and Spoke",
            "C. Mesh",
            "D. Hybrid"
        ],
        "answer": "A. Spine and Leaf"
    },
    {
        "question": "Your organization requires a network that can grow without much reconfiguration, and you need to ensure that the architecture remains simple. What design would best suit this need?",
        "options": [
            "A. Collapsed Core",
            "B. Three-Tier Hierarchical Model",
            "C. Mesh",
            "D. Hybrid"
        ],
        "answer": "B. Three-Tier Hierarchical Model"
    },
    {
        "question": "In a network with high-performance needs where many servers communicate with each other, you are seeing performance issues related to high traffic between servers. Which traffic flow should be optimized?",
        "options": [
            "A. East-West Traffic Flow",
            "B. North-South Traffic Flow",
            "C. Point to Point",
            "D. Hybrid"
        ],
        "answer": "A. East-West Traffic Flow"
    },
    {
        "question": "You are tasked with implementing a dedicated connection between two data centers for mission-critical applications. Which topology would you choose to ensure reliable performance and minimal downtime?",
        "options": [
            "A. Point to Point",
            "B. Hybrid",
            "C. Mesh",
            "D. Star/Hub and Spoke"
        ],
        "answer": "A. Point to Point"
    },
    {
        "question": "You are responsible for a large network infrastructure where several sites must be interconnected. Each site should operate independently, but you still need seamless communication between them. Which architecture would you implement?",
        "options": [
            "A. Hybrid",
            "B. Mesh",
            "C. Three-Tier Hierarchical Model",
            "D. Collapsed Core"
        ],
        "answer": "B. Mesh"
    },
    {
        "question": "You are designing a network for a large organization with multiple departments in different geographical locations. Which topology would be best suited for efficient communication between all devices while minimizing downtime?",
        "options": [
            "A. Mesh",
            "B. Hybrid",
            "C. Star/Hub and Spoke",
            "D. Spine and Leaf"
        ],
        "answer": "A. Mesh"
    },
    {
        "question": "You are tasked with building a network for a smaller organization where centralization and ease of management are important. Which topology would you select?",
        "options": [
            "A. Mesh",
            "B. Star/Hub and Spoke",
            "C. Point to Point",
            "D. Hybrid"
        ],
        "answer": "B. Star/Hub and Spoke"
    },
    {
        "question": "In a large data center where scalability and high availability are key, which network topology would be most suitable?",
        "options": [
            "A. Hybrid",
            "B. Spine and Leaf",
            "C. Point to Point",
            "D. Mesh"
        ],
        "answer": "B. Spine and Leaf"
    },
    {
        "question": "You need to design a network where each device connects directly to a central hub. Which topology is best suited for this scenario?",
        "options": [
            "A. Star/Hub and Spoke",
            "B. Mesh",
            "C. Hybrid",
            "D. Point to Point"
        ],
        "answer": "A. Star/Hub and Spoke"
    },
    {
        "question": "You are designing a network for a cloud-based infrastructure and need to ensure redundancy with minimal hops between devices. Which topology would be ideal?",
        "options": [
            "A. Mesh",
            "B. Three-Tier Hierarchical Model",
            "C. Hybrid",
            "D. Spine and Leaf"
        ],
        "answer": "A. Mesh"
    },
    {
        "question": "In a scenario where minimal downtime and fast recovery are needed, which topology would allow for multiple backup connections between devices?",
        "options": [
            "A. Mesh",
            "B. Star/Hub and Spoke",
            "C. Three-Tier Hierarchical Model",
            "D. Hybrid"
        ],
        "answer": "A. Mesh"
    },
    {
        "question": "A business is transitioning from a simple network to one that can easily scale with growing demands. Which topology should be used to maintain flexibility and scalability?",
        "options": [
            "A. Three-Tier Hierarchical Model",
            "B. Star/Hub and Spoke",
            "C. Hybrid",
            "D. Point to Point"
        ],
        "answer": "A. Three-Tier Hierarchical Model"
    },
    {
        "question": "You need to connect two geographically separated offices over a dedicated link. Which topology would be the most appropriate for this point-to-point connection?",
        "options": [
            "A. Point to Point",
            "B. Hybrid",
            "C. Star/Hub and Spoke",
            "D. Mesh"
        ],
        "answer": "A. Point to Point"
    },
    {
        "question": "For a large, high-availability data center network with multiple core switches and devices, which architecture would provide efficient traffic distribution across various access layers?",
        "options": [
            "A. Core, Distribution, and Access Model",
            "B. Point to Point",
            "C. Spine and Leaf",
            "D. Mesh"
        ],
        "answer": "A. Core, Distribution, and Access Model"
    },
    {
        "question": "In an organization with a focus on minimizing overhead costs while providing scalability, which network design would you recommend?",
        "options": [
            "A. Collapsed Core",
            "B. Three-Tier Hierarchical Model",
            "C. Spine and Leaf",
            "D. Mesh"
        ],
        "answer": "A. Collapsed Core"
    },
    {
        "question": "When you need to design a network with high availability and redundancy, where devices must be interconnected in a manner that eliminates single points of failure, which architecture should you use?",
        "options": [
            "A. Mesh",
            "B. Hybrid",
            "C. Three-Tier Hierarchical Model",
            "D. Point to Point"
        ],
        "answer": "A. Mesh"
    },
    {
        "question": "In a high-performance network requiring low latency and minimal data bottlenecks, which network design is best suited for this kind of traffic flow?",
        "options": [
            "A. North-South Traffic Flow",
            "B. East-West Traffic Flow",
            "C. Spine and Leaf",
            "D. Point to Point"
        ],
        "answer": "C. Spine and Leaf"
    },
    {
        "question": "For a company that is implementing a cloud-based application with services that require constant inbound and outbound data flow, which traffic flow should be prioritized?",
        "options": [
            "A. North-South",
            "B. East-West",
            "C. Point to Point",
            "D. Hybrid"
        ],
        "answer": "A. North-South"
    },
    {
        "question": "You are configuring a data center with a distributed network that requires constant communication between servers. Which traffic flow type is most appropriate?",
        "options": [
            "A. North-South",
            "B. East-West",
            "C. Point to Point",
            "D. Hybrid"
        ],
        "answer": "B. East-West"
    },
    {
        "question": "In a large enterprise with multiple departments and geographical locations, which topology would provide scalability while ensuring minimal latency in communication between different office sites?",
        "options": [
            "A. Star/Hub and Spoke",
            "B. Mesh",
            "C. Spine and Leaf",
            "D. Hybrid"
        ],
        "answer": "B. Mesh"
    },
    {
        "question": "For a simple network with centralized control and easy maintenance where each device connects to a central point, which topology is most effective?",
        "options": [
            "A. Point to Point",
            "B. Star/Hub and Spoke",
            "C. Mesh",
            "D. Hybrid"
        ],
        "answer": "B. Star/Hub and Spoke"
    },
    {
        "question": "You are setting up a network for a small office with limited scalability. Which topology would provide the simplest and least expensive solution?",
        "options": [
            "A. Point to Point",
            "B. Hybrid",
            "C. Star/Hub and Spoke",
            "D. Mesh"
        ],
        "answer": "C. Star/Hub and Spoke"
    },
    {
        "question": "In a hybrid network where different parts of the network use different topologies, which element would allow seamless communication across these diverse components?",
        "options": [
            "A. A centralized hub",
            "B. Redundant connections",
            "C. Interoperable devices",
            "D. Three-Tier Hierarchical Model"
        ],
        "answer": "C. Interoperable devices"
    },
    {
        "question": "You are working with a network where devices are connected in a way that eliminates any single point of failure and provides full redundancy. Which architecture are you implementing?",
        "options": [
            "A. Mesh",
            "B. Hybrid",
            "C. Star/Hub and Spoke",
            "D. Collapsed Core"
        ],
        "answer": "A. Mesh"
    },
    {
        "question": "In a cloud infrastructure that requires high throughput for data transfer between servers, which traffic flow direction is typically emphasized?",
        "options": [
            "A. North-South",
            "B. East-West",
            "C. Point to Point",
            "D. Hybrid"
        ],
        "answer": "B. East-West"
    },
    {
        "question": "Which architecture provides a scalable, redundant, and easy-to-manage model by consolidating the core and distribution layers into a single layer?",
        "options": [
            "A. Three-Tier Hierarchical Model",
            "B. Collapsed Core",
            "C. Hybrid",
            "D. Point to Point"
        ],
        "answer": "B. Collapsed Core"
    },
    {
        "question": "In a network where traffic moves predominantly between external devices and the internet, which traffic flow type should be prioritized?",
        "options": [
            "A. North-South",
            "B. East-West",
            "C. Mesh",
            "D. Point to Point"
        ],
        "answer": "A. North-South"
    },
    {
        "question": "When designing a large-scale network with multiple layers of routing and switching, which model provides the best approach for scaling with minimal downtime?",
        "options": [
            "A. Three-Tier Hierarchical Model",
            "B. Mesh",
            "C. Hybrid",
            "D. Collapsed Core"
        ],
        "answer": "A. Three-Tier Hierarchical Model"
    },
    {
        "question": "In a hybrid network setup where different departments use different types of network topologies, which design principle ensures compatibility across these topologies?",
        "options": [
            "A. Consistent routing protocols",
            "B. Simplified topology",
            "C. Increased redundancy",
            "D. Network segmentation"
        ],
        "answer": "A. Consistent routing protocols"
    },
    {
        "question": "When designing a network that prioritizes redundancy, fault tolerance, and scalability, which topology would you select?",
        "options": [
            "A. Mesh",
            "B. Star/Hub and Spoke",
            "C. Three-Tier Hierarchical Model",
            "D. Collapsed Core"
        ],
        "answer": "A. Mesh"
    },
    {
        "question": "Which topology is most effective in environments where network speed, high scalability, and minimal traffic bottlenecks are essential?",
        "options": [
            "A. Mesh",
            "B. Spine and Leaf",
            "C. Hybrid",
            "D. Point to Point"
        ],
        "answer": "B. Spine and Leaf"
    },
    {
        "question": "You are designing a high-speed local area network (LAN) for a data center. Which cable type should you use for short-distance, low-latency, high-throughput connections?",
        "options": [
            "A. Single-mode fiber",
            "B. Multimode fiber",
            "C. Direct Attach Copper (DAC)",
            "D. Coaxial cable"
        ],
        "answer": "C. Direct Attach Copper (DAC)"
    },
    {
        "question": "A company needs to connect two buildings in a campus network with a high-speed, long-distance fiber optic link. Which type of fiber optic cable should be used?",
        "options": [
            "A. Multimode fiber",
            "B. Single-mode fiber",
            "C. Direct Attach Copper (DAC)",
            "D. Coaxial cable"
        ],
        "answer": "B. Single-mode fiber"
    },
    {
        "question": "You are setting up a wireless network in a busy office building with multiple floors. Which 802.11 standard should you choose to ensure the best coverage and performance for a large number of devices?",
        "options": [
            "A. 802.11n",
            "B. 802.11ac",
            "C. 802.11g",
            "D. 802.11b"
        ],
        "answer": "B. 802.11ac"
    },
    {
        "question": "In a long-distance wireless connection between a satellite and a ground station, which technology would be most appropriate?",
        "options": [
            "A. Cellular",
            "B. Satellite",
            "C. 802.11ac",
            "D. Bluetooth"
        ],
        "answer": "B. Satellite"
    },
    {
        "question": "You are tasked with installing a fiber optic cable in a ceiling space with ventilation. Which type of cable jacket would you select to ensure it meets safety requirements?",
        "options": [
            "A. Non-plenum cable",
            "B. Plenum cable",
            "C. Fiber optic cable",
            "D. Coaxial cable"
        ],
        "answer": "B. Plenum cable"
    },
    {
        "question": "For a high-speed Ethernet connection over fiber optics, you need a transceiver that supports small-form-factor pluggable interfaces. Which would you select?",
        "options": [
            "A. SFP",
            "B. QSFP",
            "C. RJ45",
            "D. Fibre Channel (FC)"
        ],
        "answer": "A. SFP"
    },
    {
        "question": "You need to install a high-speed network link between two devices that need to transmit large amounts of data with minimal latency. Which transceiver would be most suitable for this scenario?",
        "options": [
            "A. SFP",
            "B. QSFP",
            "C. RJ45",
            "D. LC"
        ],
        "answer": "B. QSFP"
    },
    {
        "question": "A company needs to ensure that its network is future-proof and capable of handling massive data loads with high performance over fiber optics. Which transceiver type would you recommend?",
        "options": [
            "A. SFP",
            "B. QSFP",
            "C. RJ45",
            "D. ST"
        ],
        "answer": "B. QSFP"
    },
    {
        "question": "Which connector type is most commonly used for single-mode fiber optic cable in a high-density network setup?",
        "options": [
            "A. SC",
            "B. LC",
            "C. RJ45",
            "D. ST"
        ],
        "answer": "B. LC"
    },
    {
        "question": "You are planning a fiber optic installation in a network with limited space for connectors. Which connector type should you select to maximize space efficiency?",
        "options": [
            "A. SC",
            "B. LC",
            "C. MPO",
            "D. RJ45"
        ],
        "answer": "B. LC"
    },
    {
        "question": "For a network with extremely high-density fiber connections, which connector type supports up to 12 fibers in a single connector?",
        "options": [
            "A. SC",
            "B. LC",
            "C. MPO",
            "D. RJ45"
        ],
        "answer": "C. MPO"
    },
    {
        "question": "You are setting up a network for a building with multiple offices. Which type of Ethernet cable is the most appropriate for the general network connections?",
        "options": [
            "A. Cat5e",
            "B. Cat6a",
            "C. Fiber optic cable",
            "D. Coaxial cable"
        ],
        "answer": "B. Cat6a"
    },
    {
        "question": "Which cable type would you use for long-distance network connections with high-speed data transfer between different campus buildings?",
        "options": [
            "A. Single-mode fiber",
            "B. Multimode fiber",
            "C. Coaxial cable",
            "D. Direct Attach Copper (DAC)"
        ],
        "answer": "A. Single-mode fiber"
    },
    {
        "question": "If you were setting up an office network that required high-speed internet access for both voice and data transmissions, which transceiver would you choose?",
        "options": [
            "A. SFP",
            "B. Fibre Channel (FC)",
            "C. RJ45",
            "D. QSFP"
        ],
        "answer": "A. SFP"
    },
    {
        "question": "A company is installing a high-speed fiber optic network in a building with very limited ceiling space for wiring. Which type of cable jacket should be used for fire safety in these conditions?",
        "options": [
            "A. Plenum cable",
            "B. Non-plenum cable",
            "C. Fiber optic cable",
            "D. Coaxial cable"
        ],
        "answer": "A. Plenum cable"
    },
    {
        "question": "For a high-speed Ethernet connection that requires fiber optic technology with reduced space usage, which transceiver type would be appropriate?",
        "options": [
            "A. QSFP",
            "B. SFP",
            "C. RJ45",
            "D. LC"
        ],
        "answer": "B. SFP"
    },
    {
        "question": "In a scenario where two networking devices need to communicate over a high-speed fiber connection with minimal signal loss and increased bandwidth, which type of fiber optic cable would be most suitable?",
        "options": [
            "A. Single-mode fiber",
            "B. Multimode fiber",
            "C. Coaxial cable",
            "D. Twinaxial cable"
        ],
        "answer": "A. Single-mode fiber"
    },
    {
        "question": "You are setting up a fiber optic link in a campus environment. The network is prone to high interference and requires a durable and reliable connection. Which fiber optic cable would be best suited for this environment?",
        "options": [
            "A. Multimode fiber",
            "B. Single-mode fiber",
            "C. Direct Attach Copper (DAC)",
            "D. Coaxial cable"
        ],
        "answer": "B. Single-mode fiber"
    },
    {
        "question": "You need to install a fiber optic link between two network devices that are 500 meters apart. Which type of fiber optic cable should you use?",
        "options": [
            "A. Multimode fiber",
            "B. Single-mode fiber",
            "C. Coaxial cable",
            "D. Direct Attach Copper (DAC)"
        ],
        "answer": "A. Multimode fiber"
    },
    {
        "question": "A fiber optic installation requires that the connector be compatible with both single-mode and multimode cables. Which connector would you use?",
        "options": [
            "A. SC",
            "B. LC",
            "C. MPO",
            "D. RJ45"
        ],
        "answer": "A. SC"
    },
    {
        "question": "Which fiber optic connector is best suited for high-density environments, offering a small form factor with minimal space requirements?",
        "options": [
            "A. LC",
            "B. SC",
            "C. MPO",
            "D. ST"
        ],
        "answer": "A. LC"
    },
    {
        "question": "You are tasked with connecting a network device to a router in an environment with minimal signal interference. Which cable type should you use?",
        "options": [
            "A. Coaxial cable",
            "B. Fiber optic cable",
            "C. Direct Attach Copper (DAC)",
            "D. Ethernet cable"
        ],
        "answer": "B. Fiber optic cable"
    },
    {
        "question": "In a scenario where you need to establish a high-performance link for data transmission over long distances with fiber optics, which cable would you prefer?",
        "options": [
            "A. Single-mode fiber",
            "B. Multimode fiber",
            "C. Direct Attach Copper (DAC)",
            "D. Coaxial cable"
        ],
        "answer": "A. Single-mode fiber"
    },
    {
        "question": "For installing a fiber optic connection in a high-interference environment, which connector would be suitable for multimode fiber optic cables?",
        "options": [
            "A. SC",
            "B. LC",
            "C. ST",
            "D. MPO"
        ],
        "answer": "C. ST"
},
    {
        "question": "Which of the following 802.11 standards supports the highest maximum data transfer rate?",
        "options": [
            "A. 802.11n",
            "B. 802.11ac",
            "C. 802.11b",
            "D. 802.11g"
        ],
        "answer": "B. 802.11ac"
    },
    {
        "question": "Which of the following wireless technologies operates on a cellular network?",
        "options": [
            "A. Cellular",
            "B. Satellite",
            "C. 802.11ac",
            "D. Bluetooth"
        ],
        "answer": "A. Cellular"
    },
    {
        "question": "Which type of wireless technology is used for long-distance communication between satellites and ground stations?",
        "options": [
            "A. Satellite",
            "B. Cellular",
            "C. 802.11ac",
            "D. NFC"
        ],
        "answer": "A. Satellite"
    },
    {
        "question": "Which of the following is a standard for wired Ethernet networking?",
        "options": [
            "A. 802.3",
            "B. 802.11ac",
            "C. 802.1X",
            "D. 802.15"
        ],
        "answer": "A. 802.3"
    },
    {
        "question": "Which type of fiber optic cable is designed for long-distance transmission and uses a single strand of glass or plastic?",
        "options": [
            "A. Single-mode fiber",
            "B. Multimode fiber",
            "C. Coaxial cable",
            "D. Direct Attach Copper (DAC)"
        ],
        "answer": "A. Single-mode fiber"
    },
    {
        "question": "Which type of fiber optic cable is designed for short-distance transmission and uses multiple strands of glass or plastic?",
        "options": [
            "A. Multimode fiber",
            "B. Single-mode fiber",
            "C. Coaxial cable",
            "D. Direct Attach Copper (DAC)"
        ],
        "answer": "A. Multimode fiber"
    },
    {
        "question": "Which type of cable is commonly used for high-speed, short-distance connections in data centers?",
        "options": [
            "A. Direct Attach Copper (DAC)",
            "B. Fiber optic cable",
            "C. Coaxial cable",
            "D. Cat5e cable"
        ],
        "answer": "A. Direct Attach Copper (DAC)"
    },
    {
        "question": "Which type of cable is used for high-speed data transmission over short distances and is characterized by its low latency?",
        "options": [
            "A. Twinaxial cable",
            "B. Coaxial cable",
            "C. Fiber optic cable",
            "D. Ethernet cable"
        ],
        "answer": "A. Twinaxial cable"
    },
    {
        "question": "Which type of cable is used for both data transmission and television signals?",
        "options": [
            "A. Coaxial cable",
            "B. Fiber optic cable",
            "C. Direct Attach Copper (DAC)",
            "D. Ethernet cable"
        ],
        "answer": "A. Coaxial cable"
    },
    {
        "question": "Which of the following factors determines the maximum speed and distance of a network cable?",
        "options": [
            "A. Cable speed",
            "B. Cable color",
            "C. Cable length",
            "D. Cable price"
        ],
        "answer": "C. Cable length"
    },
    {
        "question": "Which type of cable is suitable for installation in air-handling spaces without the need for a fire-resistant jacket?",
        "options": [
            "A. Plenum cable",
            "B. Non-plenum cable",
            "C. Fiber optic cable",
            "D. Coaxial cable"
        ],
        "answer": "A. Plenum cable"
    },
    {
        "question": "Which of the following is the key difference between plenum and non-plenum cables?",
        "options": [
            "A. Plenum cables have a fire-resistant jacket, while non-plenum cables do not.",
            "B. Plenum cables are used for fiber optic networks.",
            "C. Non-plenum cables are typically used in long-distance communications.",
            "D. Non-plenum cables are fireproof."
        ],
        "answer": "A. Plenum cables have a fire-resistant jacket, while non-plenum cables do not."
    },
    {
        "question": "Which of the following transceivers is used for Ethernet network connections?",
        "options": [
            "A. Ethernet",
            "B. Fibre Channel (FC)",
            "C. SFP",
            "D. RJ45"
        ],
        "answer": "C. SFP"
    },
    {
        "question": "Which of the following is a transceiver standard designed to support high-speed data transmission over fiber optic cables?",
        "options": [
            "A. Fibre Channel (FC)",
            "B. Ethernet",
            "C. HDMI",
            "D. USB"
        ],
        "answer": "A. Fibre Channel (FC)"
    },
    {
        "question": "Which of the following is a small form-factor transceiver that is commonly used for short-distance connections in Ethernet networks?",
        "options": [
            "A. SFP",
            "B. QSFP",
            "C. RJ45",
            "D. Fiber optic"
        ],
        "answer": "A. SFP"
    },
    {
        "question": "Which transceiver supports higher data rates and larger numbers of channels compared to the SFP standard?",
        "options": [
            "A. QSFP",
            "B. SFP",
            "C. RJ45",
            "D. Fibre Channel"
        ],
        "answer": "A. QSFP"
    },
    {
        "question": "Which type of connector is used for single-mode and multimode fiber optic cables in a network?",
        "options": [
            "A. SC",
            "B. RJ45",
            "C. BNC",
            "D. F-type"
        ],
        "answer": "A. SC"
    },
    {
        "question": "Which connector is commonly used for high-density fiber optic networks and features a small size?",
        "options": [
            "A. LC",
            "B. SC",
            "C. RJ45",
            "D. F-type"
        ],
        "answer": "A. LC"
    },
    {
        "question": "Which type of fiber optic connector is commonly used in legacy networks and is characterized by its round, bayonet-style design?",
        "options": [
            "A. ST",
            "B. LC",
            "C. SC",
            "D. RJ45"
        ],
        "answer": "A. ST"
    },
    {
        "question": "Which of the following fiber optic connectors is designed for high-density environments and supports multiple fibers in a single connector?",
        "options": [
            "A. MPO",
            "B. SC",
            "C. LC",
            "D. RJ45"
        ],
        "answer": "A. MPO"
    },
    {
        "question": "Which of the following connectors is used for telephone and residential networks and supports low-speed data transfer?",
        "options": [
            "A. RJ11",
            "B. RJ45",
            "C. LC",
            "D. SC"
        ],
        "answer": "A. RJ11"
    },
    {
        "question": "Which connector is commonly used for Ethernet networking and supports higher data rates compared to RJ11?",
        "options": [
            "A. RJ45",
            "B. RJ11",
            "C. LC",
            "D. SC"
        ],
        "answer": "A. RJ45"
    },
    {
        "question": "Which type of connector is used for television and cable modem connections and operates over coaxial cables?",
        "options": [
            "A. F-type",
            "B. RJ45",
            "C. SC",
            "D. MPO"
        ],
        "answer": "A. F-type"
    },
    {
        "question": "Which protocol is used for transferring files in an unsecured manner over ports 20 and 21?",
        "options": [
            "A. FTP",
            "B. SFTP",
            "C. HTTPS",
            "D. SSH"
        ],
        "answer": "A. FTP"
    },
    {
        "question": "Which protocol provides secure file transfers over port 22?",
        "options": [
            "A. FTP",
            "B. SFTP",
            "C. HTTP",
            "D. Telnet"
        ],
        "answer": "B. SFTP"
    },
    {
        "question": "Which protocol is used for remote login and operates over port 22?",
        "options": [
            "A. SSH",
            "B. Telnet",
            "C. HTTP",
            "D. SMTP"
        ],
        "answer": "A. SSH"
    },
    {
        "question": "Which port is used by Telnet for remote communication?",
        "options": [
            "A. 23",
            "B. 22",
            "C. 25",
            "D. 80"
        ],
        "answer": "A. 23"
    },
    {
        "question": "Which protocol uses port 53 for translating domain names to IP addresses?",
        "options": [
            "A. DNS",
            "B. DHCP",
            "C. SMTP",
            "D. IMAP"
        ],
        "answer": "A. DNS"
    },
    {
        "question": "Which protocol operates on ports 67/68 for automatic IP address allocation?",
        "options": [
            "A. DHCP",
            "B. TFTP",
            "C. SMTP",
            "D. SNMP"
        ],
        "answer": "A. DHCP"
    },
    {
        "question": "Which protocol operates on port 69 and is used for simple file transfers with no authentication?",
        "options": [
            "A. TFTP",
            "B. FTP",
            "C. HTTP",
            "D. SSH"
        ],
        "answer": "A. TFTP"
    },
    {
        "question": "Which protocol operates over port 80 and is used for unencrypted web traffic?",
        "options": [
            "A. HTTP",
            "B. HTTPS",
            "C. SMTP",
            "D. FTP"
        ],
        "answer": "A. HTTP"
    },
    {
        "question": "Which protocol uses port 123 to synchronize the time across devices on a network?",
        "options": [
            "A. NTP",
            "B. SNMP",
            "C. SMTP",
            "D. DNS"
        ],
        "answer": "A. NTP"
    },
    {
        "question": "Which protocol uses port 161/162 for network monitoring and management?",
        "options": [
            "A. SNMP",
            "B. NTP",
            "C. FTP",
            "D. DHCP"
        ],
        "answer": "A. SNMP"
    },
    {
        "question": "Which protocol operates on port 389 to access and manage directory information?",
        "options": [
            "A. LDAP",
            "B. SNMP",
            "C. NTP",
            "D. IMAP"
        ],
        "answer": "A. LDAP"
    },
    {
        "question": "Which protocol is used to securely browse websites and operates over port 443?",
        "options": [
            "A. HTTPS",
            "B. HTTP",
            "C. SSH",
            "D. FTP"
        ],
        "answer": "A. HTTPS"
    },
    {
        "question": "Which protocol operates on port 445 for file sharing and printer access on Windows systems?",
        "options": [
            "A. SMB",
            "B. FTP",
            "C. HTTP",
            "D. POP3"
        ],
        "answer": "A. SMB"
    },
    {
        "question": "Which protocol uses port 514 for collecting and storing log data from devices?",
        "options": [
            "A. Syslog",
            "B. FTP",
            "C. DHCP",
            "D. SNMP"
        ],
        "answer": "A. Syslog"
    },
    {
        "question": "Which protocol uses port 587 to securely send email messages to a mail server?",
        "options": [
            "A. SMTPS",
            "B. SMTP",
            "C. IMAP",
            "D. FTP"
        ],
        "answer": "A. SMTPS"
    },
    {
        "question": "Which protocol uses port 636 for secure directory access over SSL?",
        "options": [
            "A. LDAPS",
            "B. LDAP",
            "C. DNS",
            "D. HTTP"
        ],
        "answer": "A. LDAPS"
    },
    {
        "question": "Which protocol is responsible for error reporting and diagnostics and operates with ICMP?",
        "options": [
            "A. ICMP",
            "B. TCP",
            "C. UDP",
            "D. GRE"
        ],
        "answer": "A. ICMP"
    },
    {
        "question": "Which of the following protocols is used for reliable, connection-oriented data transfer?",
        "options": [
            "A. TCP",
            "B. UDP",
            "C. ICMP",
            "D. GRE"
        ],
        "answer": "A. TCP"
    },
    {
        "question": "Which of the following protocols is used for fast, connectionless data transfer?",
        "options": [
            "A. UDP",
            "B. TCP",
            "C. ICMP",
            "D. GRE"
        ],
        "answer": "A. UDP"
    },
    {
        "question": "Which protocol uses port 3389 to provide a remote desktop interface?",
        "options": [
            "A. RDP",
            "B. SSH",
            "C. HTTP",
            "D. Telnet"
        ],
        "answer": "A. RDP"
    },
    {
        "question": "Which protocol uses port 5060/5061 for initiating and managing VoIP calls?",
        "options": [
            "A. SIP",
            "B. HTTP",
            "C. DNS",
            "D. NTP"
        ],
        "answer": "A. SIP"
    },
    {
        "question": "Which type of traffic sends data from one source to a single destination?",
        "options": [
            "A. Unicast",
            "B. Multicast",
            "C. Broadcast",
            "D. Anycast"
        ],
        "answer": "A. Unicast"
    },
    {
        "question": "Which traffic type is used for sending data to the nearest of several potential recipients?",
        "options": [
            "A. Anycast",
            "B. Unicast",
            "C. Multicast",
            "D. Broadcast"
        ],
        "answer": "A. Anycast"
    },
    {
        "question": "Which type of traffic sends data to all devices on a network?",
        "options": [
            "A. Broadcast",
            "B. Unicast",
            "C. Anycast",
            "D. Multicast"
        ],
        "answer": "A. Broadcast"
    },
    {
        "question": "Which of the following protocols uses port 1433 for database communication?",
        "options": [
            "A. SQL Server",
            "B. HTTP",
            "C. FTP",
            "D. SMTP"
        ],
        "answer": "A. SQL Server"
    },
    {
        "question": "Which protocol is used for secure remote login and operates over port 22?",
        "options": [
            "A. Telnet",
            "B. SSH",
            "C. FTP",
            "D. HTTP"
        ],
        "answer": "B. SSH"
    },
    {
        "question": "Which protocol uses port 25 for sending email from a mail client to a mail server?",
        "options": [
            "A. SMTP",
            "B. SMTPS",
            "C. POP3",
            "D. IMAP"
        ],
        "answer": "A. SMTP"
    },
    {
        "question": "Which port does HTTPS use for secure web browsing?",
        "options": [
            "A. 80",
            "B. 443",
            "C. 21",
            "D. 22"
        ],
        "answer": "B. 443"
    },
    {
        "question": "Which protocol uses port 23 for providing unencrypted remote login to a system?",
        "options": [
            "A. Telnet",
            "B. SSH",
            "C. HTTP",
            "D. FTP"
        ],
        "answer": "A. Telnet"
    },
    {
        "question": "Which protocol provides time synchronization for devices on a network and operates on port 123?",
        "options": [
            "A. NTP",
            "B. SNMP",
            "C. SMTP",
            "D. DNS"
        ],
        "answer": "A. NTP"
    },
    {
        "question": "Which protocol operates on port 161 and is used to manage and monitor network devices?",
        "options": [
            "A. SNMP",
            "B. NTP",
            "C. FTP",
            "D. DNS"
        ],
        "answer": "A. SNMP"
    },
    {
        "question": "Which of the following is used by network devices to exchange routing information and operates on port 520?",
        "options": [
            "A. RIP",
            "B. OSPF",
            "C. EIGRP",
            "D. BGP"
        ],
        "answer": "A. RIP"
    },
    {
        "question": "Which of the following protocols uses port 5060 for voice communications in a VoIP network?",
        "options": [
            "A. SIP",
            "B. RTP",
            "C. H.323",
            "D. HTTP"
        ],
        "answer": "A. SIP"
    },
    {
        "question": "Which protocol uses port 53 to translate domain names into IP addresses?",
        "options": [
            "A. DNS",
            "B. HTTP",
            "C. SMTP",
            "D. POP3"
        ],
        "answer": "A. DNS"
    },
    {
        "question": "Which of the following protocols is used for transferring files securely over a network using port 22?",
        "options": [
            "A. SFTP",
            "B. FTP",
            "C. HTTP",
            "D. SSH"
        ],
        "answer": "A. SFTP"
    },
    {
        "question": "Which protocol operates on port 445 for file sharing on a Windows network?",
        "options": [
            "A. SMB",
            "B. FTP",
            "C. HTTP",
            "D. POP3"
        ],
        "answer": "A. SMB"
    },
    {
        "question": "Which protocol uses port 3389 to allow remote desktop access to a computer?",
        "options": [
            "A. RDP",
            "B. SSH",
            "C. FTP",
            "D. Telnet"
        ],
        "answer": "A. RDP"
    },
    {
        "question": "Which traffic type is used to send data from one source to multiple specific destinations?",
        "options": [
            "A. Unicast",
            "B. Multicast",
            "C. Broadcast",
            "D. Anycast"
        ],
        "answer": "B. Multicast"
    },
    {
        "question": "Which traffic type allows data to be sent from a single source to multiple recipients across a network?",
        "options": [
            "A. Unicast",
            "B. Multicast",
            "C. Anycast",
            "D. Broadcast"
        ],
        "answer": "B. Multicast"
    },
    {
        "question": "Which of the following traffic types is used to send data to the nearest destination from multiple receivers?",
        "options": [
            "A. Unicast",
            "B. Multicast",
            "C. Anycast",
            "D. Broadcast"
        ],
        "answer": "C. Anycast"
    },
    {
        "question": "Which protocol operates on port 1433 to provide database communication for SQL Server?",
        "options": [
            "A. SQL Server",
            "B. HTTP",
            "C. FTP",
            "D. DNS"
        ],
        "answer": "A. SQL Server"
    },
    {
        "question": "What is the primary purpose of the Internet Control Message Protocol (ICMP)?",
        "options": [
            "A. Routing information",
            "B. Error reporting and diagnostics",
            "C. Secure communications",
            "D. File transfers"
        ],
        "answer": "B. Error reporting and diagnostics"
    },
    {
        "question": "Which port is used by the File Transfer Protocol (FTP) for data transfer?",
        "options": [
            "A. 20",
            "B. 21",
            "C. 22",
            "D. 23"
        ],
        "answer": "A. 20"
    },
    {
        "question": "Which protocol uses port 22 for secure remote access to a system?",
        "options": [
            "A. SSH",
            "B. Telnet",
            "C. SMTP",
            "D. FTP"
        ],
        "answer": "A. SSH"
    },
    {
        "question": "Which protocol is used for sending email from a client to a mail server?",
        "options": [
            "A. SMTP",
            "B. POP3",
            "C. IMAP",
            "D. SFTP"
        ],
        "answer": "A. SMTP"
    },
    {
        "question": "Which protocol uses port 53 for resolving domain names into IP addresses?",
        "options": [
            "A. HTTP",
            "B. FTP",
            "C. DNS",
            "D. SNMP"
        ],
        "answer": "C. DNS"
    },
    {
        "question": "Which protocol uses port 443 to secure web traffic?",
        "options": [
            "A. HTTP",
            "B. HTTPS",
            "C. FTP",
            "D. SFTP"
        ],
        "answer": "B. HTTPS"
    },
    {
        "question": "Which protocol uses port 67/68 for dynamically assigning IP addresses to devices in a network?",
        "options": [
            "A. DHCP",
            "B. DNS",
            "C. SMTP",
            "D. NTP"
        ],
        "answer": "A. DHCP"
    },
    {
        "question": "What does the Trivial File Transfer Protocol (TFTP) use for data transfer?",
        "options": [
            "A. Port 69",
            "B. Port 80",
            "C. Port 23",
            "D. Port 443"
        ],
        "answer": "A. Port 69"
    },
    {
        "question": "Which protocol operates over port 161/162 for managing and monitoring network devices?",
        "options": [
            "A. SNMP",
            "B. DNS",
            "C. FTP",
            "D. SMTP"
        ],
        "answer": "A. SNMP"
    },
    {
        "question": "Which of the following protocols provides secure email transfer using port 587?",
        "options": [
            "A. SMTP",
            "B. SMTPS",
            "C. HTTPS",
            "D. POP3"
        ],
        "answer": "B. SMTPS"
    },
    {
        "question": "Which protocol uses port 389 for accessing directory services?",
        "options": [
            "A. LDAP",
            "B. SNMP",
            "C. HTTPS",
            "D. SMTP"
        ],
        "answer": "A. LDAP"
    },
    {
        "question": "Which protocol uses port 3389 for remote desktop access?",
        "options": [
            "A. RDP",
            "B. Telnet",
            "C. SSH",
            "D. FTP"
        ],
        "answer": "A. RDP"
    },
    {
        "question": "Which of the following protocols allows secure communications over an insecure network using encryption, authentication, and integrity?",
        "options": [
            "A. IPSec",
            "B. SSH",
            "C. HTTP",
            "D. FTP"
        ],
        "answer": "A. IPSec"
    },
    {
        "question": "Which of the following is used to encapsulate data within another protocol to provide security in a VPN?",
        "options": [
            "A. ESP",
            "B. AH",
            "C. GRE",
            "D. IKE"
        ],
        "answer": "A. ESP"
    },
    {
        "question": "Which of the following is used to authenticate and establish keys for secure communications in IPSec?",
        "options": [
            "A. IKE",
            "B. AH",
            "C. ESP",
            "D. GRE"
        ],
        "answer": "A. IKE"
    },
    {
        "question": "Which of the following is a broadcast traffic type that sends data to all devices on a network?",
        "options": [
            "A. Unicast",
            "B. Multicast",
            "C. Anycast",
            "D. Broadcast"
        ],
        "answer": "D. Broadcast"
    },
    {
        "question": "Which of the following traffic types sends data to a single destination device?",
        "options": [
            "A. Unicast",
            "B. Multicast",
            "C. Anycast",
            "D. Broadcast"
        ],
        "answer": "A. Unicast"
    },
    {
        "question": "Which of the following traffic types allows data to be sent to multiple specific recipients, but not to all devices on the network?",
        "options": [
            "A. Unicast",
            "B. Multicast",
            "C. Broadcast",
            "D. Anycast"
        ],
        "answer": "B. Multicast"
    },
    {
        "question": "A company wants to minimize latency between its on-premises data center and the cloud provider. Which cloud connectivity option should they use?",
        "options": [
            "A. VPN",
            "B. Direct Connect",
            "C. Internet Gateway",
            "D. NAT Gateway"
        ],
        "answer": "B. Direct Connect"
    },
    {
        "question": "Which cloud deployment model allows multiple organizations to share cloud resources while maintaining some level of separation?",
        "options": [
            "A. Public Cloud",
            "B. Private Cloud",
            "C. Hybrid Cloud",
            "D. Community Cloud"
        ],
        "answer": "D. Community Cloud"
    },
    {
        "question": "Which cloud security mechanism is best suited for filtering and controlling traffic at the network perimeter?",
        "options": [
            "A. Network Security Groups",
            "B. Network Security Lists",
            "C. Role-Based Access Control (RBAC)",
            "D. Internet Gateway"
        ],
        "answer": "B. Network Security Groups"
    },
    {
        "question": "A company is running a web application that requires consistent performance even under heavy load. Which cloud function should they use?",
        "options": [
            "A. VPN",
            "B. Load Balancer",
            "C. NAT Gateway",
            "D. Direct Connect"
        ],
        "answer": "B. Load Balancer"
    },
    {
        "question": "Which cloud computing characteristic ensures that multiple users can share the same physical infrastructure while keeping their data separate?",
        "options": [
            "A. Scalability",
            "B. Elasticity",
            "C. Multitenancy",
            "D. NFV"
        ],
        "answer": "C. Multitenancy"
    },
    {
        "question": "Which cloud model provides full software applications hosted and managed by the cloud provider?",
        "options": [
            "A. SaaS",
            "B. PaaS",
            "C. IaaS",
            "D. Private Cloud"
        ],
        "answer": "A. SaaS"
    },
    {
        "question": "A company needs to improve its cloud security by restricting unauthorized outbound traffic from its cloud instances. What should they implement?",
        "options": [
            "A. Internet Gateway",
            "B. Network Security Groups",
            "C. VPN",
            "D. Direct Connect"
        ],
        "answer": "B. Network Security Groups"
    },
    {
        "question": "Which cloud concept allows IT administrators to dynamically allocate additional resources based on workload demand?",
        "options": [
            "A. Scalability",
            "B. Elasticity",
            "C. Multitenancy",
            "D. NFV"
        ],
        "answer": "B. Elasticity"
    },
    {
        "question": "A company is moving its infrastructure to the cloud but wants to maintain direct control over its networking and security policies. Which cloud deployment model should they choose?",
        "options": [
            "A. Public Cloud",
            "B. Private Cloud",
            "C. Hybrid Cloud",
            "D. Community Cloud"
        ],
        "answer": "B. Private Cloud"
    },
    {
        "question": "Which cloud gateway allows cloud resources to communicate securely with the public internet?",
        "options": [
            "A. VPN",
            "B. NAT Gateway",
            "C. Internet Gateway",
            "D. Direct Connect"
        ],
        "answer": "C. Internet Gateway"
    },
    {
        "question": "Which cloud feature ensures that an application remains available by automatically scaling resources up or down as needed?",
        "options": [
            "A. Scalability",
            "B. Elasticity",
            "C. Multitenancy",
            "D. NFV"
        ],
        "answer": "B. Elasticity"
    },
    {
        "question": "A company wants to ensure that only authorized users can access its cloud-based applications. Which security measure should they implement?",
        "options": [
            "A. Role-Based Access Control (RBAC)",
            "B. Internet Gateway",
            "C. Direct Connect",
            "D. NAT Gateway"
        ],
        "answer": "A. Role-Based Access Control (RBAC)"
    },
    {
        "question": "Which cloud service model provides a fully managed platform for developers to build, run, and manage applications without managing infrastructure?",
        "options": [
            "A. SaaS",
            "B. PaaS",
            "C. IaaS",
            "D. Private Cloud"
        ],
        "answer": "B. PaaS"
    },
    {
        "question": "An organization is expanding globally and needs to reduce latency for users in different regions. What cloud solution should they use?",
        "options": [
            "A. VPN",
            "B. Content Delivery Network (CDN)",
            "C. Direct Connect",
            "D. Internet Gateway"
        ],
        "answer": "B. Content Delivery Network (CDN)"
    },
    {
        "question": "A company wants to optimize cost and flexibility by combining private cloud infrastructure with public cloud services. What cloud deployment model should they use?",
        "options": [
            "A. Public Cloud",
            "B. Private Cloud",
            "C. Hybrid Cloud",
            "D. Multitenancy"
        ],
        "answer": "C. Hybrid Cloud"
    },
    {
        "question": "A company needs to create isolated network environments for different departments within the same cloud account. What should they use?",
        "options": [
            "A. Virtual Private Cloud (VPC)",
            "B. Direct Connect",
            "C. Internet Gateway",
            "D. NAT Gateway"
        ],
        "answer": "A. Virtual Private Cloud (VPC)"
    },
    {
        "question": "Which cloud security feature acts as a virtual firewall to control inbound and outbound traffic at the instance level?",
        "options": [
            "A. Network Security Groups",
            "B. Network Security Lists",
            "C. VPN",
            "D. Direct Connect"
        ],
        "answer": "A. Network Security Groups"
    },
    {
        "question": "An organization is migrating its legacy application to a cloud platform where it still maintains control over the OS and storage. Which cloud service model should they use?",
        "options": [
            "A. SaaS",
            "B. IaaS",
            "C. PaaS",
            "D. Hybrid Cloud"
        ],
        "answer": "B. IaaS"
    },
    {
        "question": "Which cloud connectivity option allows on-premises data centers to establish a dedicated, high-speed connection to a cloud provider?",
        "options": [
            "A. VPN",
            "B. Direct Connect",
            "C. Internet Gateway",
            "D. NAT Gateway"
        ],
        "answer": "B. Direct Connect"
    },
    {
        "question": "A company hosts a critical database in the cloud and wants to prevent direct internet access while allowing internal cloud services to communicate with it. What should they use?",
        "options": [
            "A. Internet Gateway",
            "B. NAT Gateway",
            "C. VPC with Private Subnet",
            "D. Direct Connect"
        ],
        "answer": "C. VPC with Private Subnet"
    },
    {
        "question": "Which cloud model allows organizations to use both on-premises resources and cloud services for different workloads?",
        "options": [
            "A. Public Cloud",
            "B. Private Cloud",
            "C. Hybrid Cloud",
            "D. SaaS"
        ],
        "answer": "C. Hybrid Cloud"
    },
    {
        "question": "What is the key benefit of using a Network Functions Virtualization (NFV) solution in a cloud environment?",
        "options": [
            "A. Reduces hardware dependency",
            "B. Increases physical appliance deployment",
            "C. Requires direct internet access",
            "D. Eliminates the need for VPCs"
        ],
        "answer": "A. Reduces hardware dependency"
    },
    {
        "question": "Which cloud security component allows administrators to create rules that restrict inbound and outbound traffic at the subnet level?",
        "options": [
            "A. Network Security Groups",
            "B. Network Security Lists",
            "C. VPN",
            "D. Elastic Load Balancer"
        ],
        "answer": "A. Network Security Groups"
    },
    {
        "question": "A company is deploying a cloud-based web application that needs to automatically scale during peak usage periods. Which cloud characteristic enables this?",
        "options": [
            "A. Scalability",
            "B. Elasticity",
            "C. Multitenancy",
            "D. Direct Connect"
        ],
        "answer": "B. Elasticity"
    },
    {
        "question": "Which cloud deployment model is fully owned and maintained by a single organization, typically hosted on-premises?",
        "options": [
            "A. Private Cloud",
            "B. Public Cloud",
            "C. Hybrid Cloud",
            "D. Community Cloud"
        ],
        "answer": "A. Private Cloud"
    },
    {
        "question": "A company wants to enable secure communication between remote employees and the corporate cloud environment. Which solution should they use?",
        "options": [
            "A. VPN",
            "B. Direct Connect",
            "C. Internet Gateway",
            "D. NAT Gateway"
        ],
        "answer": "A. VPN"
    },
    {
        "question": "A startup is using a cloud service where they can only configure applications but do not manage the underlying infrastructure. Which cloud service model is this?",
        "options": [
            "A. SaaS",
            "B. PaaS",
            "C. IaaS",
            "D. Hybrid Cloud"
        ],
        "answer": "B. PaaS"
    },
    {
        "question": "Which term describes the cloud’s ability to handle an increasing workload by provisioning more resources as needed?",
        "options": [
            "A. Elasticity",
            "B. Scalability",
            "C. Multitenancy",
            "D. NFV"
        ],
        "answer": "B. Scalability"
    },
    {
        "question": "A company needs to connect multiple branch offices to their cloud infrastructure securely over the public internet. What is the best solution?",
        "options": [
            "A. Direct Connect",
            "B. VPN",
            "C. Internet Gateway",
            "D. Network Security Groups"
        ],
        "answer": "B. VPN"
    },
    {
        "question": "A retail company needs to ensure that multiple customers can use its cloud-based e-commerce platform while maintaining security and data separation. What cloud concept enables this?",
        "options": [
            "A. Multitenancy",
            "B. Scalability",
            "C. Elasticity",
            "D. NFV"
        ],
        "answer": "A. Multitenancy"
    },
    {
        "question": "A company wants to allow outbound internet traffic from its cloud instances without exposing them to direct inbound traffic. What should they implement?",
        "options": [
            "A. Internet Gateway",
            "B. NAT Gateway",
            "C. Direct Connect",
            "D. Network Security Groups"
        ],
        "answer": "B. NAT Gateway"
    },
    {
        "question": "Which cloud security mechanism is best for controlling access to cloud resources based on user identity and role?",
        "options": [
            "A. VPN",
            "B. Role-Based Access Control (RBAC)",
            "C. Direct Connect",
            "D. NAT Gateway"
        ],
        "answer": "B. Role-Based Access Control (RBAC)"
    },
    {
        "question": "Which cloud component allows users to access cloud services over the internet without requiring a dedicated connection?",
        "options": [
            "A. VPN",
            "B. Internet Gateway",
            "C. NAT Gateway",
            "D. VPC"
        ],
        "answer": "B. Internet Gateway"
    },
    {
        "question": "Which cloud feature allows businesses to avoid over-provisioning by automatically adding or removing resources based on demand?",
        "options": [
            "A. Scalability",
            "B. Elasticity",
            "C. Multitenancy",
            "D. NFV"
        ],
        "answer": "B. Elasticity"
    },
    {
        "question": "Which cloud service model provides users with a fully managed application, eliminating the need to manage the underlying infrastructure?",
        "options": [
            "A. Infrastructure as a Service (IaaS)",
            "B. Platform as a Service (PaaS)",
            "C. Software as a Service (SaaS)",
            "D. Virtual Private Cloud (VPC)"
        ],
        "answer": "C. Software as a Service (SaaS)"
    },
    {
        "question": "A company wants to host a web application without managing physical servers but still have control over the virtual machines. Which cloud service model is the best choice?",
        "options": [
            "A. SaaS",
            "B. IaaS",
            "C. PaaS",
            "D. VPN"
        ],
        "answer": "B. IaaS"
    },
    {
        "question": "Which cloud deployment model provides dedicated resources for a single organization but is hosted by a third-party provider?",
        "options": [
            "A. Public Cloud",
            "B. Private Cloud",
            "C. Hybrid Cloud",
            "D. Community Cloud"
        ],
        "answer": "B. Private Cloud"
    },
    {
        "question": "A company wants to improve connectivity between its on-premises data center and cloud environment with a low-latency, high-bandwidth connection. Which solution should they choose?",
        "options": [
            "A. VPN",
            "B. Direct Connect",
            "C. NAT Gateway",
            "D. CDN"
        ],
        "answer": "B. Direct Connect"
    },
    {
        "question": "Which of the following allows organizations to scale resources dynamically based on real-time demand?",
        "options": [
            "A. Elasticity",
            "B. Scalability",
            "C. Multitenancy",
            "D. Virtualization"
        ],
        "answer": "A. Elasticity"
    },
    {
        "question": "A company needs to allow only specific IP ranges to access their cloud-based servers. Which cloud security feature should they configure?",
        "options": [
            "A. Network Security Groups",
            "B. Cloud Gateway",
            "C. Multitenancy",
            "D. Direct Connect"
        ],
        "answer": "A. Network Security Groups"
    },
    {
        "question": "Which cloud connectivity option uses the public internet to establish a secure tunnel between a remote network and a cloud environment?",
        "options": [
            "A. Direct Connect",
            "B. VPN",
            "C. Internet Gateway",
            "D. NAT Gateway"
        ],
        "answer": "B. VPN"
    },
    {
        "question": "Which cloud service model provides a preconfigured environment for developers to build, test, and deploy applications without managing infrastructure?",
        "options": [
            "A. SaaS",
            "B. IaaS",
            "C. PaaS",
            "D. VPC"
        ],
        "answer": "C. PaaS"
    },
    {
        "question": "A company wants to restrict outbound internet access from certain virtual machines in a VPC. What should they use?",
        "options": [
            "A. NAT Gateway",
            "B. Internet Gateway",
            "C. Network Security Lists",
            "D. VPN"
        ],
        "answer": "C. Network Security Lists"
    },
    {
        "question": "What is the primary function of a NAT Gateway in a cloud environment?",
        "options": [
            "A. Provides a dedicated connection to the cloud provider",
            "B. Translates private IP addresses to public IPs for outbound traffic",
            "C. Filters inbound traffic based on security rules",
            "D. Distributes traffic among multiple servers"
        ],
        "answer": "B. Translates private IP addresses to public IPs for outbound traffic"
    },
    {
        "question": "Which cloud computing characteristic ensures that multiple customers can share the same infrastructure securely?",
        "options": [
            "A. Scalability",
            "B. Elasticity",
            "C. Multitenancy",
            "D. Direct Connect"
        ],
        "answer": "C. Multitenancy"
    },
    {
        "question": "A business wants to combine both private and public cloud resources to optimize cost and security. Which deployment model should they use?",
        "options": [
            "A. Private Cloud",
            "B. Public Cloud",
            "C. Hybrid Cloud",
            "D. Community Cloud"
        ],
        "answer": "C. Hybrid Cloud"
    },
    {
        "question": "Which cloud security feature allows administrators to define access control policies based on IP ranges and security rules?",
        "options": [
            "A. Network Security Groups",
            "B. Multitenancy",
            "C. NAT Gateway",
            "D. Internet Gateway"
        ],
        "answer": "A. Network Security Groups"
    },
    {
        "question": "Which cloud service model is best suited for a company that wants a provider to handle infrastructure and runtime while allowing custom application deployment?",
        "options": [
            "A. IaaS",
            "B. PaaS",
            "C. SaaS",
            "D. Direct Connect"
        ],
        "answer": "B. PaaS"
    },
    {
        "question": "A company needs a cloud networking feature that provides a dedicated IP address for internet-facing resources. What should they use?",
        "options": [
            "A. Internet Gateway",
            "B. NAT Gateway",
            "C. VPN",
            "D. Direct Connect"
        ],
        "answer": "A. Internet Gateway"
    },
    {
        "question": "Which feature enables virtualized network functions such as firewalls and load balancers to be deployed in a cloud environment?",
        "options": [
            "A. Virtual Private Cloud (VPC)",
            "B. Network Functions Virtualization (NFV)",
            "C. Multitenancy",
            "D. Internet Gateway"
        ],
        "answer": "B. Network Functions Virtualization (NFV)"
    },
    {
        "question": "Which term describes the ability to increase computing resources as demand grows, but does not reduce them automatically?",
        "options": [
            "A. Elasticity",
            "B. Scalability",
            "C. Multitenancy",
            "D. NFV"
        ],
        "answer": "B. Scalability"
    },
    {
        "question": "A company wants to host a website on a cloud platform where they do not have to worry about infrastructure maintenance. Which cloud model is most appropriate?",
        "options": [
            "A. SaaS",
            "B. IaaS",
            "C. PaaS",
            "D. Private Cloud"
        ],
        "answer": "A. SaaS"
    },
    {
        "question": "Which of the following is NOT a cloud deployment model?",
        "options": [
            "A. Private",
            "B. Hybrid",
            "C. Public",
            "D. Local"
        ],
        "answer": "D. Local"
    },
    {
        "question": "Which cloud security mechanism provides fine-grained access control at the subnet level within a VPC?",
        "options": [
            "A. Security Groups",
            "B. Network Security Lists",
            "C. VPN",
            "D. Direct Connect"
        ],
        "answer": "B. Network Security Lists"
    },
    {
        "question": "What is the primary benefit of using a cloud-based VPN over a direct connection?",
        "options": [
            "A. Lower latency",
            "B. More stable connection",
            "C. Cost-effectiveness and ease of deployment",
            "D. Guaranteed bandwidth"
        ],
        "answer": "C. Cost-effectiveness and ease of deployment"
    },
    {
        "question": "A security team wants to inspect encrypted traffic for threats before it reaches internal servers. Which device is best suited for this function?",
        "options": [
            "A. Proxy server",
            "B. Firewall",
            "C. Load balancer",
            "D. VPN concentrator"
        ],
        "answer": "A. Proxy server"
    },
    {
        "question": "Which network device operates primarily at Layer 2 and is responsible for forwarding frames based on MAC addresses?",
        "options": [
            "A. Router",
            "B. Firewall",
            "C. Switch",
            "D. Load balancer"
        ],
        "answer": "C. Switch"
    },
    {
        "question": "A company experiences frequent Distributed Denial of Service (DDoS) attacks. Which device can help mitigate these attacks by distributing incoming traffic?",
        "options": [
            "A. Intrusion Prevention System (IPS)",
            "B. Load balancer",
            "C. Firewall",
            "D. Wireless controller"
        ],
        "answer": "B. Load balancer"
    },
    {
        "question": "Which storage solution is most suitable for an organization that requires low-latency, block-level access for high-performance applications?",
        "options": [
            "A. Network-attached storage (NAS)",
            "B. Storage area network (SAN)",
            "C. Content delivery network (CDN)",
            "D. Cloud-based storage"
        ],
        "answer": "B. Storage area network (SAN)"
    },
    {
        "question": "A company needs to restrict internal employees from accessing specific categories of websites. Which solution should they implement?",
        "options": [
            "A. Firewall",
            "B. Proxy server",
            "C. VPN",
            "D. IDS"
        ],
        "answer": "B. Proxy server"
    },
    {
        "question": "Which networking function is responsible for ensuring packets follow the most efficient path through a network?",
        "options": [
            "A. QoS",
            "B. TTL",
            "C. Routing",
            "D. VPN"
        ],
        "answer": "C. Routing"
    },
    {
        "question": "Which device is responsible for managing multiple VPN connections and ensuring secure remote access for users?",
        "options": [
            "A. Firewall",
            "B. Load balancer",
            "C. VPN concentrator",
            "D. IDS"
        ],
        "answer": "C. VPN concentrator"
    },
    {
        "question": "Which device can actively block malicious traffic before it enters the network?",
        "options": [
            "A. Intrusion Detection System (IDS)",
            "B. Intrusion Prevention System (IPS)",
            "C. Load balancer",
            "D. NAS"
        ],
        "answer": "B. Intrusion Prevention System (IPS)"
    },
    {
        "question": "A company needs to ensure employees working remotely can securely access internal company resources. What is the best solution?",
        "options": [
            "A. VPN",
            "B. IDS",
            "C. Load balancer",
            "D. Wireless AP"
        ],
        "answer": "A. VPN"
    },
    {
        "question": "Which type of network appliance is designed to optimize the distribution of media content such as videos and web pages across multiple locations?",
        "options": [
            "A. Load balancer",
            "B. Content delivery network (CDN)",
            "C. Proxy server",
            "D. VPN concentrator"
        ],
        "answer": "B. Content delivery network (CDN)"
    },
    {
        "question": "An organization wants to monitor and analyze network traffic for suspicious activity but does not want to actively block traffic. Which solution should they use?",
        "options": [
            "A. Firewall",
            "B. Intrusion Detection System (IDS)",
            "C. Intrusion Prevention System (IPS)",
            "D. Load balancer"
        ],
        "answer": "B. Intrusion Detection System (IDS)"
    },
    {
        "question": "Which appliance is used to divide network traffic among multiple backend servers to improve performance and redundancy?",
        "options": [
            "A. Router",
            "B. Load balancer",
            "C. Proxy server",
            "D. Firewall"
        ],
        "answer": "B. Load balancer"
    },
    {
        "question": "A company wants to enforce bandwidth limitations on specific applications to ensure business-critical applications get priority. What should they configure?",
        "options": [
            "A. Firewall rules",
            "B. Quality of Service (QoS)",
            "C. Virtual LAN (VLAN)",
            "D. Load balancing"
        ],
        "answer": "B. Quality of Service (QoS)"
    },
    {
        "question": "Which network appliance allows multiple wireless access points to be managed centrally, ensuring consistent configuration and performance?",
        "options": [
            "A. Router",
            "B. Firewall",
            "C. Wireless controller",
            "D. Proxy server"
        ],
        "answer": "C. Wireless controller"
    },
    {
        "question": "A network administrator is troubleshooting a problem where packets are being discarded due to excessive hops. Which networking function should they examine?",
        "options": [
            "A. VPN",
            "B. TTL (Time to Live)",
            "C. QoS",
            "D. IDS"
        ],
        "answer": "B. TTL (Time to Live)"
    },
    {
        "question": "A company implements a content delivery network (CDN) to improve website performance. What is the primary benefit of using a CDN?",
        "options": [
            "A. Reducing latency by caching content closer to users",
            "B. Encrypting network traffic",
            "C. Blocking unauthorized access",
            "D. Assigning IP addresses dynamically"
        ],
        "answer": "A. Reducing latency by caching content closer to users"
    },
    {
        "question": "Which device would be the best choice to connect multiple VLANs in an enterprise network?",
        "options": [
            "A. Switch",
            "B. Router",
            "C. Load balancer",
            "D. Proxy server"
        ],
        "answer": "B. Router"
    },
    {
        "question": "A company wants to balance traffic between multiple servers to ensure high availability. Which type of appliance should they use?",
        "options": [
            "A. Firewall",
            "B. Load balancer",
            "C. IDS",
            "D. NAS"
        ],
        "answer": "B. Load balancer"
    },
    {
        "question": "An enterprise network administrator needs to allow employees to access corporate resources securely over the internet. Which solution should be used?",
        "options": [
            "A. IDS",
            "B. VPN",
            "C. Load balancer",
            "D. Proxy"
        ],
        "answer": "B. VPN"
    },
    {
        "question": "Which appliance provides centralized management of multiple wireless access points (APs)?",
        "options": [
            "A. Router",
            "B. Firewall",
            "C. Wireless Controller",
            "D. Load balancer"
        ],
        "answer": "C. Wireless Controller"
    },
    {
        "question": "A network administrator needs to prevent unauthorized access to a company’s internal resources while allowing external access to public services. Which solution should they implement?",
        "options": [
            "A. Firewall",
            "B. IDS",
            "C. Load balancer",
            "D. VPN"
        ],
        "answer": "A. Firewall"
    },
    {
        "question": "Which storage solution provides file-level access over a network and is commonly used for centralized file sharing?",
        "options": [
            "A. SAN",
            "B. NAS",
            "C. IDS",
            "D. Proxy server"
        ],
        "answer": "B. NAS"
    },
    {
        "question": "A company has deployed an IPS. What is the primary function of an Intrusion Prevention System?",
        "options": [
            "A. To detect and log malicious activity",
            "B. To actively block or mitigate threats",
            "C. To distribute network traffic",
            "D. To provide secure remote access"
        ],
        "answer": "B. To actively block or mitigate threats"
    },
    {
        "question": "Which of the following is a key characteristic of a SAN (Storage Area Network)?",
        "options": [
            "A. Provides block-level storage",
            "B. Uses Ethernet for connectivity",
            "C. Stores data in cloud storage",
            "D. Only supports file-based access"
        ],
        "answer": "A. Provides block-level storage"
    },
    {
        "question": "A network technician needs to prevent certain types of network traffic from leaving the internal network. Which device should they configure?",
        "options": [
            "A. Firewall",
            "B. Load balancer",
            "C. NAS",
            "D. Wireless AP"
        ],
        "answer": "A. Firewall"
    },
    {
        "question": "What is the primary role of a proxy server in a corporate network?",
        "options": [
            "A. Blocking incoming attacks",
            "B. Caching and filtering web requests",
            "C. Encrypting all network traffic",
            "D. Assigning IP addresses"
        ],
        "answer": "B. Caching and filtering web requests"
    },
    {
        "question": "A company needs to ensure that video conferencing traffic receives higher priority over regular internet browsing. Which technology should they implement?",
        "options": [
            "A. VPN",
            "B. QoS",
            "C. IDS",
            "D. CDN"
        ],
        "answer": "B. QoS"
    },
    {
        "question": "Which of the following devices can be both physical and virtual, and is responsible for managing network traffic between different networks?",
        "options": [
            "A. Load balancer",
            "B. Switch",
            "C. Router",
            "D. NAS"
        ],
        "answer": "C. Router"
    },
    {
        "question": "A company is deploying multiple wireless access points throughout a building. Which device should they use to centrally manage them?",
        "options": [
            "A. Firewall",
            "B. Wireless controller",
            "C. Load balancer",
            "D. IDS"
        ],
        "answer": "B. Wireless controller"
    },
    {
        "question": "Which networking function ensures that packets are not stuck in infinite loops by limiting the number of hops a packet can take?",
        "options": [
            "A. VPN",
            "B. TTL (Time to Live)",
            "C. QoS",
            "D. IDS"
        ],
        "answer": "B. TTL (Time to Live)"
    },
    {
        "question": "A company needs to extend its network to provide internet access to remote areas where running Ethernet cables is not feasible. Which technology should they use?",
        "options": [
            "A. VPN",
            "B. IDS",
            "C. Wireless Access Point (AP)",
            "D. Load balancer"
        ],
        "answer": "C. Wireless Access Point (AP)"
    },
    {
        "question": "Which network device inspects traffic in real time and can actively block malicious packets?",
        "options": [
            "A. IDS",
            "B. IPS",
            "C. Proxy",
            "D. Router"
        ],
        "answer": "B. IPS"
    },
    {
        "question": "An administrator configures a VPN for remote employees. What is the primary benefit of this setup?",
        "options": [
            "A. It increases network bandwidth",
            "B. It provides secure remote access to internal resources",
            "C. It reduces the need for firewalls",
            "D. It replaces the need for load balancers"
        ],
        "answer": "B. It provides secure remote access to internal resources"
    },
    {
        "question": "A network technician needs to prevent broadcast storms on a large corporate network. Which device should they configure?",
        "options": [
            "A. Router",
            "B. Switch",
            "C. Proxy",
            "D. Firewall"
        ],
        "answer": "B. Switch"
    },
    {
        "question": "Which appliance is responsible for redirecting web requests and caching frequently accessed content to improve performance?",
        "options": [
            "A. Firewall",
            "B. Proxy server",
            "C. IDS",
            "D. NAS"
        ],
        "answer": "B. Proxy server"
    },
    {
        "question": "A security administrator wants to log all network traffic for analysis but does not want to block any traffic. Which device should they use?",
        "options": [
            "A. IPS",
            "B. IDS",
            "C. Proxy",
            "D. Load balancer"
        ],
        "answer": "B. IDS"
    },
    {
        "question": "Which network device assigns IP addresses dynamically to hosts on a network?",
        "options": [
            "A. Firewall",
            "B. Switch",
            "C. DHCP server",
            "D. Load balancer"
        ],
        "answer": "C. DHCP server"
    },
    {
        "question": "A company needs a storage solution that provides block-level storage for multiple servers in a data center. Which technology should they implement?",
        "options": [
            "A. NAS",
            "B. SAN",
            "C. IDS",
            "D. CDN"
        ],
        "answer": "B. SAN"
    },
    {
        "question": "A network engineer is implementing QoS policies. What is the primary reason for using QoS?",
        "options": [
            "A. To provide secure remote access",
            "B. To prioritize traffic and ensure critical applications receive adequate bandwidth",
            "C. To encrypt all network traffic",
            "D. To block unauthorized users from accessing a network"
        ],
        "answer": "B. To prioritize traffic and ensure critical applications receive adequate bandwidth"
    },
    {
        "question": "Which of the following networking appliances can operate in both physical and virtual forms?",
        "options": [
            "A. Router",
            "B. Firewall",
            "C. Load balancer",
            "D. All of the above"
        ],
        "answer": "D. All of the above"
    },
    {
        "question": "A company uses multiple servers for hosting web applications. To ensure high availability and distribute network traffic efficiently, which solution should be used?",
        "options": [
            "A. IDS",
            "B. Load balancer",
            "C. Firewall",
            "D. NAS"
        ],
        "answer": "B. Load balancer"
    },
    {
        "question": "Which device is primarily responsible for providing network access in wireless environments?",
        "options": [
            "A. Switch",
            "B. Access Point (AP)",
            "C. IDS",
            "D. Load balancer"
        ],
        "answer": "B. Access Point (AP)"
    },
    {
        "question": "An administrator needs to ensure that packets do not circulate endlessly within a network. Which field in an IP packet header helps achieve this?",
        "options": [
            "A. MAC address",
            "B. TTL (Time to Live)",
            "C. QoS",
            "D. VLAN ID"
        ],
        "answer": "B. TTL (Time to Live)"
    },
    {
        "question": "A company wants to improve security by filtering incoming and outgoing network traffic based on predefined rules. Which device should they use?",
        "options": [
            "A. IDS",
            "B. Firewall",
            "C. Proxy server",
            "D. Load balancer"
        ],
        "answer": "B. Firewall"
    },
    {
        "question": "A technician needs to provide an efficient way for employees to access files stored on a central network drive. Which solution should they implement?",
        "options": [
            "A. NAS",
            "B. SAN",
            "C. VPN",
            "D. QoS"
        ],
        "answer": "A. NAS"
    },
    {
        "question": "A company is expanding its data center and needs a solution to manage network traffic between multiple servers to ensure even distribution of workload. Which device should they implement?",
        "options": [
            "A. Router",
            "B. Firewall",
            "C. Load balancer",
            "D. Proxy server"
        ],
        "answer": "C. Load balancer"
    },
    {
        "question": "An administrator needs to allow remote employees to securely access company resources over an encrypted connection. Which technology should be implemented?",
        "options": [
            "A. IDS",
            "B. VPN",
            "C. Proxy server",
            "D. QoS"
        ],
        "answer": "B. VPN"
    },
    {
        "question": "Which of the following devices operates primarily at Layer 3 of the OSI model and is responsible for directing packets between different networks?",
        "options": [
            "A. Switch",
            "B. Router",
            "C. Firewall",
            "D. Access Point"
        ],
        "answer": "B. Router"
    },
    {
        "question": "A company uses a network device that monitors inbound traffic for malicious activity and generates alerts but does not take any action. Which device is being used?",
        "options": [
            "A. IPS",
            "B. IDS",
            "C. Firewall",
            "D. Proxy"
        ],
        "answer": "B. IDS"
    },
    {
        "question": "A network administrator is configuring a device that prevents unauthorized access to a network by filtering traffic based on predefined security rules. What device is being configured?",
        "options": [
            "A. Router",
            "B. Firewall",
            "C. Switch",
            "D. Load balancer"
        ],
        "answer": "B. Firewall"
    },
    {
        "question": "An organization wants to store frequently accessed data closer to users to reduce latency and improve loading times for web applications. Which solution should they implement?",
        "options": [
            "A. CDN",
            "B. VPN",
            "C. IDS",
            "D. NAS"
        ],
        "answer": "A. CDN"
    },
    {
        "question": "Which device allows multiple hosts on a local network to communicate with each other by forwarding frames based on MAC addresses?",
        "options": [
            "A. Router",
            "B. Switch",
            "C. Firewall",
            "D. Load balancer"
        ],
        "answer": "B. Switch"
    },
    {
        "question": "A company needs a network storage solution that allows multiple users to access files over the network simultaneously. Which option should they choose?",
        "options": [
            "A. NAS",
            "B. SAN",
            "C. Proxy",
            "D. IDS"
        ],
        "answer": "A. NAS"
    },
    {
        "question": "Which of the following is a key difference between NAS and SAN storage solutions?",
        "options": [
            "A. NAS operates at the file level, while SAN operates at the block level",
            "B. NAS is more expensive than SAN",
            "C. NAS requires fiber channel, while SAN uses Ethernet",
            "D. SAN does not support multiple users"
        ],
        "answer": "A. NAS operates at the file level, while SAN operates at the block level"
    },
    {
        "question": "A company deploys a wireless network and needs to centralize management for all access points. Which device should they use?",
        "options": [
            "A. IDS",
            "B. Wireless controller",
            "C. Proxy server",
            "D. Firewall"
        ],
        "answer": "B. Wireless controller"
    },
    {
        "question": "What is the primary purpose of a proxy server?",
        "options": [
            "A. To filter and cache internet traffic",
            "B. To encrypt end-to-end communication",
            "C. To act as a firewall",
            "D. To balance network traffic between servers"
        ],
        "answer": "A. To filter and cache internet traffic"
    },
    {
        "question": "A company uses a cloud-based solution to serve content from the nearest server location to users worldwide. Which technology is being used?",
        "options": [
            "A. IDS",
            "B. VPN",
            "C. CDN",
            "D. QoS"
        ],
        "answer": "C. CDN"
    },
    {
        "question": "Which of the following helps prioritize network traffic to ensure that critical applications receive the necessary bandwidth?",
        "options": [
            "A. IDS",
            "B. QoS",
            "C. VPN",
            "D. TTL"
        ],
        "answer": "B. QoS"
    },
    {
        "question": "What does TTL (Time to Live) prevent in networking?",
        "options": [
            "A. Unauthorized access",
            "B. Packet looping indefinitely",
            "C. Malicious attacks",
            "D. Bandwidth overuse"
        ],
        "answer": "B. Packet looping indefinitely"
    },
    {
        "question": "Which OSI layer is responsible for defining the physical characteristics of network interfaces?",
        "options": [
            "A. Data Link",
            "B. Transport",
            "C. Physical",
            "D. Network"
        ],
        "answer": "C. Physical"
    },
    {
        "question": "At which OSI layer do MAC addresses operate?",
        "options": [
            "A. Network",
            "B. Transport",
            "C. Data Link",
            "D. Session"
        ],
        "answer": "C. Data Link"
    },
    {
        "question": "Which OSI layer is responsible for logical addressing and routing?",
        "options": [
            "A. Physical",
            "B. Data Link",
            "C. Transport",
            "D. Network"
        ],
        "answer": "D. Network"
    },
    {
        "question": "What OSI layer ensures end-to-end communication reliability with error detection and correction?",
        "options": [
            "A. Network",
            "B. Transport",
            "C. Session",
            "D. Data Link"
        ],
        "answer": "B. Transport"
    },
    {
        "question": "Which OSI layer manages sessions and controls dialog between devices?",
        "options": [
            "A. Presentation",
            "B. Session",
            "C. Application",
            "D. Network"
        ],
        "answer": "B. Session"
    },
    {
        "question": "Which layer is responsible for data encryption and compression?",
        "options": [
            "A. Presentation",
            "B. Transport",
            "C. Session",
            "D. Application"
        ],
        "answer": "A. Presentation"
    },
    {
        "question": "Which OSI layer provides network services such as email, file transfer, and remote login?",
        "options": [
            "A. Presentation",
            "B. Transport",
            "C. Application",
            "D. Session"
        ],
        "answer": "C. Application"
    },
    {
        "question": "What is the primary function of the Data Link layer?",
        "options": [
            "A. Error detection and frame synchronization",
            "B. Routing and forwarding packets",
            "C. Establishing and terminating communication sessions",
            "D. Ensuring reliable data transport"
        ],
        "answer": "A. Error detection and frame synchronization"
    },
    {
        "question": "Which OSI layer uses IP addresses for communication?",
        "options": [
            "A. Data Link",
            "B. Network",
            "C. Transport",
            "D. Application"
        ],
        "answer": "B. Network"
    },
    {
        "question": "Which layer is responsible for segmenting and reassembling data?",
        "options": [
            "A. Transport",
            "B. Network",
            "C. Data Link",
            "D. Physical"
        ],
        "answer": "A. Transport"
    },
    {
        "question": "At which OSI layer do switches primarily operate?",
        "options": [
            "A. Physical",
            "B. Data Link",
            "C. Network",
            "D. Transport"
        ],
        "answer": "B. Data Link"
    },
    {
        "question": "Which of the following devices operates at the OSI Network layer?",
        "options": [
            "A. Hub",
            "B. Router",
            "C. Switch",
            "D. Repeater"
        ],
        "answer": "B. Router"
    },
    {
        "question": "Which protocol operates at the Transport layer of the OSI model?",
        "options": [
            "A. IP",
            "B. HTTP",
            "C. TCP",
            "D. ARP"
        ],
        "answer": "C. TCP"
    },
    {
        "question": "What is the primary function of the Physical layer in the OSI model?",
        "options": [
            "A. Defining hardware specifications",
            "B. Assigning IP addresses",
            "C. Managing end-to-end communication",
            "D. Establishing communication sessions"
        ],
        "answer": "A. Defining hardware specifications"
    },
    {
        "question": "Which OSI layer provides flow control and error recovery?",
        "options": [
            "A. Network",
            "B. Transport",
            "C. Data Link",
            "D. Physical"
        ],
        "answer": "B. Transport"
    },
    {
        "question": "Which OSI layer is responsible for media access control and logical link control?",
        "options": [
            "A. Data Link",
            "B. Physical",
            "C. Network",
            "D. Transport"
        ],
        "answer": "A. Data Link"
    },
    {
        "question": "Which OSI layer ensures that data is properly formatted for the application layer?",
        "options": [
            "A. Network",
            "B. Transport",
            "C. Presentation",
            "D. Data Link"
        ],
        "answer": "C. Presentation"
    },
    {
        "question": "At which OSI layer does SSL/TLS encryption occur?",
        "options": [
            "A. Session",
            "B. Transport",
            "C. Presentation",
            "D. Network"
        ],
        "answer": "C. Presentation"
    },
    {
        "question": "Which OSI layer is responsible for establishing, maintaining, and terminating communication between devices?",
        "options": [
            "A. Network",
            "B. Transport",
            "C. Session",
            "D. Application"
        ],
        "answer": "C. Session"
    },
    {
        "question": "What is a key function of the Application layer?",
        "options": [
            "A. Managing logical addresses",
            "B. Providing user interface services",
            "C. Establishing network connections",
            "D. Managing data encryption"
        ],
        "answer": "B. Providing user interface services"
    },
    {
        "question": "Which of the following protocols operates at the Application layer?",
        "options": [
            "A. HTTP",
            "B. TCP",
            "C. IP",
            "D. Ethernet"
        ],
        "answer": "A. HTTP"
    },
    {
        "question": "At which OSI layer does packet forwarding occur?",
        "options": [
            "A. Data Link",
            "B. Transport",
            "C. Network",
            "D. Physical"
        ],
        "answer": "C. Network"
    },
    {
        "question": "Which OSI layer does a firewall primarily operate at?",
        "options": [
            "A. Physical",
            "B. Network",
            "C. Data Link",
            "D. Application"
        ],
        "answer": "B. Network"
    },
    {
        "question": "Which protocol is used for reliable data transfer at the Transport layer?",
        "options": [
            "A. UDP",
            "B. TCP",
            "C. ICMP",
            "D. ARP"
        ],
        "answer": "B. TCP"
    },
    {
        "question": "At which OSI layer does ARP function?",
        "options": [
            "A. Network",
            "B. Data Link",
            "C. Transport",
            "D. Application"
        ],
        "answer": "A. Network"
    },
    {
        "question": "Which OSI layer is responsible for bit transmission over the medium?",
        "options": [
            "A. Data Link",
            "B. Transport",
            "C. Physical",
            "D. Network"
        ],
        "answer": "C. Physical"
    },
    {
        "question": "What is the primary purpose of IPv6 addressing?",
        "options": [
            "A. To replace IPv4 due to address exhaustion",
            "B. To improve wireless network speeds",
            "C. To simplify DNS resolution",
            "D. To enhance encryption for all traffic"
        ],
        "answer": "A. To replace IPv4 due to address exhaustion"
    },
    {
        "question": "Which of the following is a key advantage of IPv6 over IPv4?",
        "options": [
            "A. Smaller packet headers",
            "B. Larger address space",
            "C. Built-in NAT functionality",
            "D. Compatibility with all legacy systems"
        ],
        "answer": "B. Larger address space"
    },
    {
        "question": "What is the primary method used to mitigate IPv4 address exhaustion?",
        "options": [
            "A. Implementing IPv6",
            "B. Increasing the use of NAT",
            "C. Reducing the number of internet users",
            "D. Reusing private IP addresses"
        ],
        "answer": "A. Implementing IPv6"
    },
    {
        "question": "Which IPv6 address type is used for communication within a single network segment?",
        "options": [
            "A. Unicast",
            "B. Multicast",
            "C. Anycast",
            "D. Broadcast"
        ],
        "answer": "A. Unicast"
    },
    {
        "question": "What is the purpose of tunneling in IPv6?",
        "options": [
            "A. To encapsulate IPv6 packets within IPv4 packets for compatibility",
            "B. To encrypt IPv6 traffic for security",
            "C. To compress IPv6 headers for efficiency",
            "D. To route IPv6 traffic through a VPN"
        ],
        "answer": "A. To encapsulate IPv6 packets within IPv4 packets for compatibility"
    },
    {
        "question": "Which of the following is an example of an IPv6 tunneling protocol?",
        "options": [
            "A. GRE",
            "B. OSPF",
            "C. BGP",
            "D. RIP"
        ],
        "answer": "A. GRE"
    },
    {
        "question": "What is the purpose of dual stack in IPv6 deployment?",
        "options": [
            "A. To run IPv4 and IPv6 simultaneously on the same network",
            "B. To prioritize IPv6 traffic over IPv4",
            "C. To convert IPv4 addresses to IPv6",
            "D. To encrypt IPv6 traffic"
        ],
        "answer": "A. To run IPv4 and IPv6 simultaneously on the same network"
    },
    {
        "question": "Which of the following is a benefit of using NAT64?",
        "options": [
            "A. It allows IPv6-only devices to communicate with IPv4-only devices",
            "B. It encrypts traffic between IPv6 networks",
            "C. It reduces the size of IPv6 headers",
            "D. It eliminates the need for DNS"
        ],
        "answer": "A. It allows IPv6-only devices to communicate with IPv4-only devices"
    },
    {
        "question": "What is the primary function of NAT64?",
        "options": [
            "A. To translate IPv6 addresses to IPv4 addresses",
            "B. To encrypt IPv6 traffic",
            "C. To compress IPv6 headers",
            "D. To route IPv6 traffic through a VPN"
        ],
        "answer": "A. To translate IPv6 addresses to IPv4 addresses"
    },
    {
        "question": "Which of the following is a characteristic of IPv6 addresses?",
        "options": [
            "A. 32-bit address length",
            "B. 128-bit address length",
            "C. 64-bit address length",
            "D. 256-bit address length"
        ],
        "answer": "B. 128-bit address length"
    },
    {
        "question": "What is the purpose of the IPv6 loopback address (::1)?",
        "options": [
            "A. To test network connectivity on the local machine",
            "B. To represent an unspecified address",
            "C. To enable multicast communication",
            "D. To route traffic to the default gateway"
        ],
        "answer": "A. To test network connectivity on the local machine"
    },
    {
        "question": "Which of the following is a valid IPv6 address?",
        "options": [
            "A. 2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "B. 192.168.1.1",
            "C. 2001:0db8:85a3::8a2e:0370:7334",
            "D. Both A and C"
        ],
        "answer": "D. Both A and C"
    },
    {
        "question": "What is the primary purpose of IPv6 stateless address autoconfiguration (SLAAC)?",
        "options": [
            "A. To assign IP addresses without a DHCP server",
            "B. To encrypt IPv6 traffic",
            "C. To compress IPv6 headers",
            "D. To route traffic between networks"
        ],
        "answer": "A. To assign IP addresses without a DHCP server"
    },
    {
        "question": "Which of the following is a disadvantage of using tunneling for IPv6 deployment?",
        "options": [
            "A. Increased complexity and overhead",
            "B. Reduced security",
            "C. Incompatibility with NAT",
            "D. Limited address space"
        ],
        "answer": "A. Increased complexity and overhead"
    },
    {
        "question": "What is the purpose of the IPv6 link-local address?",
        "options": [
            "A. To enable communication within a single network segment",
            "B. To route traffic between networks",
            "C. To provide global internet connectivity",
            "D. To encrypt IPv6 traffic"
        ],
        "answer": "A. To enable communication within a single network segment"
    },
    {
        "question": "Which of the following protocols is used for IPv6 neighbor discovery?",
        "options": [
            "A. ICMPv6",
            "B. ARP",
            "C. DHCPv6",
            "D. OSPFv3"
        ],
        "answer": "A. ICMPv6"
    },
    {
        "question": "What is the primary purpose of DHCPv6?",
        "options": [
            "A. To assign IPv6 addresses and configuration parameters",
            "B. To encrypt IPv6 traffic",
            "C. To compress IPv6 headers",
            "D. To route traffic between networks"
        ],
        "answer": "A. To assign IPv6 addresses and configuration parameters"
    },
    {
        "question": "Which of the following is a benefit of using dual stack over tunneling?",
        "options": [
            "A. Simplified network configuration",
            "B. Reduced overhead",
            "C. Improved security",
            "D. Compatibility with all legacy systems"
        ],
        "answer": "B. Reduced overhead"
    },
    {
        "question": "What is the primary purpose of NAT64?",
        "options": [
            "A. To enable communication between IPv6 and IPv4 networks",
            "B. To encrypt IPv6 traffic",
            "C. To compress IPv6 headers",
            "D. To route traffic between IPv6 networks"
        ],
        "answer": "A. To enable communication between IPv6 and IPv4 networks"
    },
    {
        "question": "Which of the following is a characteristic of IPv6 multicast addresses?",
        "options": [
            "A. They start with FF00::/8",
            "B. They are used for one-to-one communication",
            "C. They are equivalent to IPv4 broadcast addresses",
            "D. They are only used for local loopback"
        ],
        "answer": "A. They start with FF00::/8"
    },
    {
        "question": "What is the purpose of the IPv6 anycast address?",
        "options": [
            "A. To deliver packets to the nearest interface in a group",
            "B. To enable multicast communication",
            "C. To test network connectivity",
            "D. To route traffic to the default gateway"
        ],
        "answer": "A. To deliver packets to the nearest interface in a group"
    },
    {
        "question": "Which of the following is a challenge of IPv6 adoption?",
        "options": [
            "A. Lack of vendor support",
            "B. Complexity of configuration",
            "C. Limited address space",
            "D. Incompatibility with modern networks"
        ],
        "answer": "B. Complexity of configuration"
    },
    {
        "question": "What is the purpose of the IPv6 prefix in an address?",
        "options": [
            "A. To identify the network portion of the address",
            "B. To identify the host portion of the address",
            "C. To enable multicast communication",
            "D. To encrypt IPv6 traffic"
        ],
        "answer": "A. To identify the network portion of the address"
    },
    {
        "question": "Which of the following is a benefit of IPv6 over IPv4?",
        "options": [
            "A. Built-in support for IPsec",
            "B. Smaller packet headers",
            "C. Compatibility with all legacy systems",
            "D. Reduced need for routing"
        ],
        "answer": "A. Built-in support for IPsec"
    },
    {
        "question": "What is the primary purpose of the IPv6 unspecified address (::)?",
        "options": [
            "A. To represent an absent or unknown address",
            "B. To enable multicast communication",
            "C. To test network connectivity",
            "D. To route traffic to the default gateway"
        ],
        "answer": "A. To represent an absent or unknown address"
    },
    {
  "question": "Which of the following is true about static routing?",
  "options": [
    "A. Static routes are automatically adjusted by the routing protocol.",
    "B. Static routing requires manual configuration of routes by the network administrator.",
    "C. Static routes use dynamic metrics to determine the best path.",
    "D. Static routes are updated automatically based on network traffic changes."
  ],
  "answer": "B. Static routing requires manual configuration of routes by the network administrator."
},
{
  "question": "Which of the following protocols is an example of a dynamic routing protocol?",
  "options": [
    "A. ARP",
    "B. OSPF",
    "C. NAT",
    "D. DNS"
  ],
  "answer": "B. OSPF"
},
{
  "question": "What is the primary function of Border Gateway Protocol (BGP)?",
  "options": [
    "A. To select the best route based on the lowest cost metric",
    "B. To exchange routing information between different autonomous systems",
    "C. To dynamically configure IP addresses in a network",
    "D. To prevent routing loops within an interior network"
  ],
  "answer": "B. To exchange routing information between different autonomous systems"
},
{
  "question": "Which of the following is a feature of Enhanced Interior Gateway Routing Protocol (EIGRP)?",
  "options": [
    "A. EIGRP uses a link-state routing algorithm to determine the best path.",
    "B. EIGRP is a distance-vector protocol with support for multiple network layer protocols.",
    "C. EIGRP only supports IP routing.",
    "D. EIGRP uses the metric based only on the number of hops."
  ],
  "answer": "B. EIGRP is a distance-vector protocol with support for multiple network layer protocols."
},
{
  "question": "What does the OSPF (Open Shortest Path First) protocol primarily use to determine the best path?",
  "options": [
    "A. The number of hops",
    "B. The lowest cost based on link metrics",
    "C. The lowest administrative distance",
    "D. The highest bandwidth link"
  ],
  "answer": "B. The lowest cost based on link metrics"
},
{
  "question": "Which of the following factors affects route selection in dynamic routing protocols?",
  "options": [
    "A. Administrative distance",
    "B. Prefix length",
    "C. Metric",
    "D. All of the above"
  ],
  "answer": "D. All of the above"
},
{
  "question": "When comparing two routing protocols, which one would be preferred if the administrative distance is lower?",
  "options": [
    "A. The routing protocol with a higher administrative distance",
    "B. The routing protocol with a lower administrative distance",
    "C. The protocol with the highest metric",
    "D. The protocol with the longest prefix length"
  ],
  "answer": "B. The routing protocol with a lower administrative distance"
},
{
  "question": "In the context of routing, what does a 'metric' represent?",
  "options": [
    "A. The time taken for a packet to travel from source to destination",
    "B. The number of hops between two routers",
    "C. The bandwidth of the network link",
    "D. A value that determines the best path to reach a destination"
  ],
  "answer": "D. A value that determines the best path to reach a destination"
},
{
  "question": "Which of the following is an example of a metric used by EIGRP?",
  "options": [
    "A. Administrative distance",
    "B. Cost",
    "C. Bandwidth and delay",
    "D. Hop count"
  ],
  "answer": "C. Bandwidth and delay"
},
{
  "question": "What is the primary purpose of Administrative Distance in route selection?",
  "options": [
    "A. To measure the delay of a route",
    "B. To prioritize the best route when multiple routing protocols provide routes to the same destination",
    "C. To calculate the cost of a path",
    "D. To define the size of the routing table"
  ],
  "answer": "B. To prioritize the best route when multiple routing protocols provide routes to the same destination"
},
{
  "question": "What is the primary advantage of using static routing over dynamic routing?",
  "options": [
    "A. Static routing requires less manual configuration.",
    "B. Static routing is more scalable than dynamic routing.",
    "C. Static routing is more secure as it does not depend on routing updates.",
    "D. Static routing automatically adjusts to network changes."
  ],
  "answer": "C. Static routing is more secure as it does not depend on routing updates."
},
{
  "question": "What is the maximum number of hops allowed in a routing path for RIP?",
  "options": [
    "A. 15",
    "B. 16",
    "C. 10",
    "D. Unlimited"
  ],
  "answer": "A. 15"
},
{
  "question": "Which of the following routing protocols is best suited for large, complex networks with multiple routes between autonomous systems?",
  "options": [
    "A. RIP",
    "B. OSPF",
    "C. BGP",
    "D. EIGRP"
  ],
  "answer": "C. BGP"
},
{
  "question": "What does the OSPF area concept help with?",
  "options": [
    "A. Reducing the size of the routing table",
    "B. Defining the physical location of routers",
    "C. Encrypting routing information",
    "D. Connecting different autonomous systems"
  ],
  "answer": "A. Reducing the size of the routing table"
},
{
  "question": "What type of routing protocol is OSPF?",
  "options": [
    "A. Distance-vector",
    "B. Link-state",
    "C. Hybrid",
    "D. Path-vector"
  ],
  "answer": "B. Link-state"
},
{
  "question": "In BGP, what is the primary metric used to determine the best path?",
  "options": [
    "A. Bandwidth",
    "B. AS Path",
    "C. Cost",
    "D. Hop count"
  ],
  "answer": "B. AS Path"
},
{
  "question": "Which routing protocol uses a Diffusing Update Algorithm (DUAL) for calculating the best path?",
  "options": [
    "A. RIP",
    "B. OSPF",
    "C. EIGRP",
    "D. BGP"
  ],
  "answer": "C. EIGRP"
},
{
  "question": "What happens when two routing protocols advertise routes with the same administrative distance?",
  "options": [
    "A. The routing protocol with the highest metric is selected.",
    "B. The route with the lowest cost is preferred.",
    "C. The route with the longest prefix length is preferred.",
    "D. The tie is broken based on the protocol type."
  ],
  "answer": "D. The tie is broken based on the protocol type."
},
{
  "question": "Which routing protocol is typically used in larger enterprise networks for internal routing?",
  "options": [
    "A. BGP",
    "B. OSPF",
    "C. RIP",
    "D. EIGRP"
  ],
  "answer": "B. OSPF"
},
{
  "question": "What does the OSPF router ID (RID) uniquely identify?",
  "options": [
    "A. The router's IP address",
    "B. The router's network interface",
    "C. The router within an OSPF network",
    "D. The OSPF version used"
  ],
  "answer": "C. The router within an OSPF network"
},
{
  "question": "Which of the following is a key advantage of using EIGRP over OSPF?",
  "options": [
    "A. EIGRP is an open standard protocol.",
    "B. EIGRP uses a less complex metric for route calculation.",
    "C. EIGRP scales better in large networks than OSPF.",
    "D. EIGRP supports more types of routing protocols."
  ],
  "answer": "B. EIGRP uses a less complex metric for route calculation."
},
{
  "question": "In the context of OSPF, what does the term 'cost' refer to?",
  "options": [
    "A. The time it takes for a packet to travel from source to destination",
    "B. A value based on the bandwidth of the link",
    "C. The number of hops between routers",
    "D. The administrative distance of a route"
  ],
  "answer": "B. A value based on the bandwidth of the link"
},
{
  "question": "What is the purpose of a routing table?",
  "options": [
    "A. To store the configuration of network devices",
    "B. To list all possible paths to a destination network",
    "C. To store all IP addresses in a network",
    "D. To store static IP address assignments"
  ],
  "answer": "B. To list all possible paths to a destination network"
},
{
  "question": "Which of the following is used to select the best route when multiple routes to a destination exist?",
  "options": [
    "A. Administrative distance",
    "B. Prefix length",
    "C. Metric",
    "D. All of the above"
  ],
  "answer": "D. All of the above"
},
{
  "question": "What does the administrative distance value indicate?",
  "options": [
    "A. The quality of the link",
    "B. The number of hops to a destination",
    "C. The reliability of the routing protocol",
    "D. The cost of a route"
  ],
  "answer": "C. The reliability of the routing protocol"
},
{
  "question": "What is the primary difference between RIP and OSPF?",
  "options": [
    "A. RIP uses hop count as a metric, while OSPF uses link cost.",
    "B. RIP is a link-state protocol, while OSPF is distance-vector.",
    "C. RIP supports multiple networks, while OSPF is limited to a single network.",
    "D. RIP supports IPv6, while OSPF does not."
  ],
  "answer": "A. RIP uses hop count as a metric, while OSPF uses link cost."
},
{
  "question": "Which metric does EIGRP use to calculate the best path?",
  "options": [
    "A. Bandwidth only",
    "B. Bandwidth and delay",
    "C. Hop count",
    "D. Administrative distance"
  ],
  "answer": "B. Bandwidth and delay"
},
{
  "question": "Which of the following describes a disadvantage of static routing?",
  "options": [
    "A. It requires frequent updates as the network topology changes.",
    "B. It automatically adapts to network failures.",
    "C. It does not require any configuration.",
    "D. It is always more scalable than dynamic routing."
  ],
  "answer": "A. It requires frequent updates as the network topology changes."
},
{
  "question": "Which of the following is a primary benefit of using BGP in a large network?",
  "options": [
    "A. It supports path selection between autonomous systems.",
    "B. It calculates the best path based solely on hop count.",
    "C. It supports automatic configuration of IP addresses.",
    "D. It is less resource-intensive than other routing protocols."
  ],
  "answer": "A. It supports path selection between autonomous systems."
},
{
  "question": "Which routing protocol would be the best choice for a small, simple network where routing information is not expected to change frequently?",
  "options": [
    "A. OSPF",
    "B. RIP",
    "C. BGP",
    "D. EIGRP"
  ],
  "answer": "B. RIP"
},
{
  "question": "What is the primary function of NAT (Network Address Translation)?",
  "options": [
    "A. To assign public IP addresses to internal devices",
    "B. To translate between private and public IP addresses",
    "C. To assign private IP addresses to internal devices",
    "D. To encrypt traffic between networks"
  ],
  "answer": "B. To translate between private and public IP addresses"
},
{
  "question": "Which of the following is a benefit of using Port Address Translation (PAT)?",
  "options": [
    "A. It enables multiple devices to share a single public IP address.",
    "B. It allows devices to use the same private IP address on a network.",
    "C. It provides a unique IP address for each device on the network.",
    "D. It reduces the need for NAT on large networks."
  ],
  "answer": "A. It enables multiple devices to share a single public IP address."
},
{
  "question": "What is the primary purpose of a Virtual IP (VIP)?",
  "options": [
    "A. To provide a single IP address that can be used by multiple devices in a network.",
    "B. To ensure high availability by allowing multiple devices to share a single IP address.",
    "C. To allow for the management of multiple network interfaces.",
    "D. To dynamically assign IP addresses to devices on a network."
  ],
  "answer": "B. To ensure high availability by allowing multiple devices to share a single IP address."
},
{
  "question": "Which of the following is a key characteristic of First Hop Redundancy Protocols (FHRPs)?",
  "options": [
    "A. They provide redundancy for the default gateway in a network.",
    "B. They assign IP addresses dynamically to devices on a network.",
    "C. They are used to route traffic across multiple ISPs.",
    "D. They translate private IP addresses to public ones."
  ],
  "answer": "A. They provide redundancy for the default gateway in a network."
},
{
  "question": "Which of the following is an example of a First Hop Redundancy Protocol (FHRP)?",
  "options": [
    "A. HSRP (Hot Standby Router Protocol)",
    "B. BGP (Border Gateway Protocol)",
    "C. RIP (Routing Information Protocol)",
    "D. OSPF (Open Shortest Path First)"
  ],
  "answer": "A. HSRP (Hot Standby Router Protocol)"
},
{
  "question": "What is the main advantage of using Subinterfaces on a router?",
  "options": [
    "A. To allow multiple VLANs to be routed through a single physical interface",
    "B. To increase the security of a network by separating broadcast domains",
    "C. To assign public IP addresses to devices within a subnet",
    "D. To improve the performance of routing protocols"
  ],
  "answer": "A. To allow multiple VLANs to be routed through a single physical interface"
},
{
  "question": "Which protocol is commonly used to configure and manage First Hop Redundancy Protocols (FHRP)?",
  "options": [
    "A. ICMP",
    "B. DHCP",
    "C. HSRP",
    "D. VRRP"
  ],
  "answer": "C. HSRP"
},
{
  "question": "What is the default behavior of a router when NAT is applied and an outgoing packet is being processed?",
  "options": [
    "A. The router changes the source IP address to a private address.",
    "B. The router replaces the destination IP address with the public IP address.",
    "C. The router replaces the source IP address with a public IP address.",
    "D. The router changes the port number to a random value."
  ],
  "answer": "C. The router replaces the source IP address with a public IP address."
},
{
  "question": "Which of the following protocols provides redundancy for a default gateway by assigning a virtual IP (VIP) address?",
  "options": [
    "A. HSRP (Hot Standby Router Protocol)",
    "B. RIP (Routing Information Protocol)",
    "C. BGP (Border Gateway Protocol)",
    "D. EIGRP (Enhanced Interior Gateway Routing Protocol)"
  ],
  "answer": "A. HSRP (Hot Standby Router Protocol)"
},
{
  "question": "How does Port Address Translation (PAT) work?",
  "options": [
    "A. It assigns a different public IP address to each internal device.",
    "B. It maps each port number to an internal IP address for outbound traffic.",
    "C. It encrypts the IP address to hide the internal network structure.",
    "D. It is used to create Virtual LANs (VLANs) on a network."
  ],
  "answer": "B. It maps each port number to an internal IP address for outbound traffic."
},
{
  "question": "What is the primary role of a subinterface in networking?",
  "options": [
    "A. To create a virtual interface on a router that is associated with a VLAN.",
    "B. To define a unique IP address for every device on a network.",
    "C. To connect different routers together in a mesh topology.",
    "D. To assign an IP address to a single physical interface."
  ],
  "answer": "A. To create a virtual interface on a router that is associated with a VLAN."
},
{
  "question": "Which of the following can be used to create redundancy for a router's default gateway?",
  "options": [
    "A. Virtual IP (VIP)",
    "B. NAT64",
    "C. Port forwarding",
    "D. DHCP"
  ],
  "answer": "A. Virtual IP (VIP)"
},
{
  "question": "When using NAT, which of the following is typically changed on outbound packets?",
  "options": [
    "A. The source MAC address",
    "B. The source IP address",
    "C. The destination IP address",
    "D. The source port number"
  ],
  "answer": "B. The source IP address"
},
{
  "question": "What is the primary purpose of a Virtual IP (VIP) address in load balancing?",
  "options": [
    "A. To balance the load between multiple routers in a network",
    "B. To provide a single IP address that is shared by multiple servers",
    "C. To assign IP addresses to internal devices in a network",
    "D. To hide the internal IP addresses of a network from external users"
  ],
  "answer": "B. To provide a single IP address that is shared by multiple servers"
},
{
  "question": "Which of the following is an example of a First Hop Redundancy Protocol (FHRP) that is used to provide a virtual IP address for redundancy?",
  "options": [
    "A. HSRP",
    "B. OSPF",
    "C. EIGRP",
    "D. RIP"
  ],
  "answer": "A. HSRP"
},
{
  "question": "Which type of network topology would benefit most from using subinterfaces?",
  "options": [
    "A. Point-to-point",
    "B. Hub-and-spoke",
    "C. Star topology",
    "D. VLANs across multiple routers"
  ],
  "answer": "D. VLANs across multiple routers"
},
{
  "question": "What is one advantage of using Port Address Translation (PAT) in a network?",
  "options": [
    "A. It enables multiple devices on a local network to share a single public IP address.",
    "B. It helps to securely encrypt traffic across the internet.",
    "C. It assigns a unique public IP address to every internal device.",
    "D. It allows devices on a local network to communicate without needing a router."
  ],
  "answer": "A. It enables multiple devices on a local network to share a single public IP address."
},
{
  "question": "What is a key characteristic of First Hop Redundancy Protocols (FHRPs) in terms of providing network reliability?",
  "options": [
    "A. They provide dynamic routing updates to avoid network failures.",
    "B. They prevent the use of static routes in a network.",
    "C. They allow multiple routers to share a virtual IP address to act as a default gateway.",
    "D. They simplify IP address assignments for end devices."
  ],
  "answer": "C. They allow multiple routers to share a virtual IP address to act as a default gateway."
},  
{
  "question": "Which of the following is true about Port Address Translation (PAT)?",
  "options": [
    "A. It assigns a unique public IP address to each internal device.",
    "B. It uses a single public IP address for multiple devices inside a private network.",
    "C. It is used to hide internal IP addresses behind a router's public IP address.",
    "D. It enables devices to communicate using their private IP addresses on the internet."
  ],
  "answer": "B. It uses a single public IP address for multiple devices inside a private network."
},
{
  "question": "Which of the following is NOT a common use of Network Address Translation (NAT)?",
  "options": [
    "A. To allow multiple devices on a private network to access the internet using one public IP.",
    "B. To assign unique IP addresses to every device within a network.",
    "C. To hide the internal IP structure of a network from external networks.",
    "D. To enable communication between devices on a private network and the public internet."
  ],
  "answer": "B. To assign unique IP addresses to every device within a network."
},
{
  "question": "What is a key benefit of using First Hop Redundancy Protocols (FHRPs) in a network?",
  "options": [
    "A. They ensure high availability of the default gateway in case of a failure.",
    "B. They reduce network congestion by filtering unnecessary traffic.",
    "C. They simplify the management of IP addressing in a network.",
    "D. They dynamically assign IP addresses to devices in the network."
  ],
  "answer": "A. They ensure high availability of the default gateway in case of a failure."
},
{
  "question": "Which protocol is used in the configuration of First Hop Redundancy Protocols (FHRPs)?",
  "options": [
    "A. OSPF",
    "B. HSRP",
    "C. RIP",
    "D. DHCP"
  ],
  "answer": "B. HSRP"
},
{
  "question": "What is the purpose of a Virtual IP (VIP) in load balancing?",
  "options": [
    "A. To provide a consistent IP address for multiple devices or services.",
    "B. To allocate unique IP addresses to devices on a network.",
    "C. To provide a private IP address for each device on a network.",
    "D. To create isolated subnets within the same IP address range."
  ],
  "answer": "A. To provide a consistent IP address for multiple devices or services."
},
{
  "question": "What is the primary use case for NAT64?",
  "options": [
    "A. To provide IPv4 address translation for IPv6-only clients.",
    "B. To allow IPv6 clients to access IPv4-only services.",
    "C. To assign IPv6 addresses to devices on a private network.",
    "D. To configure a single IPv6 address for use in multiple networks."
  ],
  "answer": "B. To allow IPv6 clients to access IPv4-only services."
},
{
  "question": "What is one advantage of using subinterfaces on a router?",
  "options": [
    "A. They allow multiple IP addresses on a single physical interface.",
    "B. They increase the bandwidth of a physical interface.",
    "C. They simplify the management of routing tables.",
    "D. They provide high availability by creating backup interfaces."
  ],
  "answer": "A. They allow multiple IP addresses on a single physical interface."
},
{
  "question": "Which of the following scenarios would most likely require the use of a subinterface?",
  "options": [
    "A. Connecting two routers for high availability.",
    "B. Routing between multiple VLANs on the same physical router interface.",
    "C. Adding a firewall between the public and private network.",
    "D. Using a VPN to connect remote offices."
  ],
  "answer": "B. Routing between multiple VLANs on the same physical router interface."
},
{
  "question": "Which of the following is true when configuring HSRP on two routers?",
  "options": [
    "A. One router is active and the other is in standby mode.",
    "B. Both routers share the same IP address, which is used as the default gateway.",
    "C. Both routers share their respective MAC addresses to respond to traffic.",
    "D. HSRP is used to manage the IP addresses within a network's VLAN."
  ],
  "answer": "B. Both routers share the same IP address, which is used as the default gateway."
},
{
  "question": "Which of the following configurations would you use to create a redundant gateway setup using FHRP?",
  "options": [
    "A. Assign static IP addresses to each device.",
    "B. Use a Virtual IP (VIP) and configure HSRP or VRRP.",
    "C. Use a single dynamic IP address for each device.",
    "D. Configure the default gateway to point to a remote router."
  ],
  "answer": "B. Use a Virtual IP (VIP) and configure HSRP or VRRP."
},
{
  "question": "Which of the following is a feature of NAT overload?",
  "options": [
    "A. It allows multiple private IP addresses to map to a single public IP address.",
    "B. It provides a static mapping between private and public IP addresses.",
    "C. It assigns a unique public IP address to every internal device.",
    "D. It encrypts the IP addresses of devices within a network."
  ],
  "answer": "A. It allows multiple private IP addresses to map to a single public IP address."
},
{
  "question": "Which of the following protocols is commonly used to configure a router to allow multiple VLANs on a single physical interface?",
  "options": [
    "A. HSRP",
    "B. VRRP",
    "C. 802.1Q",
    "D. OSPF"
  ],
  "answer": "C. 802.1Q"
},
{
  "question": "Which of the following is an example of how subinterfaces are used on a router?",
  "options": [
    "A. To connect two physical routers.",
    "B. To assign multiple IP addresses to a single physical interface for different VLANs.",
    "C. To encrypt data traffic on a physical interface.",
    "D. To extend the physical interface to another network."
  ],
  "answer": "B. To assign multiple IP addresses to a single physical interface for different VLANs."
},
{
  "question": "Which of the following is the primary advantage of using NAT in a network?",
  "options": [
    "A. It allows devices to communicate across different network segments.",
    "B. It improves the security of a network by hiding internal IP addresses.",
    "C. It provides faster internet access for devices within a network.",
    "D. It assigns public IP addresses to each device in a network."
  ],
  "answer": "B. It improves the security of a network by hiding internal IP addresses."
},
{
  "question": "Which of the following protocols can be used to configure a default gateway redundancy with VIPs (Virtual IPs)?",
  "options": [
    "A. HSRP",
    "B. RIP",
    "C. EIGRP",
    "D. OSPF"
  ],
  "answer": "A. HSRP"
    },
    {
        "question": "What is the primary difference between **Pre-shared Key (PSK)** and **Enterprise authentication** in wireless networks?",
        "options": [
            "A. PSK uses a password shared among all users, while Enterprise uses unique credentials for each user",
            "B. PSK requires a server for authentication, while Enterprise does not",
            "C. PSK is used only in large networks, while Enterprise is used in small networks",
            "D. Enterprise authentication is more vulnerable than PSK"
        ],
        "answer": "A. PSK uses a password shared among all users, while Enterprise uses unique credentials for each user"
    },
    {
        "question": "Which of the following is true about **PSK** authentication?",
        "options": [
            "A. It is more secure than Enterprise authentication",
            "B. It uses a centralized authentication server",
            "C. It is suitable for small networks with a few devices",
            "D. It requires a RADIUS server"
        ],
        "answer": "C. It is suitable for small networks with a few devices"
    },
    {
        "question": "Which of the following is an advantage of **Enterprise** authentication over **PSK**?",
        "options": [
            "A. It is easier to implement and manage",
            "B. It allows for individual user credentials and stronger security",
            "C. It does not require a network administrator",
            "D. It requires fewer resources for authentication"
        ],
        "answer": "B. It allows for individual user credentials and stronger security"
    },
    {
        "question": "Which of the following protocols is commonly used for **Enterprise authentication** in wireless networks?",
        "options": [
            "A. WEP",
            "B. WPA2-PSK",
            "C. EAP",
            "D. RADIUS"
        ],
        "answer": "C. EAP"
    },
    {
        "question": "What is a key benefit of using **RADIUS** in **Enterprise** authentication?",
        "options": [
            "A. It allows users to authenticate using a shared password",
            "B. It centralizes authentication and provides detailed user access controls",
            "C. It provides automatic encryption of user credentials",
            "D. It is used exclusively for small networks"
        ],
        "answer": "B. It centralizes authentication and provides detailed user access controls"
    },
    {
        "question": "Which of the following best describes an **omnidirectional antenna**?",
        "options": [
            "A. It focuses the radio signal in a single direction",
            "B. It broadcasts signals in a 360-degree pattern around the antenna",
            "C. It requires a more complex configuration than directional antennas",
            "D. It only works at long distances"
        ],
        "answer": "B. It broadcasts signals in a 360-degree pattern around the antenna"
    },
    {
        "question": "What is the main characteristic of a **directional antenna**?",
        "options": [
            "A. It provides coverage in all directions equally",
            "B. It has a narrow focus, directing the signal in one specific direction",
            "C. It is used exclusively for short-range communications",
            "D. It can be used to prevent interference in wireless networks"
        ],
        "answer": "B. It has a narrow focus, directing the signal in one specific direction"
    },
    {
        "question": "In what situation would a **directional antenna** be preferred over an **omnidirectional antenna**?",
        "options": [
            "A. When wide coverage is needed across multiple areas",
            "B. When high-range communication is required in a specific direction",
            "C. When the network must provide coverage to a large group of devices",
            "D. When the signal needs to be equally distributed in all directions"
        ],
        "answer": "B. When high-range communication is required in a specific direction"
    },
    {
        "question": "Which type of antenna would be best suited for a **Wi-Fi network in a large open area**?",
        "options": [
            "A. Directional antenna",
            "B. Omnidirectional antenna",
            "C. Yagi antenna",
            "D. Parabolic antenna"
        ],
        "answer": "B. Omnidirectional antenna"
    },
    {
        "question": "What is the main difference between **autonomous** and **lightweight access points**?",
        "options": [
            "A. Autonomous access points rely on a controller, while lightweight access points do not",
            "B. Lightweight access points are easier to deploy and manage, while autonomous access points are more complex",
            "C. Autonomous access points require additional configuration, while lightweight access points are self-configuring",
            "D. Autonomous access points have better performance in large networks"
        ],
        "answer": "B. Lightweight access points are easier to deploy and manage, while autonomous access points are more complex"
    },
    {
        "question": "Which of the following is a feature of a **lightweight access point**?",
        "options": [
            "A. It requires an external controller to manage the configuration",
            "B. It does not support wireless management",
            "C. It operates independently without a controller",
            "D. It has limited configuration options compared to autonomous APs"
        ],
        "answer": "A. It requires an external controller to manage the configuration"
    },
    {
        "question": "Which type of access point is typically used in **large enterprise networks**?",
        "options": [
            "A. Autonomous access point",
            "B. Lightweight access point",
            "C. Wireless repeater",
            "D. Mesh access point"
        ],
        "answer": "B. Lightweight access point"
    },
    {
        "question": "Which of the following describes the advantage of using an **autonomous access point**?",
        "options": [
            "A. It simplifies deployment by relying on a central controller",
            "B. It is independent and does not require a controller for operation",
            "C. It supports only a limited number of wireless clients",
            "D. It requires less power to operate than lightweight APs"
        ],
        "answer": "B. It is independent and does not require a controller for operation"
    },
    {
        "question": "In which of the following scenarios would you most likely choose an **autonomous access point**?",
        "options": [
            "A. A small office with minimal wireless coverage requirements",
            "B. A large organization with a need for centralized management",
            "C. A wireless network in a densely populated area with high client density",
            "D. A campus with a high number of wireless access points managed centrally"
        ],
        "answer": "A. A small office with minimal wireless coverage requirements"
    },
    {
        "question": "What is the key characteristic of **lightweight access points** in a network?",
        "options": [
            "A. They require individual configuration and management",
            "B. They rely on a centralized controller for configuration and management",
            "C. They offer higher security features than autonomous access points",
            "D. They are suitable for small networks with minimal traffic"
        ],
        "answer": "B. They rely on a centralized controller for configuration and management"
    },
    {
        "question": "What is the role of a **controller** in a **lightweight access point** network?",
        "options": [
            "A. To provide wireless encryption",
            "B. To handle traffic routing between access points",
            "C. To manage and configure the lightweight access points",
            "D. To connect the access points to the wired network"
        ],
        "answer": "C. To manage and configure the lightweight access points"
    },
    {
        "question": "What is a common benefit of using **lightweight access points** in a wireless network?",
        "options": [
            "A. They reduce the cost of network infrastructure by removing the need for a controller",
            "B. They enable centralized management, making configuration and troubleshooting easier",
            "C. They provide higher data throughput than autonomous access points",
            "D. They require less power and are more energy-efficient"
        ],
        "answer": "B. They enable centralized management, making configuration and troubleshooting easier"
    },
    {
        "question": "Which of the following is a disadvantage of **autonomous access points** compared to **lightweight access points**?",
        "options": [
            "A. They require an external controller to operate",
            "B. They are more scalable and can manage large networks",
            "C. They require individual configuration for each access point",
            "D. They support fewer clients than lightweight access points"
        ],
        "answer": "C. They require individual configuration for each access point"
    },
    {
        "question": "Which type of access point would likely be used in **small businesses or homes**?",
        "options": [
            "A. Autonomous access point",
            "B. Lightweight access point",
            "C. Cloud-managed access point",
            "D. High-density access point"
        ],
        "answer": "A. Autonomous access point"
    },
    {
        "question": "Which of the following is a disadvantage of using **PSK** authentication in a wireless network?",
        "options": [
            "A. It requires a dedicated authentication server",
            "B. It is easier to crack if the shared key is weak or distributed incorrectly",
            "C. It is not supported by most consumer-grade devices",
            "D. It provides individual authentication for each user"
        ],
        "answer": "B. It is easier to crack if the shared key is weak or distributed incorrectly"
    },
    {
        "question": "Which antenna type would be most suitable for a **point-to-point** wireless connection?",
        "options": [
            "A. Omnidirectional antenna",
            "B. Directional antenna",
            "C. Parabolic antenna",
            "D. Patch antenna"
        ],
        "answer": "B. Directional antenna"
    },
    {
        "question": "Which authentication method is recommended for a **corporate Wi-Fi network** with high-security requirements?",
        "options": [
            "A. PSK",
            "B. WPA2-PSK",
            "C. EAP-TLS",
            "D. WEP"
        ],
        "answer": "C. EAP-TLS"
    },
    {
        "question": "Which of the following is **not** a characteristic of **lightweight access points**?",
        "options": [
            "A. They can be deployed without a central controller",
            "B. They are centrally managed for easier administration",
            "C. They offer scalability for larger networks",
            "D. They support features like roaming and load balancing"
        ],
        "answer": "A. They can be deployed without a central controller"
    },
    {
        "question": "What is the primary purpose of a **RADIUS server** in **Enterprise authentication**?",
        "options": [
            "A. To encrypt wireless signals",
            "B. To provide centralized authentication and authorization services",
            "C. To assign IP addresses to clients",
            "D. To manage the wireless network topology"
        ],
        "answer": "B. To provide centralized authentication and authorization services"
    },
    {
        "question": "What is the primary difference between **Pre-shared Key (PSK)** and **Enterprise authentication** in wireless networks?",
        "options": [
            "A. PSK uses a password shared among all users, while Enterprise uses unique credentials for each user",
            "B. PSK requires a server for authentication, while Enterprise does not",
            "C. PSK is used only in large networks, while Enterprise is used in small networks",
            "D. Enterprise authentication is more vulnerable than PSK"
        ],
        "answer": "A. PSK uses a password shared among all users, while Enterprise uses unique credentials for each user"
    },
    {
        "question": "Which of the following is true about **PSK** authentication?",
        "options": [
            "A. It is more secure than Enterprise authentication",
            "B. It uses a centralized authentication server",
            "C. It is suitable for small networks with a few devices",
            "D. It requires a RADIUS server"
        ],
        "answer": "C. It is suitable for small networks with a few devices"
    },
    {
        "question": "Which of the following is an advantage of **Enterprise** authentication over **PSK**?",
        "options": [
            "A. It is easier to implement and manage",
            "B. It allows for individual user credentials and stronger security",
            "C. It does not require a network administrator",
            "D. It requires fewer resources for authentication"
        ],
        "answer": "B. It allows for individual user credentials and stronger security"
    },
    {
        "question": "Which of the following protocols is commonly used for **Enterprise authentication** in wireless networks?",
        "options": [
            "A. WEP",
            "B. WPA2-PSK",
            "C. EAP",
            "D. RADIUS"
        ],
        "answer": "C. EAP"
    },
    {
        "question": "What is a key benefit of using **RADIUS** in **Enterprise** authentication?",
        "options": [
            "A. It allows users to authenticate using a shared password",
            "B. It centralizes authentication and provides detailed user access controls",
            "C. It provides automatic encryption of user credentials",
            "D. It is used exclusively for small networks"
        ],
        "answer": "B. It centralizes authentication and provides detailed user access controls"
    },
    {
        "question": "Which of the following best describes an **omnidirectional antenna**?",
        "options": [
            "A. It focuses the radio signal in a single direction",
            "B. It broadcasts signals in a 360-degree pattern around the antenna",
            "C. It requires a more complex configuration than directional antennas",
            "D. It only works at long distances"
        ],
        "answer": "B. It broadcasts signals in a 360-degree pattern around the antenna"
    },
    {
        "question": "What is the main characteristic of a **directional antenna**?",
        "options": [
            "A. It provides coverage in all directions equally",
            "B. It has a narrow focus, directing the signal in one specific direction",
            "C. It is used exclusively for short-range communications",
            "D. It can be used to prevent interference in wireless networks"
        ],
        "answer": "B. It has a narrow focus, directing the signal in one specific direction"
    },
    {
        "question": "In what situation would a **directional antenna** be preferred over an **omnidirectional antenna**?",
        "options": [
            "A. When wide coverage is needed across multiple areas",
            "B. When high-range communication is required in a specific direction",
            "C. When the network must provide coverage to a large group of devices",
            "D. When the signal needs to be equally distributed in all directions"
        ],
        "answer": "B. When high-range communication is required in a specific direction"
    },
    {
        "question": "Which type of antenna would be best suited for a **Wi-Fi network in a large open area**?",
        "options": [
            "A. Directional antenna",
            "B. Omnidirectional antenna",
            "C. Yagi antenna",
            "D. Parabolic antenna"
        ],
        "answer": "B. Omnidirectional antenna"
    },
    {
        "question": "What is the main difference between **autonomous** and **lightweight access points**?",
        "options": [
            "A. Autonomous access points rely on a controller, while lightweight access points do not",
            "B. Lightweight access points are easier to deploy and manage, while autonomous access points are more complex",
            "C. Autonomous access points require additional configuration, while lightweight access points are self-configuring",
            "D. Autonomous access points have better performance in large networks"
        ],
        "answer": "B. Lightweight access points are easier to deploy and manage, while autonomous access points are more complex"
    },
    {
        "question": "Which of the following is a feature of a **lightweight access point**?",
        "options": [
            "A. It requires an external controller to manage the configuration",
            "B. It does not support wireless management",
            "C. It operates independently without a controller",
            "D. It has limited configuration options compared to autonomous APs"
        ],
        "answer": "A. It requires an external controller to manage the configuration"
    },
    {
        "question": "Which type of access point is typically used in **large enterprise networks**?",
        "options": [
            "A. Autonomous access point",
            "B. Lightweight access point",
            "C. Wireless repeater",
            "D. Mesh access point"
        ],
        "answer": "B. Lightweight access point"
    },
    {
        "question": "Which of the following describes the advantage of using an **autonomous access point**?",
        "options": [
            "A. It simplifies deployment by relying on a central controller",
            "B. It is independent and does not require a controller for operation",
            "C. It supports only a limited number of wireless clients",
            "D. It requires less power to operate than lightweight APs"
        ],
        "answer": "B. It is independent and does not require a controller for operation"
    },
    {
        "question": "In which of the following scenarios would you most likely choose an **autonomous access point**?",
        "options": [
            "A. A small office with minimal wireless coverage requirements",
            "B. A large organization with a need for centralized management",
            "C. A wireless network in a densely populated area with high client density",
            "D. A campus with a high number of wireless access points managed centrally"
        ],
        "answer": "A. A small office with minimal wireless coverage requirements"
    },
    {
        "question": "What is the key characteristic of **lightweight access points** in a network?",
        "options": [
            "A. They require individual configuration and management",
            "B. They rely on a centralized controller for configuration and management",
            "C. They offer higher security features than autonomous access points",
            "D. They are suitable for small networks with minimal traffic"
        ],
        "answer": "B. They rely on a centralized controller for configuration and management"
    },
    {
        "question": "What is the role of a **controller** in a **lightweight access point** network?",
        "options": [
            "A. To provide wireless encryption",
            "B. To handle traffic routing between access points",
            "C. To manage and configure the lightweight access points",
            "D. To connect the access points to the wired network"
        ],
        "answer": "C. To manage and configure the lightweight access points"
    },
    {
        "question": "What is a common benefit of using **lightweight access points** in a wireless network?",
        "options": [
            "A. They reduce the cost of network infrastructure by removing the need for a controller",
            "B. They enable centralized management, making configuration and troubleshooting easier",
            "C. They provide higher data throughput than autonomous access points",
            "D. They require less power and are more energy-efficient"
        ],
        "answer": "B. They enable centralized management, making configuration and troubleshooting easier"
    },
    {
        "question": "Which of the following is a disadvantage of **autonomous access points** compared to **lightweight access points**?",
        "options": [
            "A. They require an external controller to operate",
            "B. They are more scalable and can manage large networks",
            "C. They require individual configuration for each access point",
            "D. They support fewer clients than lightweight access points"
        ],
        "answer": "C. They require individual configuration for each access point"
    },
    {
        "question": "Which type of access point would likely be used in **small businesses or homes**?",
        "options": [
            "A. Autonomous access point",
            "B. Lightweight access point",
            "C. Cloud-managed access point",
            "D. High-density access point"
        ],
        "answer": "A. Autonomous access point"
    },
    {
        "question": "Which of the following is a disadvantage of using **PSK** authentication in a wireless network?",
        "options": [
            "A. It requires a dedicated authentication server",
            "B. It is easier to crack if the shared key is weak or distributed incorrectly",
            "C. It is not supported by most consumer-grade devices",
            "D. It provides individual authentication for each user"
        ],
        "answer": "B. It is easier to crack if the shared key is weak or distributed incorrectly"
    },
    {
        "question": "Which antenna type would be most suitable for a **point-to-point** wireless connection?",
        "options": [
            "A. Omnidirectional antenna",
            "B. Directional antenna",
            "C. Parabolic antenna",
            "D. Patch antenna"
        ],
        "answer": "B. Directional antenna"
    },
    {
        "question": "Which authentication method is recommended for a **corporate Wi-Fi network** with high-security requirements?",
        "options": [
            "A. PSK",
            "B. WPA2-PSK",
            "C. EAP-TLS",
            "D. WEP"
        ],
        "answer": "C. EAP-TLS"
    },
    {
        "question": "Which of the following is **not** a characteristic of **lightweight access points**?",
        "options": [
            "A. They can be deployed without a central controller",
            "B. They are centrally managed for easier administration",
            "C. They offer scalability for larger networks",
            "D. They support features like roaming and load balancing"
        ],
        "answer": "A. They can be deployed without a central controller"
    },
    {
        "question": "What is the primary purpose of a **RADIUS server** in **Enterprise authentication**?",
        "options": [
            "A. To encrypt wireless signals",
            "B. To provide centralized authentication and authorization services",
            "C. To assign IP addresses to clients",
            "D. To manage the wireless network topology"
        ],
        "answer": "B. To provide centralized authentication and authorization services"
    },
    {
        "question": "What is the primary purpose of **802.1Q tagging** in Ethernet frames?",
        "options": [
            "A. To prioritize voice traffic over data traffic",
            "B. To allow multiple VLANs to exist on a single physical link",
            "C. To increase the maximum frame size for jumbo frames",
            "D. To perform error correction for data frames"
        ],
        "answer": "B. To allow multiple VLANs to exist on a single physical link"
    },
    {
        "question": "Which of the following is true about **802.1Q tagging**?",
        "options": [
            "A. It encapsulates the Ethernet frame in a TCP header",
            "B. It inserts a 4-byte tag between the source MAC address and the EtherType field",
            "C. It encrypts the Ethernet frame for secure transmission",
            "D. It uses a 16-bit field for VLAN tagging"
        ],
        "answer": "B. It inserts a 4-byte tag between the source MAC address and the EtherType field"
    },
    {
        "question": "What does **link aggregation** allow for in a network?",
        "options": [
            "A. It allows for redundant connections and combines multiple physical links into a single logical link",
            "B. It creates separate virtual networks over the same physical link",
            "C. It splits traffic across multiple network segments for load balancing",
            "D. It aggregates multiple VLANs onto one trunk link"
        ],
        "answer": "A. It allows for redundant connections and combines multiple physical links into a single logical link"
    },
    {
        "question": "Which protocol is commonly used to implement **link aggregation**?",
        "options": [
            "A. Spanning Tree Protocol (STP)",
            "B. Port Aggregation Protocol (PAgP)",
            "C. Rapid Spanning Tree Protocol (RSTP)",
            "D. Internet Group Management Protocol (IGMP)"
        ],
        "answer": "B. Port Aggregation Protocol (PAgP)"
    },
    {
        "question": "What is the effect of setting the **speed** of a network interface to 1000 Mbps?",
        "options": [
            "A. The interface can transfer data at a maximum rate of 1 Gbps",
            "B. The interface can transfer data at a maximum rate of 100 Mbps",
            "C. The interface can transfer data at a maximum rate of 10 Mbps",
            "D. The interface can only support data transfer at half-duplex"
        ],
        "answer": "A. The interface can transfer data at a maximum rate of 1 Gbps"
    },
    {
        "question": "Which of the following is true about the **duplex** setting on a network interface?",
        "options": [
            "A. Half-duplex allows for simultaneous two-way communication, while full-duplex only allows one-way communication",
            "B. Full-duplex allows for simultaneous two-way communication, while half-duplex only allows one-way communication",
            "C. Both half-duplex and full-duplex allow for one-way communication only",
            "D. Duplex settings are irrelevant in modern Ethernet networks"
        ],
        "answer": "B. Full-duplex allows for simultaneous two-way communication, while half-duplex only allows one-way communication"
    },
    {
        "question": "What is the primary purpose of the **Spanning Tree Protocol (STP)**?",
        "options": [
            "A. To prevent routing loops in a network",
            "B. To block redundant paths and prevent loops in Ethernet networks",
            "C. To aggregate multiple network links for higher throughput",
            "D. To control the flow of multicast traffic in a network"
        ],
        "answer": "B. To block redundant paths and prevent loops in Ethernet networks"
    },
    {
        "question": "What does **STP** use to determine the best path for data transmission?",
        "options": [
            "A. MAC address table",
            "B. VLAN configuration",
            "C. Bridge protocol data units (BPDU)",
            "D. IP routing table"
        ],
        "answer": "C. Bridge protocol data units (BPDU)"
    },
    {
        "question": "Which of the following best describes the **Maximum Transmission Unit (MTU)**?",
        "options": [
            "A. The minimum frame size allowed in a network",
            "B. The maximum size of a packet that can be transmitted over a network",
            "C. The maximum number of hops a packet can take between devices",
            "D. The number of devices in a subnet"
        ],
        "answer": "B. The maximum size of a packet that can be transmitted over a network"
    },
    {
        "question": "What is the **default MTU** size for Ethernet frames?",
        "options": [
            "A. 1500 bytes",
            "B. 1000 bytes",
            "C. 9000 bytes",
            "D. 2000 bytes"
        ],
        "answer": "A. 1500 bytes"
    },
    {
        "question": "Which of the following is true about **jumbo frames**?",
        "options": [
            "A. They are used to increase the size of the Ethernet frame to above 1500 bytes, typically up to 9000 bytes",
            "B. They are used to decrease the size of Ethernet frames to improve network performance",
            "C. They reduce the number of hops a packet must take in a network",
            "D. They are used for encrypted network traffic"
        ],
        "answer": "A. They are used to increase the size of the Ethernet frame to above 1500 bytes, typically up to 9000 bytes"
    },
    {
        "question": "Which of the following is a potential drawback of using **jumbo frames**?",
        "options": [
            "A. They can cause higher network latency due to their size",
            "B. They can result in frame fragmentation if network devices do not support larger frames",
            "C. They improve security by reducing the number of frames sent",
            "D. They are incompatible with modern switches"
        ],
        "answer": "B. They can result in frame fragmentation if network devices do not support larger frames"
    },
    {
        "question": "Which of the following commands is used to **enable 802.1Q trunking** on a Cisco switch port?",
        "options": [
            "A. switchport mode trunk",
            "B. trunk enable 802.1Q",
            "C. switchport trunk vlan 10",
            "D. set trunk 802.1Q"
        ],
        "answer": "A. switchport mode trunk"
    },
    {
        "question": "Which of the following is true about **link aggregation** with **EtherChannel**?",
        "options": [
            "A. It allows for a single logical link between two devices using multiple physical links",
            "B. It allows for splitting traffic across multiple subnets",
            "C. It allows for automatic IP address allocation between switches",
            "D. It uses IP addresses to group physical links"
        ],
        "answer": "A. It allows for a single logical link between two devices using multiple physical links"
    },
    {
        "question": "What is the maximum number of ports that can be grouped together in a **Cisco EtherChannel** configuration?",
        "options": [
            "A. 8",
            "B. 16",
            "C. 4",
            "D. 12"
        ],
        "answer": "A. 8"
    },
    {
        "question": "In **802.1Q tagging**, what is the purpose of the **VLAN Identifier (VID)**?",
        "options": [
            "A. It identifies the type of traffic (e.g., data or voice)",
            "B. It specifies the source and destination MAC addresses of the frame",
            "C. It identifies the VLAN to which the frame belongs",
            "D. It indicates the type of physical media being used"
        ],
        "answer": "C. It identifies the VLAN to which the frame belongs"
    },
    {
        "question": "What is the primary benefit of using **jumbo frames** in high-throughput networks?",
        "options": [
            "A. They reduce the overhead of sending many small frames, increasing overall network efficiency",
            "B. They provide better security by encrypting larger packets",
            "C. They improve the reliability of wireless connections",
            "D. They reduce the number of switches required in a network"
        ],
        "answer": "A. They reduce the overhead of sending many small frames, increasing overall network efficiency"
    },
    {
        "question": "What command is used to configure **link aggregation** using **PAgP** on a Cisco switch?",
        "options": [
            "A. channel-group 1 mode desirable",
            "B. etherchannel-group 1 mode active",
            "C. switchport mode link-aggregate",
            "D. channel-group 1 mode auto"
        ],
        "answer": "A. channel-group 1 mode desirable"
    },
    {
        "question": "What does the **STP** protocol use to elect the **root bridge**?",
        "options": [
            "A. Lowest MAC address",
            "B. Highest IP address",
            "C. Lowest IP address",
            "D. Highest MAC address"
        ],
        "answer": "A. Lowest MAC address"
    },
    {
        "question": "What is the maximum **MTU** size supported by most modern Ethernet networks?",
        "options": [
            "A. 1500 bytes",
            "B. 9000 bytes",
            "C. 3000 bytes",
            "D. 2000 bytes"
        ],
        "answer": "B. 9000 bytes"
    },
    {
        "question": "Which of the following statements is **true** about **duplex mode** in Ethernet networks?",
        "options": [
            "A. Full-duplex communication allows devices to send and receive data simultaneously",
            "B. Half-duplex communication allows devices to send and receive data simultaneously",
            "C. Duplex mode is not supported on Gigabit Ethernet",
            "D. Duplex settings should be manually configured for every connection"
        ],
        "answer": "A. Full-duplex communication allows devices to send and receive data simultaneously"
    },
    {
        "question": "What is the primary purpose of the **spanning tree** in Ethernet networks?",
        "options": [
            "A. To prevent broadcast storms",
            "B. To manage the allocation of IP addresses",
            "C. To detect faulty hardware in the network",
            "D. To prevent loops and redundant paths"
        ],
        "answer": "D. To prevent loops and redundant paths"
    },
    {
        "question": "Which of the following is true about the **VLAN database** in Cisco switches?",
        "options": [
            "A. The VLAN database contains information about the MAC addresses of devices in each VLAN",
            "B. The VLAN database can only store a maximum of 100 VLANs on a switch",
            "C. The VLAN database is used to store information about VLANs and their associated ports",
            "D. The VLAN database is used to store IP address information"
        ],
        "answer": "C. The VLAN database is used to store information about VLANs and their associated ports"
    },
    {
        "question": "What happens when you create a VLAN on a Cisco switch?",
        "options": [
            "A. The switch automatically assigns all ports to the new VLAN",
            "B. The switch creates an SVI for the VLAN automatically",
            "C. The switch configures a default IP address for the VLAN",
            "D. The VLAN is added to the VLAN database and associated with ports manually"
        ],
        "answer": "D. The VLAN is added to the VLAN database and associated with ports manually"
    },
    {
        "question": "In a **trunking** configuration, which VLAN carries untagged traffic?",
        "options": [
            "A. The Native VLAN",
            "B. The Voice VLAN",
            "C. The Management VLAN",
            "D. The Default VLAN"
        ],
        "answer": "A. The Native VLAN"
    },
    {
        "question": "Which of the following is the correct command to assign a port to a **Voice VLAN**?",
        "options": [
            "A. switchport mode voice vlan 10",
            "B. switchport voice vlan 10",
            "C. voice vlan 10",
            "D. switchport vlan 10 voice"
        ],
        "answer": "B. switchport voice vlan 10"
    },
    {
        "question": "What does the **`show vlan brief`** command display on a Cisco switch?",
        "options": [
            "A. A list of all VLANs configured on the switch, their associated ports, and their status",
            "B. A detailed report on the interface configurations for each VLAN",
            "C. The routing table for each VLAN",
            "D. Information on the VLAN interfaces and IP addresses"
        ],
        "answer": "A. A list of all VLANs configured on the switch, their associated ports, and their status"
    },
    {
        "question": "How do you assign an **SVI (Switch Virtual Interface)** to a VLAN on a Cisco switch?",
        "options": [
            "A. By using the command 'interface vlan 10'",
            "B. By configuring a trunk port with the VLAN ID",
            "C. By configuring the VLAN as the native VLAN",
            "D. By assigning an IP address to the VLAN database"
        ],
        "answer": "A. By using the command 'interface vlan 10'"
    },
    {
        "question": "Which of the following is the **default behavior** for VLANs on a Cisco switch?",
        "options": [
            "A. All VLANs are assigned to all switch ports by default",
            "B. VLAN 1 is assigned to all switch ports by default",
            "C. VLANs are automatically configured as trunk ports",
            "D. All ports are untagged by default and belong to VLAN 10"
        ],
        "answer": "B. VLAN 1 is assigned to all switch ports by default"
    },
    {
        "question": "What type of **VLAN** is typically used for **management purposes** on a Cisco switch?",
        "options": [
            "A. VLAN 1",
            "B. VLAN 99",
            "C. Voice VLAN",
            "D. Native VLAN"
        ],
        "answer": "B. VLAN 99"
    },
    {
        "question": "What is the purpose of using a **Voice VLAN** in a network?",
        "options": [
            "A. To allow voice traffic to bypass the data VLAN and increase performance",
            "B. To encrypt voice traffic and protect its confidentiality",
            "C. To enable QoS for voice traffic by marking it with a higher priority",
            "D. To separate voice and data traffic physically"
        ],
        "answer": "C. To enable QoS for voice traffic by marking it with a higher priority"
    },
    {
        "question": "Which command would you use to verify **trunking** information on a Cisco switch port?",
        "options": [
            "A. show interface trunk",
            "B. show vlan brief",
            "C. show interfaces vlan 10",
            "D. show ip route"
        ],
        "answer": "A. show interface trunk"
    },
    {
        "question": "What is the primary difference between a **Native VLAN** and a **Voice VLAN**?",
        "options": [
            "A. Native VLAN is used to transport data traffic while Voice VLAN is used to prioritize voice traffic",
            "B. Native VLAN handles encryption while Voice VLAN is for unencrypted traffic",
            "C. Native VLAN is used only for wireless networks, while Voice VLAN is for wired networks",
            "D. Native VLAN does not require QoS configuration, while Voice VLAN does"
        ],
        "answer": "A. Native VLAN is used to transport data traffic while Voice VLAN is used to prioritize voice traffic"
    },
    {
        "question": "When configuring a switch port, what does the **`switchport mode access`** command do?",
        "options": [
            "A. It configures the port as a trunk port",
            "B. It configures the port to allow only a single VLAN",
            "C. It allows the port to be used for both data and voice traffic",
            "D. It disables all VLANs on the port"
        ],
        "answer": "B. It configures the port to allow only a single VLAN"
    },
    {
        "question": "What does the **`switchport trunk allowed vlan`** command do?",
        "options": [
            "A. It defines which VLANs are allowed on the trunk link",
            "B. It assigns a VLAN to a port",
            "C. It sets the native VLAN for the trunk link",
            "D. It creates a new VLAN on the switch"
        ],
        "answer": "A. It defines which VLANs are allowed on the trunk link"
    },
    {
        "question": "Which of the following commands is used to assign an **IP address** to an **SVI** on a Cisco switch?",
        "options": [
            "A. ip address 192.168.1.1 255.255.255.0",
            "B. interface vlan 10",
            "C. ip routing",
            "D. interface vlan 10 ip address"
        ],
        "answer": "A. ip address 192.168.1.1 255.255.255.0"
    },
    {
        "question": "What is the typical use of **SVIs** on a switch?",
        "options": [
            "A. To provide inter-VLAN routing",
            "B. To configure routing protocols on a switch",
            "C. To assign a VLAN to a specific port",
            "D. To connect switches together in a network"
        ],
        "answer": "A. To provide inter-VLAN routing"
    },
    {
        "question": "Which type of **VLAN** is commonly used for **Voice over IP (VoIP)** devices?",
        "options": [
            "A. Data VLAN",
            "B. Management VLAN",
            "C. Voice VLAN",
            "D. Guest VLAN"
        ],
        "answer": "C. Voice VLAN"
    },
    {
        "question": "Which of the following is true about the **Native VLAN** on a trunk link?",
        "options": [
            "A. It is always VLAN 1",
            "B. It should be used to carry only untagged traffic",
            "C. It requires encryption for security",
            "D. It should be configured on access ports only"
        ],
        "answer": "B. It should be used to carry only untagged traffic"
    },
    {
        "question": "What is the correct syntax to **delete a VLAN** on a Cisco switch?",
        "options": [
            "A. no vlan 10",
            "B. delete vlan 10",
            "C. no vlan database",
            "D. erase vlan 10"
        ],
        "answer": "A. no vlan 10"
    },
    {
        "question": "Which of the following is the correct command to configure the **Native VLAN** on a trunk port?",
        "options": [
            "A. switchport trunk native vlan 10",
            "B. switchport mode native vlan 10",
            "C. vlan 10 native port",
            "D. trunk vlan native 10"
        ],
        "answer": "A. switchport trunk native vlan 10"
    },
    {
        "question": "What is the primary purpose of the **VLAN database** in a Cisco switch?",
        "options": [
            "A. To store information about IP routing",
            "B. To store information about which VLANs are configured on the switch and which ports belong to them",
            "C. To store IP addresses for all devices in the VLAN",
            "D. To store information about switch port configurations"
        ],
        "answer": "B. To store information about which VLANs are configured on the switch and which ports belong to them"
    },
    {
        "question": "When configuring a **Voice VLAN**, what does the **`switchport voice vlan`** command do?",
        "options": [
            "A. It configures the Voice VLAN on an interface to prioritize voice traffic",
            "B. It defines the VLAN number for voice devices",
            "C. It enables voice traffic over a trunk link",
            "D. It enables QoS for voice traffic on the port"
        ],
        "answer": "A. It configures the Voice VLAN on an interface to prioritize voice traffic"
    },
    {
        "question": "What is the primary purpose of a **VLAN** (Virtual Local Area Network)?",
        "options": [
            "A. To increase network bandwidth",
            "B. To segment a large network into smaller, manageable broadcast domains",
            "C. To secure network communications through encryption",
            "D. To provide remote access to the network"
        ],
        "answer": "B. To segment a large network into smaller, manageable broadcast domains"
    },
    {
        "question": "Which of the following is stored in the **VLAN database** on a switch?",
        "options": [
            "A. IP addresses of all network devices",
            "B. MAC addresses of all devices in the network",
            "C. VLAN IDs and associated ports",
            "D. Routing information for the network"
        ],
        "answer": "C. VLAN IDs and associated ports"
    },
    {
        "question": "What does a **Switch Virtual Interface (SVI)** provide?",
        "options": [
            "A. A physical interface for connecting devices to a switch",
            "B. A virtual interface that allows a switch to participate in routing and Layer 3 functionality",
            "C. A protocol for VLAN management",
            "D. A virtual IP address for each port on the switch"
        ],
        "answer": "B. A virtual interface that allows a switch to participate in routing and Layer 3 functionality"
    },
    {
        "question": "Which of the following is the default VLAN on most switches?",
        "options": [
            "A. VLAN 1",
            "B. VLAN 10",
            "C. VLAN 20",
            "D. VLAN 100"
        ],
        "answer": "A. VLAN 1"
    },
    {
        "question": "Which type of interface is used to configure an SVI for a VLAN on a switch?",
        "options": [
            "A. Physical interface",
            "B. Loopback interface",
            "C. Virtual interface",
            "D. Management interface"
        ],
        "answer": "C. Virtual interface"
    },
    {
        "question": "Which of the following commands is used to create a VLAN on a Cisco switch?",
        "options": [
            "A. vlan create 10",
            "B. vlan 10",
            "C. vlan database",
            "D. create vlan 10"
        ],
        "answer": "B. vlan 10"
    },
    {
        "question": "What is the role of the **Native VLAN** in a trunk port configuration?",
        "options": [
            "A. It is used for tagging frames on the trunk port",
            "B. It is the default VLAN for untagged frames on the trunk",
            "C. It is used to assign IP addresses to VLANs",
            "D. It is used to encrypt data on trunk links"
        ],
        "answer": "B. It is the default VLAN for untagged frames on the trunk"
    },
    {
        "question": "Which of the following statements about the **Voice VLAN** is true?",
        "options": [
            "A. It prioritizes voice traffic over other data traffic",
            "B. It is configured to handle encrypted voice communications",
            "C. It is typically configured for video conferencing traffic",
            "D. It is used to separate guest network traffic from internal traffic"
        ],
        "answer": "A. It prioritizes voice traffic over other data traffic"
    },
    {
        "question": "Which of the following is the correct syntax to assign a port to a VLAN on a Cisco switch?",
        "options": [
            "A. switchport mode access vlan 10",
            "B. switchport vlan 10",
            "C. vlan 10 access port",
            "D. port vlan 10"
        ],
        "answer": "A. switchport mode access vlan 10"
    },
    {
        "question": "When configuring a **Voice VLAN**, which of the following is the most common method to implement QoS (Quality of Service)?",
        "options": [
            "A. By assigning a high priority to voice traffic using **802.1p tagging**",
            "B. By isolating the voice VLAN using private VLANs",
            "C. By configuring **VPNs** for voice traffic",
            "D. By using encryption for voice traffic"
        ],
        "answer": "A. By assigning a high priority to voice traffic using **802.1p tagging**"
    },
    {
        "question": "What is the purpose of the **VLAN database** in a Cisco switch?",
        "options": [
            "A. To store information about IP routing paths",
            "B. To manage the list of VLANs that can be assigned to switch ports",
            "C. To manage the security configurations for VLANs",
            "D. To configure IP addresses on each VLAN"
        ],
        "answer": "B. To manage the list of VLANs that can be assigned to switch ports"
    },
    {
        "question": "Which command is used to assign a **VLAN** to a trunk port on a switch?",
        "options": [
            "A. switchport mode trunk vlan 10",
            "B. switchport trunk allowed vlan 10",
            "C. trunk vlan 10",
            "D. vlan trunk mode 10"
        ],
        "answer": "B. switchport trunk allowed vlan 10"
    },
    {
        "question": "Which VLAN range is used for **private VLANs**?",
        "options": [
            "A. VLAN 1-1005",
            "B. VLAN 1006-4095",
            "C. VLAN 2-10",
            "D. VLAN 1000-2000"
        ],
        "answer": "B. VLAN 1006-4095"
    },
    {
        "question": "Which command is used to configure an **SVI** on a Cisco switch?",
        "options": [
            "A. interface vlan 10",
            "B. interface trunk 10",
            "C. vlan 10",
            "D. interface access 10"
        ],
        "answer": "A. interface vlan 10"
    },
    {
        "question": "Which of the following is the purpose of the **native VLAN** in a trunk configuration?",
        "options": [
            "A. To allow both tagged and untagged traffic on a trunk link",
            "B. To isolate traffic between VLANs on a switch",
            "C. To provide default routing for network traffic",
            "D. To define the maximum number of VLANs a trunk link can carry"
        ],
        "answer": "A. To allow both tagged and untagged traffic on a trunk link"
    },
    {
        "question": "What is typically the **Voice VLAN** used for in a network?",
        "options": [
            "A. To ensure voice communication gets priority over other traffic",
            "B. To provide encryption for voice calls",
            "C. To segment voice and data traffic into separate networks",
            "D. To enable secure communication between telephony devices"
        ],
        "answer": "A. To ensure voice communication gets priority over other traffic"
    },
    {
        "question": "Which of the following statements is true about **Switch Virtual Interface (SVI)**?",
        "options": [
            "A. An SVI is used to route traffic between different VLANs",
            "B. An SVI is created automatically when a physical interface is configured",
            "C. An SVI is used to manage the physical ports on a switch",
            "D. An SVI can be assigned an IP address only on Layer 2 switches"
        ],
        "answer": "A. An SVI is used to route traffic between different VLANs"
    },
    {
        "question": "When configuring an interface for the **Voice VLAN**, which of the following is typically configured?",
        "options": [
            "A. An 802.1p priority level for voice traffic",
            "B. A unique IP address for voice communication",
            "C. A separate cable for voice traffic",
            "D. Encryption for voice communication"
        ],
        "answer": "A. An 802.1p priority level for voice traffic"
    },
    {
        "question": "Which command is used to verify the **SVI configuration** on a Cisco switch?",
        "options": [
            "A. show interface vlan 10",
            "B. show vlan brief",
            "C. show ip route",
            "D. show ip interface brief"
        ],
        "answer": "A. show interface vlan 10"
    },
    {
        "question": "What does the command `switchport voice vlan 10` do on a switch interface?",
        "options": [
            "A. Assigns VLAN 10 as the Voice VLAN on the port",
            "B. Disables the Voice VLAN on the port",
            "C. Configures VLAN 10 for data traffic only",
            "D. Sets VLAN 10 as the Native VLAN on the port"
        ],
        "answer": "A. Assigns VLAN 10 as the Voice VLAN on the port"
    },
    {
        "question": "Which of the following commands would you use to configure a **VLAN** on a Cisco switch?",
        "options": [
            "A. vlan create 10",
            "B. switchport vlan 10",
            "C. interface vlan 10",
            "D. vlan 10"
        ],
        "answer": "D. vlan 10"
    },
    {
        "question": "Which of the following commands can be used to check the configuration of VLANs on a switch?",
        "options": [
            "A. show ip interface brief",
            "B. show vlan brief",
            "C. show interfaces trunk",
            "D. show running-config"
        ],
        "answer": "B. show vlan brief"
    },
    {
        "question": "What is the primary function of NAT (Network Address Translation)?",
        "options": [
            "A. To convert public IP addresses into private IP addresses",
            "B. To assign dynamic IP addresses to devices on the network",
            "C. To map private IP addresses to public IP addresses",
            "D. To encrypt data transmitted over the network"
        ],
        "answer": "C. To map private IP addresses to public IP addresses"
    },
    {
        "question": "Which of the following is true about Port Address Translation (PAT)?",
        "options": [
            "A. PAT maps multiple private IP addresses to a single public IP address",
            "B. PAT requires a pool of public IP addresses",
            "C. PAT can only translate port numbers, not IP addresses",
            "D. PAT is only used for IPv6 address translation"
        ],
        "answer": "A. PAT maps multiple private IP addresses to a single public IP address"
    },
    {
        "question": "Which of the following is an advantage of using NAT in a network?",
        "options": [
            "A. NAT reduces the need for public IP addresses",
            "B. NAT allows devices to directly communicate over the internet",
            "C. NAT eliminates the need for subnetting",
            "D. NAT increases the security by encrypting data"
        ],
        "answer": "A. NAT reduces the need for public IP addresses"
    },
    {
        "question": "In a scenario using PAT, which component in a network needs to manage the translation of private IP addresses to a single public IP address?",
        "options": [
            "A. Router",
            "B. Switch",
            "C. Firewall",
            "D. DNS server"
        ],
        "answer": "A. Router"
    },
    {
        "question": "Which of the following is NOT an example of First Hop Redundancy Protocol (FHRP)?",
        "options": [
            "A. HSRP (Hot Standby Router Protocol)",
            "B. VRRP (Virtual Router Redundancy Protocol)",
            "C. GLBP (Gateway Load Balancing Protocol)",
            "D. OSPF (Open Shortest Path First)"
        ],
        "answer": "D. OSPF (Open Shortest Path First)"
    },
    {
        "question": "What is the main purpose of **Virtual IP (VIP)** in FHRP configurations?",
        "options": [
            "A. To allow multiple devices to share the same IP address",
            "B. To configure a failover mechanism for routers",
            "C. To assign a static IP address to a router",
            "D. To provide DNS services"
        ],
        "answer": "B. To configure a failover mechanism for routers"
    },
    {
        "question": "In a **HSRP** (Hot Standby Router Protocol) configuration, which router is responsible for responding to ARP requests for the Virtual IP (VIP)?",
        "options": [
            "A. Active router",
            "B. Standby router",
            "C. Both Active and Standby routers",
            "D. The router with the highest priority"
        ],
        "answer": "A. Active router"
    },
    {
        "question": "Which of the following protocols supports load balancing between multiple routers in an FHRP setup?",
        "options": [
            "A. HSRP",
            "B. VRRP",
            "C. GLBP",
            "D. RIPv2"
        ],
        "answer": "C. GLBP"
    },
    {
        "question": "In a **Virtual IP (VIP)** scenario, which of the following statements is true?",
        "options": [
            "A. A VIP is used to load balance traffic between routers",
            "B. A VIP is a physical address assigned to a specific router",
            "C. A VIP allows a group of routers to appear as a single device to the network",
            "D. A VIP is assigned to a server to handle multiple requests"
        ],
        "answer": "C. A VIP allows a group of routers to appear as a single device to the network"
    },
    {
        "question": "Which of the following best describes a **subinterface**?",
        "options": [
            "A. A logical interface used to represent multiple devices on the same physical interface",
            "B. A physical interface used to connect to other network segments",
            "C. A backup interface used when the primary interface fails",
            "D. A virtual interface used to manage routing tables"
        ],
        "answer": "A. A logical interface used to represent multiple devices on the same physical interface"
    },
    {
        "question": "In which scenario would a network administrator use **subinterfaces**?",
        "options": [
            "A. To segment a physical network into smaller broadcast domains",
            "B. To assign multiple IP addresses to a single physical interface",
            "C. To connect multiple routers to the same LAN",
            "D. To configure the routing protocol on the network"
        ],
        "answer": "B. To assign multiple IP addresses to a single physical interface"
    },
    {
        "question": "Which of the following is a key advantage of using NAT in a home network?",
        "options": [
            "A. It allows multiple devices to share a single public IP address",
            "B. It provides high-speed data transfer across the network",
            "C. It prevents malware from spreading across devices",
            "D. It encrypts data transmitted between devices"
        ],
        "answer": "A. It allows multiple devices to share a single public IP address"
    },
    {
        "question": "Which of the following is an example of an FHRP that is designed to prevent a single point of failure in a router network?",
        "options": [
            "A. VRRP",
            "B. RIP",
            "C. BGP",
            "D. NAT"
        ],
        "answer": "A. VRRP"
    },
    {
        "question": "Which of the following is a benefit of using **PAT** (Port Address Translation)?",
        "options": [
            "A. It allows multiple users to share the same public IP address",
            "B. It provides full internet access to each private IP address",
            "C. It uses a separate public IP address for each internal device",
            "D. It requires no configuration to operate"
        ],
        "answer": "A. It allows multiple users to share the same public IP address"
    },
    {
        "question": "Which of the following is true about **subinterfaces** on a router?",
        "options": [
            "A. Subinterfaces are configured with physical hardware",
            "B. Subinterfaces can be used to support multiple VLANs on a router",
            "C. Subinterfaces must be manually mapped to MAC addresses",
            "D. Subinterfaces cannot be used for routing purposes"
        ],
        "answer": "B. Subinterfaces can be used to support multiple VLANs on a router"
    },
    {
        "question": "In **HSRP**, which of the following routers is designated as the ‘Active Router’?",
        "options": [
            "A. The router that holds the highest priority",
            "B. The router that has the most up-to-date routing table",
            "C. The router that responds to ARP requests for the Virtual IP",
            "D. The router that receives the most network traffic"
        ],
        "answer": "C. The router that responds to ARP requests for the Virtual IP"
    },
    {
        "question": "What is the main role of **FHRP** in a network?",
        "options": [
            "A. To provide routing information between routers",
            "B. To enable load balancing between servers",
            "C. To ensure that multiple routers can be used as a gateway",
            "D. To prevent network congestion"
        ],
        "answer": "C. To ensure that multiple routers can be used as a gateway"
    },
    {
        "question": "Which of the following is the default behavior when a router receives a packet destined for a Virtual IP (VIP)?",
        "options": [
            "A. The packet is dropped unless it is part of an FHRP group",
            "B. The router forwards the packet based on the best route in the routing table",
            "C. The router responds with an ICMP echo reply",
            "D. The router initiates a DNS lookup for the destination address"
        ],
        "answer": "B. The router forwards the packet based on the best route in the routing table"
    },
    {
        "question": "Which of the following commands would you use to configure a subinterface on a router?",
        "options": [
            "A. interface FastEthernet 0/0.1",
            "B. ip address 192.168.1.1",
            "C. vlan 1",
            "D. ip nat inside"
        ],
        "answer": "A. interface FastEthernet 0/0.1"
    },
    {
        "question": "In a **PAT** setup, which element does the router modify to maintain multiple translations?",
        "options": [
            "A. Source IP address and source port number",
            "B. Destination IP address and destination port number",
            "C. Source IP address and destination port number",
            "D. Destination IP address and source port number"
        ],
        "answer": "A. Source IP address and source port number"
    },
    {
        "question": "Which protocol does **FHRP** rely on to allow multiple routers to work together to provide a single default gateway?",
        "options": [
            "A. ICMP",
            "B. ARP",
            "C. DNS",
            "D. BGP"
        ],
        "answer": "B. ARP"
    },
    {
        "question": "Which of the following is the default port range used in **PAT**?",
        "options": [
            "A. 1-1023",
            "B. 1024-65535",
            "C. 0-65535",
            "D. 1024-2048"
        ],
        "answer": "B. 1024-65535"
    },
    {
        "question": "Which of the following configuration changes would you make to set up **subinterfaces** for multiple VLANs?",
        "options": [
            "A. Assigning a unique VLAN ID to each subinterface",
            "B. Enabling the NAT protocol on each subinterface",
            "C. Setting a specific IP address for the physical interface",
            "D. Configuring a gateway for each subinterface"
        ],
        "answer": "A. Assigning a unique VLAN ID to each subinterface"
    },
    {
        "question": "Which of the following is true about static routing?",
        "options": [
            "A. Routes are automatically learned by routers",
            "B. Routes are manually configured by the network administrator",
            "C. Static routes are best for large, dynamic networks",
            "D. Static routes use routing protocols to update the network"
        ],
        "answer": "B. Routes are manually configured by the network administrator"
    },
    {
        "question": "In a dynamic routing setup, which of the following protocols would a network administrator use for inter-domain routing?",
        "options": [
            "A. OSPF",
            "B. EIGRP",
            "C. BGP",
            "D. RIP"
        ],
        "answer": "C. BGP"
    },
    {
        "question": "Which of the following is an advantage of using dynamic routing protocols over static routing?",
        "options": [
            "A. Automatic route recalculation during topology changes",
            "B. More control over route selection",
            "C. Faster convergence than static routes",
            "D. Requires less bandwidth to maintain routes"
        ],
        "answer": "A. Automatic route recalculation during topology changes"
    },
    {
        "question": "Which routing protocol is considered an Interior Gateway Protocol (IGP) and uses a distance vector method?",
        "options": [
            "A. OSPF",
            "B. EIGRP",
            "C. BGP",
            "D. RIP"
        ],
        "answer": "D. RIP"
    },
    {
        "question": "Which of the following is the primary difference between BGP and EIGRP?",
        "options": [
            "A. BGP is an IGP and EIGRP is an EGP",
            "B. BGP uses link-state routing while EIGRP uses distance vector",
            "C. BGP is used for inter-domain routing while EIGRP is for intra-domain routing",
            "D. EIGRP is used for both inter-domain and intra-domain routing"
        ],
        "answer": "C. BGP is used for inter-domain routing while EIGRP is for intra-domain routing"
    },
    {
        "question": "In Open Shortest Path First (OSPF), which metric is used to determine the best route?",
        "options": [
            "A. Hop count",
            "B. Bandwidth",
            "C. Cost",
            "D. Delay"
        ],
        "answer": "C. Cost"
    },
    {
        "question": "What is the purpose of administrative distance in dynamic routing?",
        "options": [
            "A. It determines the speed of a route",
            "B. It defines the reliability of a route",
            "C. It assigns a preference to a routing protocol when multiple protocols provide routes",
            "D. It prevents routing loops"
        ],
        "answer": "C. It assigns a preference to a routing protocol when multiple protocols provide routes"
    },
    {
        "question": "Which of the following routing protocols is best known for its ability to support VLSM (Variable Length Subnet Masking)?",
        "options": [
            "A. RIP",
            "B. BGP",
            "C. OSPF",
            "D. EIGRP"
        ],
        "answer": "D. EIGRP"
    },
    {
        "question": "In which scenario would a network administrator use **BGP**?",
        "options": [
            "A. To advertise routes within an enterprise network",
            "B. To exchange routing information between different ISPs",
            "C. To determine the shortest path within a single LAN",
            "D. To manage dynamic IP addressing within a subnet"
        ],
        "answer": "B. To exchange routing information between different ISPs"
    },
    {
        "question": "In OSPF, what does an area represent?",
        "options": [
            "A. A group of routers exchanging routing information",
            "B. A collection of IP addresses in a specific range",
            "C. A physical location of routers",
            "D. A logical grouping of routers in a network"
        ],
        "answer": "D. A logical grouping of routers in a network"
    },
    {
        "question": "Which of the following is an example of a metric used by a routing protocol to determine the best path?",
        "options": [
            "A. Packet size",
            "B. Hop count",
            "C. TTL",
            "D. Subnet mask"
        ],
        "answer": "B. Hop count"
    },
    {
        "question": "Which dynamic routing protocol is known for having fast convergence times and supports both IPv4 and IPv6?",
        "options": [
            "A. OSPF",
            "B. EIGRP",
            "C. BGP",
            "D. RIP"
        ],
        "answer": "B. EIGRP"
    },
    {
        "question": "Which of the following is true about **Static Routing**?",
        "options": [
            "A. Static routes are prone to network changes",
            "B. Static routes are only configured in large networks",
            "C. Static routes require manual intervention to update",
            "D. Static routes are automatically updated by the router"
        ],
        "answer": "C. Static routes require manual intervention to update"
    },
    {
        "question": "In OSPF, the default metric for a route is based on what?",
        "options": [
            "A. Bandwidth",
            "B. Cost",
            "C. Hop count",
            "D. Delay"
        ],
        "answer": "B. Cost"
    },
    {
        "question": "When comparing **BGP** and **EIGRP**, which is correct?",
        "options": [
            "A. EIGRP uses hop count as its metric, while BGP uses AS path length",
            "B. BGP is an interior gateway protocol, while EIGRP is an exterior gateway protocol",
            "C. BGP is used for large-scale routing, while EIGRP is better for smaller networks",
            "D. EIGRP is faster at converging than BGP"
        ],
        "answer": "C. BGP is used for large-scale routing, while EIGRP is better for smaller networks"
    },
    {
        "question": "Which of the following is used to manually configure a path between two routers in a static routing setup?",
        "options": [
            "A. OSPF",
            "B. BGP",
            "C. Static route command",
            "D. Dynamic routing protocol"
        ],
        "answer": "C. Static route command"
    },
    {
        "question": "Which of the following is a valid reason for selecting a route with a lower administrative distance?",
        "options": [
            "A. It has the most reliable path",
            "B. It has the most preferred metric",
            "C. It is more secure",
            "D. It is the most recent route"
        ],
        "answer": "A. It has the most reliable path"
    },
    {
        "question": "In a scenario where multiple routers use different routing protocols to route traffic, what would determine which protocol’s route is selected?",
        "options": [
            "A. Administrative distance",
            "B. Prefix length",
            "C. Metric",
            "D. Bandwidth"
        ],
        "answer": "A. Administrative distance"
    },
    {
        "question": "What is the purpose of a **routing table** in a router?",
        "options": [
            "A. It stores the source IP addresses of incoming packets",
            "B. It stores the configuration of static routes",
            "C. It stores the paths that the router can use to forward packets",
            "D. It stores the configuration of dynamic routing protocols"
        ],
        "answer": "C. It stores the paths that the router can use to forward packets"
    },
    {
        "question": "Which of the following is a key feature of **Open Shortest Path First (OSPF)**?",
        "options": [
            "A. It uses a distance vector approach",
            "B. It is used for large-scale routing across the internet",
            "C. It uses the link-state approach",
            "D. It does not support VLSM"
        ],
        "answer": "C. It uses the link-state approach"
    },
    {
        "question": "Which routing protocol would you use in a situation where multiple routes need to be selected based on the best path and traffic engineering?",
        "options": [
            "A. BGP",
            "B. EIGRP",
            "C. RIP",
            "D. OSPF"
        ],
        "answer": "A. BGP"
    },
    {
        "question": "In a routing protocol, what does **metric** refer to?",
        "options": [
            "A. The number of hops a packet must take to reach its destination",
            "B. The cost assigned to a route based on factors like bandwidth or delay",
            "C. The IP address of the next hop",
            "D. The packet size used by the protocol"
        ],
        "answer": "B. The cost assigned to a route based on factors like"
    },
    {
        "question": "A company wants to extend its wireless network across multiple buildings while ensuring seamless roaming for users. Which of the following network types should they implement?",
        "options": [
            "A. Ad hoc",
            "B. Point to point",
            "C. Extended Service Set (ESS)",
            "D. Mesh network"
        ],
        "answer": "C. Extended Service Set (ESS)"
    },
    {
        "question": "What is the primary purpose of an **Extended Service Set Identifier (ESSID)** in a wireless network?",
        "options": [
            "A. To uniquely identify a single access point",
            "B. To group multiple access points into a single logical network",
            "C. To encrypt data transmitted over the network",
            "D. To provide a unique identifier for ad hoc networks"
        ],
        "answer": "B. To group multiple access points into a single logical network"
    },
    {
        "question": "A small office wants to create a temporary wireless network for a meeting without using an access point. Which network type should they use?",
        "options": [
            "A. Infrastructure",
            "B. Mesh network",
            "C. Ad hoc",
            "D. Point to point"
        ],
        "answer": "C. Ad hoc"
    },
    {
        "question": "Which of the following is a key advantage of a **mesh network**?",
        "options": [
            "A. It requires no configuration and works out of the box",
            "B. It provides self-healing and redundancy by allowing multiple paths for data",
            "C. It is the most cost-effective solution for small networks",
            "D. It uses less power than traditional networks"
        ],
        "answer": "B. It provides self-healing and redundancy by allowing multiple paths for data"
    },
    {
        "question": "A network administrator is setting up a wireless link between two buildings located 1 kilometer apart. Which network type is most suitable for this scenario?",
        "options": [
            "A. Ad hoc",
            "B. Point to point",
            "C. Mesh network",
            "D. Infrastructure"
        ],
        "answer": "B. Point to point"
    },
    {
        "question": "Which of the following is a characteristic of an **infrastructure** wireless network?",
        "options": [
            "A. Devices communicate directly with each other without an access point",
            "B. It uses a centralized access point to manage connections",
            "C. It is primarily used for temporary networks",
            "D. It does not support encryption"
        ],
        "answer": "B. It uses a centralized access point to manage connections"
    },
    {
        "question": "A company wants to ensure the highest level of security for its wireless network. Which encryption protocol should they use?",
        "options": [
            "A. WEP",
            "B. WPA2",
            "C. WPA3",
            "D. Open authentication"
        ],
        "answer": "C. WPA3"
    },
    {
        "question": "What is the primary improvement of **WPA3** over **WPA2**?",
        "options": [
            "A. It uses weaker encryption for better compatibility",
            "B. It introduces stronger encryption and protection against brute-force attacks",
            "C. It removes the need for a pre-shared key (PSK)",
            "D. It allows for longer SSIDs"
        ],
        "answer": "B. It introduces stronger encryption and protection against brute-force attacks"
    },
    {
        "question": "A coffee shop wants to provide internet access to customers while isolating them from the internal network. Which of the following should they implement?",
        "options": [
            "A. WPA3 encryption",
            "B. A guest network with a captive portal",
            "C. An ad hoc network",
            "D. A point-to-point network"
        ],
        "answer": "B. A guest network with a captive portal"
    },
    {
        "question": "What is the primary purpose of a **captive portal** in a guest network?",
        "options": [
            "A. To encrypt all traffic on the network",
            "B. To force users to authenticate or accept terms before accessing the internet",
            "C. To block all external websites",
            "D. To provide a unique SSID for each user"
        ],
        "answer": "B. To force users to authenticate or accept terms before accessing the internet"
    },
    {
        "question": "A user connects to a public Wi-Fi network and is redirected to a webpage asking them to agree to terms of service. What is this an example of?",
        "options": [
            "A. WPA2 encryption",
            "B. A captive portal",
            "C. An ad hoc network",
            "D. A mesh network"
        ],
        "answer": "B. A captive portal"
    },
    {
        "question": "Which of the following is a security risk associated with **guest networks**?",
        "options": [
            "A. They use WPA3 encryption by default",
            "B. They often lack strong encryption, making them vulnerable to attacks",
            "C. They require users to authenticate with a username and password",
            "D. They are isolated from the main network by default"
        ],
        "answer": "B. They often lack strong encryption, making them vulnerable to attacks"
    },
    {
        "question": "A network administrator wants to ensure that guest users cannot access internal company resources. Which of the following should they configure?",
        "options": [
            "A. Enable WPA2 encryption on the guest network",
            "B. Use a captive portal for authentication",
            "C. Isolate the guest network from the internal network",
            "D. Disable SSID broadcasting for the guest network"
        ],
        "answer": "C. Isolate the guest network from the internal network"
    },
    {
        "question": "Which of the following is a key difference between **WPA2** and **WPA3** encryption?",
        "options": [
            "A. WPA2 uses AES encryption, while WPA3 uses TKIP",
            "B. WPA3 provides forward secrecy, while WPA2 does not",
            "C. WPA2 is more secure than WPA3",
            "D. WPA3 is not compatible with modern devices"
        ],
        "answer": "B. WPA3 provides forward secrecy, while WPA2 does not"
    },
    {
        "question": "A company wants to deploy a wireless network that can automatically reroute traffic if one node fails. Which network type should they use?",
        "options": [
            "A. Ad hoc",
            "B. Point to point",
            "C. Mesh network",
            "D. Infrastructure"
        ],
        "answer": "C. Mesh network"
    },
    {
        "question": "Which of the following is a disadvantage of using an **ad hoc** wireless network?",
        "options": [
            "A. It requires a centralized access point",
            "B. It is difficult to scale for large networks",
            "C. It provides high-speed connectivity over long distances",
            "D. It is more secure than infrastructure networks"
        ],
        "answer": "B. It is difficult to scale for large networks"
    },
    {
        "question": "A network administrator is configuring a wireless network and wants to ensure that users can roam between access points without losing connectivity. Which of the following should they configure?",
        "options": [
            "A. Ad hoc network",
            "B. Extended Service Set (ESS)",
            "C. Point-to-point network",
            "D. Captive portal"
        ],
        "answer": "B. Extended Service Set (ESS)"
    },
    {
        "question": "Which of the following is a key benefit of using **WPA2** encryption over **WEP**?",
        "options": [
            "A. WPA2 uses weaker encryption for better performance",
            "B. WPA2 is more secure and uses AES encryption",
            "C. WPA2 is easier to configure than WEP",
            "D. WPA2 does not require a pre-shared key (PSK)"
        ],
        "answer": "B. WPA2 is more secure and uses AES encryption"
    },
    {
        "question": "A hotel wants to provide internet access to guests while displaying a welcome page upon connection. Which of the following should they implement?",
        "options": [
            "A. WPA3 encryption",
            "B. A captive portal",
            "C. An ad hoc network",
            "D. A mesh network"
        ],
        "answer": "B. A captive portal"
    },
    {
        "question": "Which of the following is a key characteristic of a **point-to-point** wireless network?",
        "options": [
            "A. It allows multiple devices to connect to a single access point",
            "B. It is used to connect two locations directly",
            "C. It is self-healing and redundant",
            "D. It is primarily used for temporary networks"
        ],
        "answer": "B. It is used to connect two locations directly"
    },
    {
        "question": "A company wants to deploy a wireless network that can cover a large area with minimal dead zones. Which network type should they use?",
        "options": [
            "A. Ad hoc",
            "B. Point to point",
            "C. Mesh network",
            "D. Infrastructure"
        ],
        "answer": "C. Mesh network"
    },
    {
        "question": "Which of the following is a key difference between **WPA2-Personal** and **WPA2-Enterprise**?",
        "options": [
            "A. WPA2-Personal uses a pre-shared key (PSK), while WPA2-Enterprise uses individual user credentials",
            "B. WPA2-Personal is less secure than WPA2-Enterprise",
            "C. WPA2-Enterprise is only used in ad hoc networks",
            "D. WPA2-Personal requires a RADIUS server"
        ],
        "answer": "A. WPA2-Personal uses a pre-shared key (PSK), while WPA2-Enterprise uses individual user credentials"
    },
    {
        "question": "A network administrator wants to ensure that guest users are authenticated before accessing the internet. Which of the following should they implement?",
        "options": [
            "A. WPA3 encryption",
            "B. A captive portal",
            "C. An ad hoc network",
            "D. A point-to-point network"
        ],
        "answer": "B. A captive portal"
    },
    {
        "question": "Which of the following is a key advantage of using **WPA3** over **WPA2** for IoT devices?",
        "options": [
            "A. WPA3 uses weaker encryption for better compatibility",
            "B. WPA3 provides stronger protection against brute-force attacks",
            "C. WPA3 is not supported by IoT devices",
            "D. WPA3 requires a captive portal"
        ],
        "answer": "B. WPA3 provides stronger protection against brute-force attacks"
    },
    {
        "question": "A company wants to deploy a wireless network that can automatically adjust to changes in the network topology. Which network type should they use?",
        "options": [
            "A. Ad hoc",
            "B. Point to point",
            "C. Mesh network",
            "D. Infrastructure"
        ],
        "answer": "C. Mesh network"
    },
    {
        "question": "Which of the following is a key advantage of using **5GHz** over **2.4GHz** for Wi-Fi networks?",
        "options": [
            "A. Longer range and better penetration through walls",
            "B. More non-overlapping channels and less interference",
            "C. Better compatibility with older devices",
            "D. Higher power output for increased signal strength"
        ],
        "answer": "B. More non-overlapping channels and less interference"
    },
    {
        "question": "What is the primary purpose of **dynamic frequency selection (DFS)** in wireless networks?",
        "options": [
            "A. To automatically switch devices to the least congested channel",
            "B. To avoid interference with radar systems and other licensed users",
            "C. To increase the channel width for higher throughput",
            "D. To enable band steering between 2.4GHz and 5GHz"
        ],
        "answer": "B. To avoid interference with radar systems and other licensed users"
    },
    {
        "question": "Which of the following is **true** about the **6GHz band** introduced by Wi-Fi 6E?",
        "options": [
            "A. It supports only 20MHz channel widths",
            "B. It is backward compatible with 802.11a/b/g/n devices",
            "C. It provides up to 1,200MHz of additional spectrum for Wi-Fi",
            "D. It is only available for use in outdoor environments"
        ],
        "answer": "C. It provides up to 1,200MHz of additional spectrum for Wi-Fi"
    },
    {
        "question": "What is the maximum number of **non-overlapping channels** available in the **5GHz band**?",
        "options": [
            "A. 3",
            "B. 9",
            "C. 25",
            "D. 45"
        ],
        "answer": "C. 25"
    },
    {
        "question": "Which of the following is a **disadvantage** of using a **40MHz channel width** in the 2.4GHz band?",
        "options": [
            "A. Reduced throughput due to narrower bandwidth",
            "B. Increased interference with neighboring networks",
            "C. Incompatibility with 802.11n devices",
            "D. Limited range compared to 20MHz channels"
        ],
        "answer": "B. Increased interference with neighboring networks"
    },
    {
        "question": "What is the primary function of **transmit power control (TPC)** in wireless networks?",
        "options": [
            "A. To increase the range of the wireless signal",
            "B. To reduce interference by adjusting the power level of the access point",
            "C. To enable faster data rates by boosting signal strength",
            "D. To allow devices to switch between frequency bands automatically"
        ],
        "answer": "B. To reduce interference by adjusting the power level of the access point"
    },
    {
        "question": "Which of the following statements is **true** about **SSID broadcasting**?",
        "options": [
            "A. Disabling SSID broadcasting makes the network completely invisible",
            "B. SSID broadcasting is required for all wireless networks",
            "C. Disabling SSID broadcasting can improve network security",
            "D. SSID broadcasting has no impact on network performance"
        ],
        "answer": "C. Disabling SSID broadcasting can improve network security"
    },
    {
        "question": "What is the primary purpose of a **Basic Service Set (BSS)** in wireless networking?",
        "options": [
            "A. To connect multiple access points to a single network",
            "B. To define a group of devices connected to a single access point",
            "C. To enable communication between devices in an ad-hoc network",
            "D. To provide a unique identifier for a wireless network"
        ],
        "answer": "B. To define a group of devices connected to a single access point"
    },
    {
        "question": "Which of the following is a **regulatory requirement** for using the **5GHz band** in some regions?",
        "options": [
            "A. Use of 40MHz channel width",
            "B. Implementation of dynamic frequency selection (DFS)",
            "C. Support for 802.11b/g devices",
            "D. Use of WPA3 encryption"
        ],
        "answer": "B. Implementation of dynamic frequency selection (DFS)"
    },
    {
        "question": "What is the primary benefit of using **non-overlapping channels** in a wireless network?",
        "options": [
            "A. Increased signal range",
            "B. Reduced interference and improved performance",
            "C. Compatibility with older devices",
            "D. Higher power output for access points"
        ],
        "answer": "B. Reduced interference and improved performance"
    },
    {
        "question": "Which of the following is **true** about **channel width** in wireless networks?",
        "options": [
            "A. A wider channel width increases throughput but may reduce the number of available non-overlapping channels",
            "B. A narrower channel width increases throughput and reduces interference",
            "C. Channel width has no impact on network performance",
            "D. A wider channel width reduces throughput but increases range"
        ],
        "answer": "A. A wider channel width increases throughput but may reduce the number of available non-overlapping channels"
    },
    {
        "question": "What is the primary purpose of **non-overlapping channels** in the 2.4GHz band?",
        "options": [
            "A. To increase the number of available channels",
            "B. To reduce interference between adjacent wireless networks",
            "C. To allow devices to switch between frequencies automatically",
            "D. To enable higher data rates in the 5GHz band"
        ],
        "answer": "B. To reduce interference between adjacent wireless networks"
    },
    {
        "question": "Which regulatory standard introduced **dynamic frequency selection (DFS)** and **transmit power control (TPC)** to comply with European regulations?",
        "options": [
            "A. 802.11a",
            "B. 802.11h",
            "C. 802.11n",
            "D. 802.11ac"
        ],
        "answer": "B. 802.11h"
    },
    {
        "question": "Which of the following frequency bands is **NOT** commonly used in modern Wi-Fi networks?",
        "options": [
            "A. 2.4GHz",
            "B. 5GHz",
            "C. 6GHz",
            "D. 10GHz"
        ],
        "answer": "D. 10GHz"
    },
    {
        "question": "What is the primary purpose of **band steering** in dual-band wireless networks?",
        "options": [
            "A. To force devices to use the 2.4GHz band for better range",
            "B. To automatically direct devices to the least congested frequency band (2.4GHz or 5GHz)",
            "C. To disable the 5GHz band for compatibility with older devices",
            "D. To increase the channel width on the 2.4GHz band"
        ],
        "answer": "B. To automatically direct devices to the least congested frequency band (2.4GHz or 5GHz)"
    },
    {
        "question": "What does **SSID** stand for in wireless networking?",
        "options": [
            "A. Secure Service Identifier",
            "B. Service Set Identifier",
            "C. Signal Strength Indicator Data",
            "D. System Security Identifier"
        ],
        "answer": "B. Service Set Identifier"
    },
    {
        "question": "Which of the following is **true** about a **Basic Service Set Identifier (BSSID)**?",
        "options": [
            "A. It is the same as the SSID",
            "B. It is a unique identifier for a wireless access point's radio",
            "C. It is only used in ad-hoc wireless networks",
            "D. It is a type of encryption key"
        ],
        "answer": "B. It is a unique identifier for a wireless access point's radio"
    },
    {
        "question": "In the 2.4GHz band, how many non-overlapping channels are available in the United States?",
        "options": [
            "A. 3",
            "B. 6",
            "C. 11",
            "D. 14"
        ],
        "answer": "A. 3"
    },
    {
        "question": "Which of the following frequency bands provides the **greatest number of non-overlapping channels**?",
        "options": [
            "A. 2.4GHz",
            "B. 5GHz",
            "C. 6GHz",
            "D. All bands provide the same number of non-overlapping channels"
        ],
        "answer": "C. 6GHz"
    },
    {
        "question": "What is the primary benefit of using the **6GHz band** for Wi-Fi?",
        "options": [
            "A. Longer range compared to 2.4GHz and 5GHz",
            "B. Greater availability of non-overlapping channels and higher bandwidth",
            "C. Better compatibility with older devices",
            "D. Reduced power consumption for connected devices"
        ],
        "answer": "B. Greater availability of non-overlapping channels and higher bandwidth"
    },
    {
        "question": "Which of the following is **true** about **channel width** in wireless networks?",
        "options": [
            "A. A wider channel width increases throughput but may reduce the number of available non-overlapping channels",
            "B. A narrower channel width increases throughput and reduces interference",
            "C. Channel width has no impact on network performance",
            "D. A wider channel width reduces throughput but increases range"
        ],
        "answer": "A. A wider channel width increases throughput but may reduce the number of available non-overlapping channels"
    },
    {
        "question": "What is the primary purpose of **non-overlapping channels** in the 2.4GHz band?",
        "options": [
            "A. To increase the number of available channels",
            "B. To reduce interference between adjacent wireless networks",
            "C. To allow devices to switch between frequencies automatically",
            "D. To enable higher data rates in the 5GHz band"
        ],
        "answer": "B. To reduce interference between adjacent wireless networks"
    },
    {
        "question": "Which regulatory standard introduced **dynamic frequency selection (DFS)** and **transmit power control (TPC)** to comply with European regulations?",
        "options": [
            "A. 802.11a",
            "B. 802.11h",
            "C. 802.11n",
            "D. 802.11ac"
        ],
        "answer": "B. 802.11h"
    },
    {
        "question": "Which of the following frequency bands is **NOT** commonly used in modern Wi-Fi networks?",
        "options": [
            "A. 2.4GHz",
            "B. 5GHz",
            "C. 6GHz",
            "D. 10GHz"
        ],
        "answer": "D. 10GHz"
    },
    {
        "question": "What is the primary purpose of **band steering** in dual-band wireless networks?",
        "options": [
            "A. To force devices to use the 2.4GHz band for better range",
            "B. To automatically direct devices to the least congested frequency band (2.4GHz or 5GHz)",
            "C. To disable the 5GHz band for compatibility with older devices",
            "D. To increase the channel width on the 2.4GHz band"
        ],
        "answer": "B. To automatically direct devices to the least congested frequency band (2.4GHz or 5GHz)"
    },
    {
        "question": "What does **SSID** stand for in wireless networking?",
        "options": [
            "A. Secure Service Identifier",
            "B. Service Set Identifier",
            "C. Signal Strength Indicator Data",
            "D. System Security Identifier"
        ],
        "answer": "B. Service Set Identifier"
    },
    {
        "question": "Which of the following is **true** about a **Basic Service Set Identifier (BSSID)**?",
        "options": [
            "A. It is the same as the SSID",
            "B. It is a unique identifier for a wireless access point's radio",
            "C. It is only used in ad-hoc wireless networks",
            "D. It is a type of encryption key"
        ],
        "answer": "B. It is a unique identifier for a wireless access point's radio"
    },
    {
        "question": "In the 2.4GHz band, how many non-overlapping channels are available in the United States?",
        "options": [
            "A. 3",
            "B. 6",
            "C. 11",
            "D. 14"
        ],
        "answer": "A. 3"
    },
    {
        "question": "Which of the following frequency bands provides the **greatest number of non-overlapping channels**?",
        "options": [
            "A. 2.4GHz",
            "B. 5GHz",
            "C. 6GHz",
            "D. All bands provide the same number of non-overlapping channels"
        ],
        "answer": "C. 6GHz"
    },
    {
        "question": "What is the primary benefit of using the **6GHz band** for Wi-Fi?",
        "options": [
            "A. Longer range compared to 2.4GHz and 5GHz",
            "B. Greater availability of non-overlapping channels and higher bandwidth",
            "C. Better compatibility with older devices",
            "D. Reduced power consumption for connected devices"
        ],
        "answer": "B. Greater availability of non-overlapping channels and higher bandwidth"
    },
    {
        "question": "Which of the following is **true** about **channel width** in wireless networks?",
        "options": [
            "A. A wider channel width increases throughput but may reduce the number of available non-overlapping channels",
            "B. A narrower channel width increases throughput and reduces interference",
            "C. Channel width has no impact on network performance",
            "D. A wider channel width reduces throughput but increases range"
        ],
        "answer": "A. A wider channel width increases throughput but may reduce the number of available non-overlapping channels"
    },
    {
        "question": "What is the primary purpose of **non-overlapping channels** in the 2.4GHz band?",
        "options": [
            "A. To increase the number of available channels",
            "B. To reduce interference between adjacent wireless networks",
            "C. To allow devices to switch between frequencies automatically",
            "D. To enable higher data rates in the 5GHz band"
        ],
        "answer": "B. To reduce interference between adjacent wireless networks"
    },
    {
        "question": "Which regulatory standard introduced **dynamic frequency selection (DFS)** and **transmit power control (TPC)** to comply with European regulations?",
        "options": [
            "A. 802.11a",
            "B. 802.11h",
            "C. 802.11n",
            "D. 802.11ac"
        ],
        "answer": "B. 802.11h"
    },
    {
        "question": "Which of the following frequency bands is **NOT** commonly used in modern Wi-Fi networks?",
        "options": [
            "A. 2.4GHz",
            "B. 5GHz",
            "C. 6GHz",
            "D. 10GHz"
        ],
        "answer": "D. 10GHz"
    },
    {
        "question": "What is the primary purpose of **band steering** in dual-band wireless networks?",
        "options": [
            "A. To force devices to use the 2.4GHz band for better range",
            "B. To automatically direct devices to the least congested frequency band (2.4GHz or 5GHz)",
            "C. To disable the 5GHz band for compatibility with older devices",
            "D. To increase the channel width on the 2.4GHz band"
        ],
        "answer": "B. To automatically direct devices to the least congested frequency band (2.4GHz or 5GHz)"
    },
    {
        "question": "What does **SSID** stand for in wireless networking?",
        "options": [
            "A. Secure Service Identifier",
            "B. Service Set Identifier",
            "C. Signal Strength Indicator Data",
            "D. System Security Identifier"
        ],
        "answer": "B. Service Set Identifier"
    },
    {
        "question": "Which of the following is **true** about a **Basic Service Set Identifier (BSSID)**?",
        "options": [
            "A. It is the same as the SSID",
            "B. It is a unique identifier for a wireless access point's radio",
            "C. It is only used in ad-hoc wireless networks",
            "D. It is a type of encryption key"
        ],
        "answer": "B. It is a unique identifier for a wireless access point's radio"
    },
    {
        "question": "In the 2.4GHz band, how many non-overlapping channels are available in the United States?",
        "options": [
            "A. 3",
            "B. 6",
            "C. 11",
            "D. 14"
        ],
        "answer": "A. 3"
    },
    {
        "question": "Which of the following frequency bands provides the **greatest number of non-overlapping channels**?",
        "options": [
            "A. 2.4GHz",
            "B. 5GHz",
            "C. 6GHz",
            "D. All bands provide the same number of non-overlapping channels"
        ],
        "answer": "C. 6GHz"
    },
    {
        "question": "What is the primary benefit of using the **6GHz band** for Wi-Fi?",
        "options": [
            "A. Longer range compared to 2.4GHz and 5GHz",
            "B. Greater availability of non-overlapping channels and higher bandwidth",
            "C. Better compatibility with older devices",
            "D. Reduced power consumption for connected devices"
        ],
        "answer": "B. Greater availability of non-overlapping channels and higher bandwidth"
    },
    {
        "question": "Which factor should be considered when selecting a UPS for a network rack?",
        "options": [
            "A. The number of cooling fans in the rack",
            "B. The total power consumption of connected devices",
            "C. The number of network switches in use",
            "D. The IP address of the UPS"
        ],
        "answer": "B. The total power consumption of connected devices"
    },
    {
        "question": "Which component helps prevent power spikes from damaging networking equipment?",
        "options": [
            "A. Uninterruptible Power Supply (UPS)",
            "B. Power Distribution Unit (PDU)",
            "C. Surge protector",
            "D. Line filter"
        ],
        "answer": "C. Surge protector"
    },
    {
        "question": "What is the primary benefit of using a smart PDU over a basic PDU?",
        "options": [
            "A. It provides real-time power monitoring and remote management",
            "B. It eliminates the need for a UPS",
            "C. It increases network bandwidth",
            "D. It converts AC power to DC power"
        ],
        "answer": "A. It provides real-time power monitoring and remote management"
    },
    {
        "question": "How does excessive temperature affect network equipment in a data center?",
        "options": [
            "A. It improves network latency",
            "B. It increases power efficiency",
            "C. It reduces equipment lifespan and performance",
            "D. It enhances cooling system efficiency"
        ],
        "answer": "C. It reduces equipment lifespan and performance"
    },
    {
        "question": "Which type of fire suppression system is most effective in protecting sensitive electronic equipment?",
        "options": [
            "A. Dry chemical fire extinguishers",
            "B. CO2 gas suppression",
            "C. Water sprinklers",
            "D. Halon-based extinguishers"
        ],
        "answer": "B. CO2 gas suppression"
    },
    {
        "question": "Why is a dual-power supply configuration recommended for critical network devices?",
        "options": [
            "A. It increases data transfer speed",
            "B. It provides redundancy in case of a power supply failure",
            "C. It eliminates the need for a UPS",
            "D. It reduces power consumption"
        ],
        "answer": "B. It provides redundancy in case of a power supply failure"
    },
    {
        "question": "Which method is used to optimize airflow in a server rack?",
        "options": [
            "A. Installing blanking panels between unused rack spaces",
            "B. Removing all front covers from network switches",
            "C. Positioning network racks near windows",
            "D. Using fiber optic cables instead of copper cables"
        ],
        "answer": "A. Installing blanking panels between unused rack spaces"
    },
    {
        "question": "Which device can regulate and stabilize voltage levels to protect network equipment?",
        "options": [
            "A. Circuit breaker",
            "B. Automatic voltage regulator (AVR)",
            "C. Fiber distribution panel",
            "D. Wireless access point"
        ],
        "answer": "B. Automatic voltage regulator (AVR)"
    },
    {
        "question": "What is the primary advantage of hot aisle/cold aisle containment in a data center?",
        "options": [
            "A. It improves security by restricting access to server racks",
            "B. It enhances power efficiency and cooling effectiveness",
            "C. It increases the number of devices that can be installed in a rack",
            "D. It reduces electromagnetic interference"
        ],
        "answer": "B. It enhances power efficiency and cooling effectiveness"
    },
    {
        "question": "Which factor should be monitored to prevent condensation-related failures in a server room?",
        "options": [
            "A. Temperature only",
            "B. Voltage fluctuations",
            "C. Humidity levels",
            "D. Air pressure"
        ],
        "answer": "C. Humidity levels"
    },
    {
        "question": "What is the primary function of an Uninterruptible Power Supply (UPS) in a network environment?",
        "options": [
            "A. To replace the need for power outlets",
            "B. To provide backup power and protect against power surges",
            "C. To increase internet speed",
            "D. To act as a firewall for network security"
        ],
        "answer": "B. To provide backup power and protect against power surges"
    },
    {
        "question": "Which of the following best describes a Power Distribution Unit (PDU) in a network rack?",
        "options": [
            "A. It supplies and manages power distribution to multiple devices in a rack",
            "B. It converts DC power to AC power for networking equipment",
            "C. It replaces an Uninterruptible Power Supply (UPS) in a data center",
            "D. It stores backup power for extended outages"
        ],
        "answer": "A. It supplies and manages power distribution to multiple devices in a rack"
    },
    {
        "question": "Why is power load an important consideration when designing a network infrastructure?",
        "options": [
            "A. To ensure that connected devices do not exceed power capacity",
            "B. To reduce the number of required power cables",
            "C. To increase network bandwidth",
            "D. To improve internet connectivity"
        ],
        "answer": "A. To ensure that connected devices do not exceed power capacity"
    },
    {
        "question": "Which voltage standard is commonly used for network equipment in North America?",
        "options": [
            "A. 120V",
            "B. 230V",
            "C. 48V",
            "D. 12V"
        ],
        "answer": "A. 120V"
    },
    {
        "question": "Which voltage standard is typically used for large-scale data centers in Europe?",
        "options": [
            "A. 120V",
            "B. 230V",
            "C. 5V",
            "D. 24V"
        ],
        "answer": "B. 230V"
    },
    {
        "question": "Why is humidity control important in server rooms and data centers?",
        "options": [
            "A. To prevent static electricity and condensation",
            "B. To enhance wireless network signals",
            "C. To improve server processing speed",
            "D. To increase the efficiency of fiber optic connections"
        ],
        "answer": "A. To prevent static electricity and condensation"
    },
    {
        "question": "What is the recommended relative humidity range for a data center?",
        "options": [
            "A. 10% - 20%",
            "B. 30% - 50%",
            "C. 60% - 80%",
            "D. 90% - 100%"
        ],
        "answer": "B. 30% - 50%"
    },
    {
        "question": "Which fire suppression method is commonly used in data centers to avoid equipment damage?",
        "options": [
            "A. Water sprinklers",
            "B. Carbon dioxide (CO2) gas suppression",
            "C. Sand-based extinguishers",
            "D. Halon-based fire extinguishers"
        ],
        "answer": "B. Carbon dioxide (CO2) gas suppression"
    },
    {
        "question": "Why are traditional water-based fire suppression systems generally avoided in data centers?",
        "options": [
            "A. They are not effective in cooling equipment",
            "B. They can damage electrical and network equipment",
            "C. They do not meet environmental regulations",
            "D. They require frequent maintenance"
        ],
        "answer": "B. They can damage electrical and network equipment"
    },
    {
        "question": "What is the ideal temperature range for a server room to ensure optimal performance?",
        "options": [
            "A. 40°F - 50°F (4°C - 10°C)",
            "B. 68°F - 77°F (20°C - 25°C)",
            "C. 90°F - 100°F (32°C - 38°C)",
            "D. 50°F - 60°F (10°C - 16°C)"
        ],
        "answer": "B. 68°F - 77°F (20°C - 25°C)"
    },
    {
        "question": "What is the purpose of a redundant UPS system in a data center?",
        "options": [
            "A. To improve network bandwidth",
            "B. To provide additional power protection in case of failure",
            "C. To eliminate the need for cooling systems",
            "D. To reduce electromagnetic interference"
        ],
        "answer": "B. To provide additional power protection in case of failure"
    },
    {
        "question": "How does a Power Distribution Unit (PDU) help manage power consumption in a network rack?",
        "options": [
            "A. It automatically shuts down idle devices",
            "B. It distributes electrical power efficiently across multiple devices",
            "C. It converts AC power into DC power",
            "D. It eliminates the need for UPS backup power"
        ],
        "answer": "B. It distributes electrical power efficiently across multiple devices"
    },
    {
        "question": "What type of power issue can a UPS protect against?",
        "options": [
            "A. Network congestion",
            "B. Sudden power outages and surges",
            "C. Slow internet speeds",
            "D. Excessive packet loss"
        ],
        "answer": "B. Sudden power outages and surges"
    },
    {
        "question": "What can occur if power load is not properly managed in a data center?",
        "options": [
            "A. Overloaded circuits and potential equipment failure",
            "B. Faster internet speeds",
            "C. Improved Wi-Fi signal strength",
            "D. Better airflow in network racks"
        ],
        "answer": "A. Overloaded circuits and potential equipment failure"
    },
    {
        "question": "Which fire suppression agent is considered safe for use in network environments?",
        "options": [
            "A. Water",
            "B. Halon gas",
            "C. FM-200 gas",
            "D. Foam-based extinguishers"
        ],
        "answer": "C. FM-200 gas"
    },
    {
        "question": "Which type of UPS provides continuous power without a switching delay?",
        "options": [
            "A. Offline UPS",
            "B. Standby UPS",
            "C. Line-interactive UPS",
            "D. Online (Double-conversion) UPS"
        ],
        "answer": "D. Online (Double-conversion) UPS"
    },
    {
        "question": "What is the primary risk of excessive humidity in a data center?",
        "options": [
            "A. Equipment overheating",
            "B. Condensation leading to short circuits",
            "C. Increased fire risk",
            "D. Slower network speeds"
        ],
        "answer": "B. Condensation leading to short circuits"
    },
    {
        "question": "What is a best practice for maintaining stable temperature in a server room?",
        "options": [
            "A. Positioning racks near windows for ventilation",
            "B. Using HVAC systems designed for data center cooling",
            "C. Installing additional fiber optic cables",
            "D. Placing fire extinguishers near network switches"
        ],
        "answer": "B. Using HVAC systems designed for data center cooling"
    },
    {
        "question": "Which cooling technique is commonly used in data centers to maintain optimal temperature?",
        "options": [
            "A. Freezing the server room overnight",
            "B. Liquid immersion cooling",
            "C. Opening windows for airflow",
            "D. Using ice packs inside the racks"
        ],
        "answer": "B. Liquid immersion cooling"
    },
    {
        "question": "What is the primary function of an Intermediate Distribution Frame (IDF) in a network infrastructure?",
        "options": [
            "A. To connect end-user devices directly to the internet",
            "B. To serve as an intermediary connection point between the Main Distribution Frame (MDF) and end devices",
            "C. To act as a firewall for network security",
            "D. To store backup data for the network"
        ],
        "answer": "B. To serve as an intermediary connection point between the Main Distribution Frame (MDF) and end devices"
    },
    {
        "question": "Which of the following best describes the function of a Main Distribution Frame (MDF)?",
        "options": [
            "A. It serves as the central connection point for network traffic in a building or campus",
            "B. It houses only patch panels for fiber optic connections",
            "C. It connects workstations directly to the internet",
            "D. It functions as a cooling system for data center equipment"
        ],
        "answer": "A. It serves as the central connection point for network traffic in a building or campus"
    },
    {
        "question": "What should be considered when determining the appropriate rack size for network equipment?",
        "options": [
            "A. The number of servers and switches to be mounted",
            "B. The total weight of the cabling infrastructure",
            "C. The humidity level of the room",
            "D. The length of the patch cables used"
        ],
        "answer": "A. The number of servers and switches to be mounted"
    },
    {
        "question": "Why is proper airflow management important in network racks, particularly regarding port-side exhaust and intake?",
        "options": [
            "A. To prevent overheating and ensure optimal equipment performance",
            "B. To allow free access to cabling connections",
            "C. To maintain electromagnetic shielding",
            "D. To improve data transmission speed"
        ],
        "answer": "A. To prevent overheating and ensure optimal equipment performance"
    },
    {
        "question": "What is the purpose of using a patch panel in a structured cabling system?",
        "options": [
            "A. To extend wireless signal coverage",
            "B. To serve as a central termination point for network cables",
            "C. To encrypt network traffic",
            "D. To store backup network configurations"
        ],
        "answer": "B. To serve as a central termination point for network cables"
    },
    {
        "question": "Which of the following components is specifically used for organizing fiber optic connections in a network installation?",
        "options": [
            "A. Patch panel",
            "B. Fiber distribution panel",
            "C. RJ45 switch",
            "D. Demarcation point"
        ],
        "answer": "B. Fiber distribution panel"
    },
    {
        "question": "Why is it important to use lockable enclosures or racks in an MDF or IDF?",
        "options": [
            "A. To protect network equipment from unauthorized access and tampering",
            "B. To reduce the amount of power consumption in a data center",
            "C. To improve cooling efficiency in server rooms",
            "D. To simplify network cable management"
        ],
        "answer": "A. To protect network equipment from unauthorized access and tampering"
    },
    {
        "question": "What is a key benefit of using fiber distribution panels in a network infrastructure?",
        "options": [
            "A. They simplify cable management for fiber optic connections",
            "B. They increase the transmission speed of copper cabling",
            "C. They reduce the need for additional MDFs in a network",
            "D. They eliminate the need for rack-mounted switches"
        ],
        "answer": "A. They simplify cable management for fiber optic connections"
    },
    {
        "question": "Which of the following factors is most important when determining the location of an IDF within a building?",
        "options": [
            "A. The availability of natural light",
            "B. The distance between the MDF and connected end devices",
            "C. The number of Wi-Fi access points in the building",
            "D. The amount of furniture in the room"
        ],
        "answer": "B. The distance between the MDF and connected end devices"
    },
    {
        "question": "What is the best practice for ensuring proper cooling in network racks with front-to-back airflow?",
        "options": [
            "A. Use blanking panels to prevent hot air recirculation",
            "B. Position racks near windows for ventilation",
            "C. Use only open-frame racks for better airflow",
            "D. Install network switches at the top of the rack"
        ],
        "answer": "A. Use blanking panels to prevent hot air recirculation"
    },
    {
        "question": "Which type of cable is typically used for high-speed connections between switches in a data center?",
        "options": [
            "A. Cat 5e",
            "B. Cat 6",
            "C. Cat 6a",
            "D. Cat 7"
        ],
        "answer": "C. Cat 6a"
    },
    {
        "question": "What is the maximum recommended length for a Cat 6 Ethernet cable to maintain optimal performance?",
        "options": [
            "A. 55 meters",
            "B. 75 meters",
            "C. 90 meters",
            "D. 100 meters"
        ],
        "answer": "D. 100 meters"
    },
    {
        "question": "Which of the following tools is essential for creating custom-length Ethernet cables?",
        "options": [
            "A. Cable tester",
            "B. Crimping tool",
            "C. Tone generator",
            "D. Punch-down tool"
        ],
        "answer": "B. Crimping tool"
    },
    {
        "question": "In a structured cabling system, what is the purpose of a demarcation point?",
        "options": [
            "A. To separate the service provider's network from the customer's network",
            "B. To connect multiple VLANs within a network",
            "C. To serve as a backup connection point",
            "D. To provide a location for network monitoring equipment"
        ],
        "answer": "A. To separate the service provider's network from the customer's network"
    },
    {
        "question": "Which of the following is a characteristic of single-mode fiber optic cable?",
        "options": [
            "A. It supports shorter transmission distances compared to multimode fiber",
            "B. It has a larger core diameter than multimode fiber",
            "C. It is typically used for long-distance data transmission",
            "D. It is more susceptible to signal attenuation than multimode fiber"
        ],
        "answer": "C. It is typically used for long-distance data transmission"
    },
    {
        "question": "What is the function of a media converter in a network?",
        "options": [
            "A. To amplify network signals over long distances",
            "B. To convert signals between different media types, such as fiber to copper",
            "C. To manage network traffic and reduce congestion",
            "D. To provide power to network devices over Ethernet"
        ],
        "answer": "B. To convert signals between different media types, such as fiber to copper"
    },
    {
        "question": "Which standard specifies the use of twisted-pair cabling for Ethernet networks operating at 10 Gbps?",
        "options": [
            "A. 1000Base-T",
            "B. 10GBase-T",
            "C. 100Base-TX",
            "D. 10Base-T"
        ],
        "answer": "B. 10GBase-T"
    },
    {
        "question": "Why is it important to adhere to bend radius limitations when installing fiber optic cables?",
        "options": [
            "A. To prevent signal loss and potential cable damage",
            "B. To reduce electromagnetic interference",
            "C. To ensure proper grounding of the cable",
            "D. To maintain the cable's fire-resistant properties"
        ],
        "answer": "A. To prevent signal loss and potential cable damage"
    },
    {
        "question": "Which of the following connectors is commonly used with coaxial cables in network installations?",
        "options": [
            "A. RJ45",
            "B. LC",
            "C. BNC",
            "D. SC"
        ],
        "answer": "C. BNC"
    },
    {
        "question": "What is the primary advantage of using a modular patch panel in a network installation?",
        "options": [
            "A. It reduces the need for cable management",
            "B. It allows for easy reconfiguration and scalability",
            "C. It enhances network security",
            "D. It increases data transmission speeds"
        ],
        "answer": "B. It allows for easy reconfiguration and scalability"
    },
    {
        "question": "What is the primary function of an Intermediate Distribution Frame (IDF) in a network infrastructure?",
        "options": [
            "A. To serve as the main connection point for all network equipment",
            "B. To provide interconnection between end devices and the Main Distribution Frame (MDF)",
            "C. To manage external network connections",
            "D. To store backup configurations for network devices"
        ],
        "answer": "B. To provide interconnection between end devices and the Main Distribution Frame (MDF)"
    },
    {
        "question": "Which component is typically housed in the Main Distribution Frame (MDF)?",
        "options": [
            "A. User workstations",
            "B. Core network switches and routers",
            "C. Wireless access points",
            "D. Client patch panels"
        ],
        "answer": "B. Core network switches and routers"
    },
    {
        "question": "What is the standard rack size width for most enterprise network equipment?",
        "options": [
            "A. 19 inches",
            "B. 21 inches",
            "C. 23 inches",
            "D. 25 inches"
        ],
        "answer": "A. 19 inches"
    },
    {
        "question": "Which airflow configuration should be considered for server racks to ensure proper cooling?",
        "options": [
            "A. Rear-to-front airflow",
            "B. Side-to-side airflow",
            "C. Port-side exhaust with front intake",
            "D. Randomized airflow"
        ],
        "answer": "A. Rear-to-front airflow"
    },
    {
        "question": "What is the primary purpose of a patch panel in a network rack?",
        "options": [
            "A. To increase data transmission speeds",
            "B. To terminate fiber optic cables",
            "C. To organize and manage network cables for easy reconfiguration",
            "D. To store backups of network configurations"
        ],
        "answer": "C. To organize and manage network cables for easy reconfiguration"
    },
    {
        "question": "Which cabling component is designed specifically to manage fiber optic connections?",
        "options": [
            "A. Patch panel",
            "B. Fiber distribution panel",
            "C. Keystone jack",
            "D. RJ45 connector"
        ],
        "answer": "B. Fiber distribution panel"
    },
    {
        "question": "Why is plenum-rated cabling required in certain installations?",
        "options": [
            "A. It has lower data transmission loss",
            "B. It meets fire safety regulations for air-handling spaces",
            "C. It allows for longer cable runs",
            "D. It is more resistant to moisture"
        ],
        "answer": "B. It meets fire safety regulations for air-handling spaces"
    },
    {
        "question": "Which component should be installed in a rack to help secure patch panel connections from unauthorized access?",
        "options": [
            "A. Fiber distribution panel",
            "B. Lockable enclosure",
            "C. Cable management tray",
            "D. Horizontal cable organizer"
        ],
        "answer": "B. Lockable enclosure"
    },
    {
        "question": "What is the recommended vertical height of a standard full-size network rack?",
        "options": [
            "A. 24U",
            "B. 42U",
            "C. 48U",
            "D. 60U"
        ],
        "answer": "B. 42U"
    },
    {
        "question": "Which of the following best describes the role of an MDF in a network installation?",
        "options": [
            "A. It connects an organization's network to an ISP",
            "B. It provides local termination for endpoint devices",
            "C. It serves as the secondary distribution point for cabling",
            "D. It eliminates the need for network switches"
        ],
        "answer": "A. It connects an organization's network to an ISP"
    },
    {
        "question": "Why is proper cable management essential in a network rack installation?",
        "options": [
            "A. To improve network bandwidth",
            "B. To prevent overheating and ensure easier troubleshooting",
            "C. To eliminate the need for fiber optics",
            "D. To extend the lifespan of network switches"
        ],
        "answer": "B. To prevent overheating and ensure easier troubleshooting"
    },
    {
        "question": "What is the primary function of a lockable rack enclosure?",
        "options": [
            "A. To improve airflow management",
            "B. To enhance physical security and prevent unauthorized access",
            "C. To boost network performance",
            "D. To store additional network configurations"
        ],
        "answer": "B. To enhance physical security and prevent unauthorized access"
    },
    {
        "question": "Which of the following factors should be considered when placing an IDF in a building?",
        "options": [
            "A. Proximity to the MDF",
            "B. Number of available power outlets",
            "C. Availability of Wi-Fi signals",
            "D. Compatibility with network adapters"
        ],
        "answer": "A. Proximity to the MDF"
    },
    {
        "question": "What is a potential drawback of placing an MDF in a non-climate-controlled environment?",
        "options": [
            "A. Increased risk of electromagnetic interference",
            "B. Higher chances of overheating and hardware failure",
            "C. Limited bandwidth availability",
            "D. Increased latency in network communication"
        ],
        "answer": "B. Higher chances of overheating and hardware failure"
    },
    {
        "question": "Which of the following rack sizes would be most suitable for a small office environment with limited space?",
        "options": [
            "A. 6U",
            "B. 24U",
            "C. 42U",
            "D. 48U"
        ],
        "answer": "A. 6U"
    },
    {
        "question": "Which cable type is best suited for backbone connections between an MDF and IDF?",
        "options": [
            "A. Cat 6 Ethernet",
            "B. Fiber optic cable",
            "C. Coaxial cable",
            "D. Shielded twisted pair"
        ],
        "answer": "B. Fiber optic cable"
    },
    {
        "question": "Why should network racks be installed with front-to-back airflow consideration?",
        "options": [
            "A. To maximize cooling efficiency and prevent equipment overheating",
            "B. To reduce cable clutter",
            "C. To simplify software updates",
            "D. To improve Wi-Fi coverage"
        ],
        "answer": "A. To maximize cooling efficiency and prevent equipment overheating"
    },
    {
        "question": "What is the purpose of a raised floor in a data center installation?",
        "options": [
            "A. To provide additional space for storage",
            "B. To allow better airflow and cable management",
            "C. To create a secure server enclosure",
            "D. To reduce electromagnetic interference"
        ],
        "answer": "B. To allow better airflow and cable management"
    },
    {
        "question": "Which of the following best describes a structured cabling system?",
        "options": [
            "A. A randomly connected network of cables",
            "B. An organized and standardized cabling infrastructure",
            "C. A single cable running directly from each device to the ISP",
            "D. A wireless network setup"
        ],
        "answer": "B. An organized and standardized cabling infrastructure"
    },
    {
        "question": "What is the primary purpose of a logical network diagram?",
        "options": [
            "A. To show the physical layout of devices in a rack",
            "B. To represent the flow of data and relationships between devices",
            "C. To display the exact location of cables and ports",
            "D. To provide a visual representation of warranty information"
        ],
        "answer": "B. To represent the flow of data and relationships between devices"
    },
    {
        "question": "Which of the following is a key difference between a physical and a logical diagram?",
        "options": [
            "A. Physical diagrams show IP addresses, while logical diagrams show cable types",
            "B. Physical diagrams display device locations, while logical diagrams show data flow",
            "C. Logical diagrams include rack layouts, while physical diagrams include wireless heat maps",
            "D. Physical diagrams focus on software licensing, while logical diagrams focus on hardware"
        ],
        "answer": "B. Physical diagrams display device locations, while logical diagrams show data flow"
    },
    {
        "question": "What is the primary purpose of a rack diagram?",
        "options": [
            "A. To show the logical flow of data between devices",
            "B. To display the physical arrangement of devices in a server rack",
            "C. To map out IP addresses and subnets",
            "D. To document software licensing agreements"
        ],
        "answer": "B. To display the physical arrangement of devices in a server rack"
    },
    {
        "question": "Which of the following is typically included in a cable map?",
        "options": [
            "A. IP address assignments",
            "B. Physical cable routes and connections",
            "C. Software licensing details",
            "D. Warranty expiration dates"
        ],
        "answer": "B. Physical cable routes and connections"
    },
    {
        "question": "What does Layer 1 of the OSI model primarily deal with?",
        "options": [
            "A. Data encryption and decryption",
            "B. Physical connections and cabling",
            "C. IP addressing and routing",
            "D. Error detection and correction"
        ],
        "answer": "B. Physical connections and cabling"
    },
    {
        "question": "Which of the following is a function of Layer 2 in the OSI model?",
        "options": [
            "A. Routing packets between networks",
            "B. Encapsulating data into frames",
            "C. Providing end-to-end communication",
            "D. Managing physical cabling"
        ],
        "answer": "B. Encapsulating data into frames"
    },
    {
        "question": "What is the primary purpose of an asset inventory in network management?",
        "options": [
            "A. To track the physical and logical location of network devices",
            "B. To monitor real-time network traffic",
            "C. To document IP address assignments",
            "D. To create wireless heat maps"
        ],
        "answer": "A. To track the physical and logical location of network devices"
    },
    {
        "question": "Which of the following is a key component of IP address management (IPAM)?",
        "options": [
            "A. Tracking software licenses",
            "B. Monitoring server temperatures",
            "C. Managing IP address allocations and subnets",
            "D. Creating rack diagrams"
        ],
        "answer": "C. Managing IP address allocations and subnets"
    },
    {
        "question": "What is the purpose of a service-level agreement (SLA) in networking?",
        "options": [
            "A. To define the physical layout of a network",
            "B. To specify the expected performance and availability of a service",
            "C. To document cable routes and connections",
            "D. To track hardware warranties"
        ],
        "answer": "B. To specify the expected performance and availability of a service"
    },
    {
        "question": "What is the primary use of a wireless survey or heat map?",
        "options": [
            "A. To document IP address assignments",
            "B. To visualize wireless signal strength and coverage",
            "C. To create logical network diagrams",
            "D. To track hardware inventory"
        ],
        "answer": "B. To visualize wireless signal strength and coverage"
    },
    {
        "question": "Which of the following is true about hardware documentation?",
        "options": [
            "A. It includes software licensing details",
            "B. It focuses on tracking physical devices and their configurations",
            "C. It is used to create logical network diagrams",
            "D. It primarily documents IP address assignments"
        ],
        "answer": "B. It focuses on tracking physical devices and their configurations"
    },
    {
        "question": "What is the purpose of a warranty support document?",
        "options": [
            "A. To track IP address allocations",
            "B. To provide details about hardware repair or replacement coverage",
            "C. To create wireless heat maps",
            "D. To document cable routes"
        ],
        "answer": "B. To provide details about hardware repair or replacement coverage"
    },
    {
        "question": "Which of the following is a key benefit of maintaining a software licensing document?",
        "options": [
            "A. To track physical cable routes",
            "B. To ensure compliance with legal and contractual obligations",
            "C. To create rack diagrams",
            "D. To monitor wireless signal strength"
        ],
        "answer": "B. To ensure compliance with legal and contractual obligations"
    },
    {
        "question": "What is the primary purpose of Layer 3 in the OSI model?",
        "options": [
            "A. To manage physical cabling",
            "B. To encapsulate data into frames",
            "C. To route packets between networks",
            "D. To provide error detection and correction"
        ],
        "answer": "C. To route packets between networks"
    },
    {
        "question": "Which of the following is a key element of a network diagram?",
        "options": [
            "A. Warranty expiration dates",
            "B. IP address assignments and device relationships",
            "C. Software licensing details",
            "D. Physical cable lengths"
        ],
        "answer": "B. IP address assignments and device relationships"
    },
    {
        "question": "What is the primary purpose of a cable map?",
        "options": [
            "A. To document software licenses",
            "B. To track hardware warranties",
            "C. To show the physical layout of cables and connections",
            "D. To create logical network diagrams"
        ],
        "answer": "C. To show the physical layout of cables and connections"
    },
    {
        "question": "Which of the following is a key benefit of maintaining an asset inventory?",
        "options": [
            "A. To monitor real-time network traffic",
            "B. To track the location and configuration of network devices",
            "C. To create wireless heat maps",
            "D. To document IP address assignments"
        ],
        "answer": "B. To track the location and configuration of network devices"
    },
    {
        "question": "What is the primary purpose of a wireless heat map?",
        "options": [
            "A. To document cable routes",
            "B. To visualize wireless signal strength and coverage",
            "C. To track hardware warranties",
            "D. To create logical network diagrams"
        ],
        "answer": "B. To visualize wireless signal strength and coverage"
    },
    {
        "question": "Which of the following is a key component of a service-level agreement (SLA)?",
        "options": [
            "A. Physical cable routes",
            "B. Expected uptime and performance metrics",
            "C. Software licensing details",
            "D. Hardware inventory"
        ],
        "answer": "B. Expected uptime and performance metrics"
    },
    {
        "question": "What is the primary purpose of IP address management (IPAM)?",
        "options": [
            "A. To track hardware warranties",
            "B. To manage IP address allocations and subnets",
            "C. To create rack diagrams",
            "D. To document cable routes"
        ],
        "answer": "B. To manage IP address allocations and subnets"
    },
    {
        "question": "Which of the following is a key benefit of maintaining a rack diagram?",
        "options": [
            "A. To track software licenses",
            "B. To visualize the physical arrangement of devices in a rack",
            "C. To monitor wireless signal strength",
            "D. To document IP address assignments"
        ],
        "answer": "B. To visualize the physical arrangement of devices in a rack"
    },
    {
        "question": "What is the primary purpose of a physical network diagram?",
        "options": [
            "A. To show the logical flow of data between devices",
            "B. To display the physical layout of devices and cables",
            "C. To document IP address assignments",
            "D. To track software licenses"
        ],
        "answer": "B. To display the physical layout of devices and cables"
    },
    {
        "question": "Which of the following is a key benefit of maintaining a logical network diagram?",
        "options": [
            "A. To track hardware warranties",
            "B. To visualize the flow of data and device relationships",
            "C. To document cable routes",
            "D. To monitor wireless signal strength"
        ],
        "answer": "B. To visualize the flow of data and device relationships"
    },
    {
        "question": "What is the primary purpose of a warranty support document?",
        "options": [
            "A. To track IP address allocations",
            "B. To provide details about hardware repair or replacement coverage",
            "C. To create wireless heat maps",
            "D. To document cable routes"
        ],
        "answer": "B. To provide details about hardware repair or replacement coverage"
    },
    {
        "question": "Which of the following is a key benefit of maintaining a software licensing document?",
        "options": [
            "A. To track physical cable routes",
            "B. To ensure compliance with legal and contractual obligations",
            "C. To create rack diagrams",
            "D. To monitor wireless signal strength"
        ],
        "answer": "B. To ensure compliance with legal and contractual obligations"
    },
    {
        "question": "Which type of diagram provides a high-level overview of network traffic flow between different network segments?",
        "options": [
            "A. Rack diagram",
            "B. Physical topology diagram",
            "C. Logical topology diagram",
            "D. Cable map"
        ],
        "answer": "C. Logical topology diagram"
    },
    {
        "question": "Which of the following best describes a rack diagram?",
        "options": [
            "A. A blueprint of network connectivity between devices",
            "B. A visual representation of physical hardware placement within a server rack",
            "C. A floor plan showing wireless access points and coverage areas",
            "D. A document listing all software licenses in an organization"
        ],
        "answer": "B. A visual representation of physical hardware placement within a server rack"
    },
    {
        "question": "A network administrator is troubleshooting a connectivity issue and discovers that the network cable layout does not match the expected design. Which type of documentation should be reviewed first?",
        "options": [
            "A. Logical topology diagram",
            "B. Rack diagram",
            "C. Cable map",
            "D. Asset inventory"
        ],
        "answer": "C. Cable map"
    },
    {
        "question": "Which of the following network layers is responsible for MAC addressing and frame forwarding?",
        "options": [
            "A. Layer 1",
            "B. Layer 2",
            "C. Layer 3",
            "D. Layer 4"
        ],
        "answer": "B. Layer 2"
    },
    {
        "question": "Which type of diagram is essential for planning and troubleshooting IP addressing and subnetting?",
        "options": [
            "A. Physical topology diagram",
            "B. Rack diagram",
            "C. IP address management (IPAM) diagram",
            "D. Wireless heat map"
        ],
        "answer": "C. IP address management (IPAM) diagram"
    },
    {
        "question": "Which of the following best describes a Layer 1 issue in a network?",
        "options": [
            "A. Incorrect VLAN assignment",
            "B. Misconfigured IP address",
            "C. Loose or damaged Ethernet cable",
            "D. Routing table misconfiguration"
        ],
        "answer": "C. Loose or damaged Ethernet cable"
    },
    {
        "question": "Which network component primarily operates at Layer 3?",
        "options": [
            "A. Switch",
            "B. Router",
            "C. Network Interface Card (NIC)",
            "D. Hub"
        ],
        "answer": "B. Router"
    },
    {
        "question": "A company needs to ensure compliance with software licensing agreements. Which document should they maintain?",
        "options": [
            "A. Network diagram",
            "B. Asset inventory",
            "C. Service-level agreement (SLA)",
            "D. Wireless heat map"
        ],
        "answer": "B. Asset inventory"
    },
    {
        "question": "Which document specifies the terms of service between a customer and a service provider, including uptime guarantees?",
        "options": [
            "A. IP address management (IPAM)",
            "B. Service-level agreement (SLA)",
            "C. Warranty support contract",
            "D. Logical topology diagram"
        ],
        "answer": "B. Service-level agreement (SLA)"
    },
    {
        "question": "Which tool is used to create a visual representation of Wi-Fi coverage within an office space?",
        "options": [
            "A. Cable tester",
            "B. Wireless survey/heat map",
            "C. Network topology diagram",
            "D. Rack diagram"
        ],
        "answer": "B. Wireless survey/heat map"
    },
    {
        "question": "Which layer of the OSI model is responsible for packet forwarding based on IP addresses?",
        "options": [
            "A. Layer 1",
            "B. Layer 2",
            "C. Layer 3",
            "D. Layer 4"
        ],
        "answer": "C. Layer 3"
    },
    {
        "question": "What is the main advantage of using an IP Address Management (IPAM) system?",
        "options": [
            "A. It secures network devices from unauthorized access",
            "B. It prevents network loops in Layer 2 environments",
            "C. It helps manage and allocate IP addresses efficiently",
            "D. It improves wireless network coverage"
        ],
        "answer": "C. It helps manage and allocate IP addresses efficiently"
    },
    {
        "question": "A network administrator is designing a cable map for a new office. What is the primary purpose of this document?",
        "options": [
            "A. To track device asset inventory",
            "B. To ensure proper IP address assignment",
            "C. To document cable routes and connections",
            "D. To optimize wireless signal distribution"
        ],
        "answer": "C. To document cable routes and connections"
    },
    {
        "question": "Which of the following is a key benefit of maintaining an asset inventory for network hardware?",
        "options": [
            "A. Ensures proper software licensing compliance",
            "B. Helps identify equipment for maintenance and upgrades",
            "C. Provides wireless signal strength analysis",
            "D. Improves physical security by limiting access to devices"
        ],
        "answer": "B. Helps identify equipment for maintenance and upgrades"
    },
    {
        "question": "An organization needs to ensure that all devices remain under manufacturer support. Which document should be reviewed?",
        "options": [
            "A. Licensing agreement",
            "B. Warranty support documentation",
            "C. Logical topology diagram",
            "D. Wireless heat map"
        ],
        "answer": "B. Warranty support documentation"
    },
    {
        "question": "A network administrator is setting up a wireless network in a multi-floor office building. What tool would best help identify coverage gaps?",
        "options": [
            "A. Cable tester",
            "B. Wireless survey/heat map",
            "C. IP address management (IPAM)",
            "D. Logical topology diagram"
        ],
        "answer": "B. Wireless survey/heat map"
    },
    {
        "question": "Which of the following is a common component found in a rack diagram?",
        "options": [
            "A. Wireless access points",
            "B. Subnet masks",
            "C. Server locations",
            "D. Heat maps"
        ],
        "answer": "C. Server locations"
    },
    {
        "question": "Which documentation is crucial for identifying all software licenses within an organization?",
        "options": [
            "A. Rack diagram",
            "B. Logical network diagram",
            "C. Software asset inventory",
            "D. Service-level agreement (SLA)"
        ],
        "answer": "C. Software asset inventory"
    },
    {
        "question": "A company wants to track warranty expiration dates for all networking equipment. Which document should they maintain?",
        "options": [
            "A. Hardware asset inventory",
            "B. IPAM records",
            "C. Wireless heat map",
            "D. Cable map"
        ],
        "answer": "A. Hardware asset inventory"
    },
    {
        "question": "Which of the following is a primary concern addressed by a service-level agreement (SLA)?",
        "options": [
            "A. Network topology design",
            "B. Hardware warranty expiration dates",
            "C. Uptime and performance guarantees",
            "D. Physical security of network devices"
        ],
        "answer": "C. Uptime and performance guarantees"
    },
    {
        "question": "A network administrator is tasked with documenting the physical layout of a new server room. Which of the following would be the most appropriate type of diagram to create?",
        "options": [
            "A. Logical network diagram",
            "B. Rack diagram",
            "C. Wireless heat map",
            "D. IP address management (IPAM) report"
        ],
        "answer": "B. Rack diagram"
    },
    {
        "question": "A company is experiencing intermittent connectivity issues in their wireless network. Which of the following tools should the network administrator use to identify areas with weak signal strength?",
        "options": [
            "A. Cable map",
            "B. Wireless heat map",
            "C. Logical network diagram",
            "D. Asset inventory"
        ],
        "answer": "B. Wireless heat map"
    },
    {
        "question": "A network technician is troubleshooting a connectivity issue and needs to trace the physical path of a cable from a workstation to a switch. Which of the following documents would be most helpful?",
        "options": [
            "A. Logical network diagram",
            "B. Cable map",
            "C. IP address management (IPAM) report",
            "D. Service-level agreement (SLA)"
        ],
        "answer": "B. Cable map"
    },
    {
        "question": "A company is expanding its network and needs to ensure that all new devices are properly documented. Which of the following should the network administrator update to track the new devices?",
        "options": [
            "A. Wireless heat map",
            "B. Asset inventory",
            "C. Logical network diagram",
            "D. Service-level agreement (SLA)"
        ],
        "answer": "B. Asset inventory"
    },
    {
        "question": "A network administrator is preparing for an audit and needs to ensure that all software licenses are up to date. Which of the following documents should the administrator review?",
        "options": [
            "A. Cable map",
            "B. Software licensing document",
            "C. Rack diagram",
            "D. Wireless heat map"
        ],
        "answer": "B. Software licensing document"
    },
    {
        "question": "A company is experiencing frequent downtime with their internet service. The network administrator needs to determine if the service provider is meeting their obligations. Which of the following documents should the administrator review?",
        "options": [
            "A. Service-level agreement (SLA)",
            "B. Logical network diagram",
            "C. Cable map",
            "D. Asset inventory"
        ],
        "answer": "A. Service-level agreement (SLA)"
    },
    {
        "question": "A network technician is planning to upgrade the firmware on all network switches. Which of the following documents would help the technician identify the models and locations of the switches?",
        "options": [
            "A. Wireless heat map",
            "B. Asset inventory",
            "C. Logical network diagram",
            "D. IP address management (IPAM) report"
        ],
        "answer": "B. Asset inventory"
    },
    {
        "question": "A company is deploying a new VoIP system and needs to ensure that all devices have unique IP addresses. Which of the following tools should the network administrator use to manage IP address assignments?",
        "options": [
            "A. Cable map",
            "B. IP address management (IPAM) tool",
            "C. Wireless heat map",
            "D. Rack diagram"
        ],
        "answer": "B. IP address management (IPAM) tool"
    },
    {
        "question": "A network administrator is troubleshooting a Layer 2 issue and needs to verify the MAC address table on a switch. Which of the following documents would provide the necessary information?",
        "options": [
            "A. Logical network diagram",
            "B. Cable map",
            "C. Asset inventory",
            "D. Rack diagram"
        ],
        "answer": "A. Logical network diagram"
    },
    {
        "question": "A company is relocating its data center and needs to document the current layout of servers and networking equipment. Which of the following diagrams would be most useful?",
        "options": [
            "A. Wireless heat map",
            "B. Rack diagram",
            "C. Logical network diagram",
            "D. IP address management (IPAM) report"
        ],
        "answer": "B. Rack diagram"
    },
    {
        "question": "A network administrator is troubleshooting a connectivity issue between two devices and needs to verify the physical connections. Which of the following documents would be most helpful?",
        "options": [
            "A. Logical network diagram",
            "B. Cable map",
            "C. Asset inventory",
            "D. Service-level agreement (SLA)"
        ],
        "answer": "B. Cable map"
    },
    {
        "question": "A company is deploying a new wireless network and needs to ensure optimal coverage throughout the building. Which of the following tools should the network administrator use to plan the deployment?",
        "options": [
            "A. Cable map",
            "B. Wireless heat map",
            "C. Logical network diagram",
            "D. Asset inventory"
        ],
        "answer": "B. Wireless heat map"
    },
    {
        "question": "A network administrator is preparing for a hardware refresh and needs to identify devices that are no longer under warranty. Which of the following documents should the administrator review?",
        "options": [
            "A. Asset inventory",
            "B. Logical network diagram",
            "C. Cable map",
            "D. IP address management (IPAM) report"
        ],
        "answer": "A. Asset inventory"
    },
    {
        "question": "A company is experiencing IP address conflicts on its network. Which of the following tools should the network administrator use to resolve the issue?",
        "options": [
            "A. Wireless heat map",
            "B. IP address management (IPAM) tool",
            "C. Cable map",
            "D. Rack diagram"
        ],
        "answer": "B. IP address management (IPAM) tool"
    },
    {
        "question": "A network administrator is troubleshooting a Layer 3 issue and needs to verify the routing table on a router. Which of the following documents would provide the necessary information?",
        "options": [
            "A. Logical network diagram",
            "B. Cable map",
            "C. Asset inventory",
            "D. Rack diagram"
        ],
        "answer": "A. Logical network diagram"
    },
    {
        "question": "A company is deploying a new application and needs to ensure that all servers have sufficient bandwidth. Which of the following documents would help the network administrator plan for the deployment?",
        "options": [
            "A. Logical network diagram",
            "B. Cable map",
            "C. Asset inventory",
            "D. Service-level agreement (SLA)"
        ],
        "answer": "A. Logical network diagram"
    },
    {
        "question": "A network administrator is troubleshooting a connectivity issue and needs to verify the physical layer connections. Which of the following tools would be most helpful?",
        "options": [
            "A. Cable tester",
            "B. Wireless heat map",
            "C. Logical network diagram",
            "D. IP address management (IPAM) report"
        ],
        "answer": "A. Cable tester"
    },
    {
        "question": "A company is preparing for a compliance audit and needs to ensure that all software licenses are properly documented. Which of the following documents should the network administrator review?",
        "options": [
            "A. Asset inventory",
            "B. Software licensing document",
            "C. Logical network diagram",
            "D. Cable map"
        ],
        "answer": "B. Software licensing document"
    },
    {
        "question": "A network administrator is troubleshooting a connectivity issue and needs to verify the IP address assignments for all devices. Which of the following tools should the administrator use?",
        "options": [
            "A. Wireless heat map",
            "B. IP address management (IPAM) tool",
            "C. Cable map",
            "D. Rack diagram"
        ],
        "answer": "B. IP address management (IPAM) tool"
    },
    {
        "question": "A company is experiencing frequent downtime with their internet service. The network administrator needs to determine if the service provider is meeting their obligations. Which of the following documents should the administrator review?",
        "options": [
            "A. Service-level agreement (SLA)",
            "B. Logical network diagram",
            "C. Cable map",
            "D. Asset inventory"
        ],
        "answer": "A. Service-level agreement (SLA)"
    },
    {
        "question": "Which type of diagram provides a high-level overview of network traffic flow between different network segments?",
        "options": [
            "A. Rack diagram",
            "B. Physical topology diagram",
            "C. Logical topology diagram",
            "D. Cable map"
        ],
        "answer": "C. Logical topology diagram"
    },
    {
        "question": "Which of the following best describes a rack diagram?",
        "options": [
            "A. A blueprint of network connectivity between devices",
            "B. A visual representation of physical hardware placement within a server rack",
            "C. A floor plan showing wireless access points and coverage areas",
            "D. A document listing all software licenses in an organization"
        ],
        "answer": "B. A visual representation of physical hardware placement within a server rack"
    },
    {
        "question": "A network administrator is troubleshooting a connectivity issue and discovers that the network cable layout does not match the expected design. Which type of documentation should be reviewed first?",
        "options": [
            "A. Logical topology diagram",
            "B. Rack diagram",
            "C. Cable map",
            "D. Asset inventory"
        ],
        "answer": "C. Cable map"
    },
    {
        "question": "Which of the following network layers is responsible for MAC addressing and frame forwarding?",
        "options": [
            "A. Layer 1",
            "B. Layer 2",
            "C. Layer 3",
            "D. Layer 4"
        ],
        "answer": "B. Layer 2"
    },
    {
        "question": "Which type of diagram is essential for planning and troubleshooting IP addressing and subnetting?",
        "options": [
            "A. Physical topology diagram",
            "B. Rack diagram",
            "C. IP address management (IPAM) diagram",
            "D. Wireless heat map"
        ],
        "answer": "C. IP address management (IPAM) diagram"
    },
    {
        "question": "Which of the following best describes a Layer 1 issue in a network?",
        "options": [
            "A. Incorrect VLAN assignment",
            "B. Misconfigured IP address",
            "C. Loose or damaged Ethernet cable",
            "D. Routing table misconfiguration"
        ],
        "answer": "C. Loose or damaged Ethernet cable"
    },
    {
        "question": "Which network component primarily operates at Layer 3?",
        "options": [
            "A. Switch",
            "B. Router",
            "C. Network Interface Card (NIC)",
            "D. Hub"
        ],
        "answer": "B. Router"
    },
    {
        "question": "A company needs to ensure compliance with software licensing agreements. Which document should they maintain?",
        "options": [
            "A. Network diagram",
            "B. Asset inventory",
            "C. Service-level agreement (SLA)",
            "D. Wireless heat map"
        ],
        "answer": "B. Asset inventory"
    },
    {
        "question": "Which document specifies the terms of service between a customer and a service provider, including uptime guarantees?",
        "options": [
            "A. IP address management (IPAM)",
            "B. Service-level agreement (SLA)",
            "C. Warranty support contract",
            "D. Logical topology diagram"
        ],
        "answer": "B. Service-level agreement (SLA)"
    },
    {
        "question": "Which tool is used to create a visual representation of Wi-Fi coverage within an office space?",
        "options": [
            "A. Cable tester",
            "B. Wireless survey/heat map",
            "C. Network topology diagram",
            "D. Rack diagram"
        ],
        "answer": "B. Wireless survey/heat map"
    },
    {
        "question": "Which layer of the OSI model is responsible for packet forwarding based on IP addresses?",
        "options": [
            "A. Layer 1",
            "B. Layer 2",
            "C. Layer 3",
            "D. Layer 4"
        ],
        "answer": "C. Layer 3"
    },
    {
        "question": "What is the main advantage of using an IP Address Management (IPAM) system?",
        "options": [
            "A. It secures network devices from unauthorized access",
            "B. It prevents network loops in Layer 2 environments",
            "C. It helps manage and allocate IP addresses efficiently",
            "D. It improves wireless network coverage"
        ],
        "answer": "C. It helps manage and allocate IP addresses efficiently"
    },
    {
        "question": "A network administrator is designing a cable map for a new office. What is the primary purpose of this document?",
        "options": [
            "A. To track device asset inventory",
            "B. To ensure proper IP address assignment",
            "C. To document cable routes and connections",
            "D. To optimize wireless signal distribution"
        ],
        "answer": "C. To document cable routes and connections"
    },
    {
        "question": "Which of the following is a key benefit of maintaining an asset inventory for network hardware?",
        "options": [
            "A. Ensures proper software licensing compliance",
            "B. Helps identify equipment for maintenance and upgrades",
            "C. Provides wireless signal strength analysis",
            "D. Improves physical security by limiting access to devices"
        ],
        "answer": "B. Helps identify equipment for maintenance and upgrades"
    },
    {
        "question": "An organization needs to ensure that all devices remain under manufacturer support. Which document should be reviewed?",
        "options": [
            "A. Licensing agreement",
            "B. Warranty support documentation",
            "C. Logical topology diagram",
            "D. Wireless heat map"
        ],
        "answer": "B. Warranty support documentation"
    },
    {
        "question": "A network administrator is setting up a wireless network in a multi-floor office building. What tool would best help identify coverage gaps?",
        "options": [
            "A. Cable tester",
            "B. Wireless survey/heat map",
            "C. IP address management (IPAM)",
            "D. Logical topology diagram"
        ],
        "answer": "B. Wireless survey/heat map"
    },
    {
        "question": "Which of the following is a common component found in a rack diagram?",
        "options": [
            "A. Wireless access points",
            "B. Subnet masks",
            "C. Server locations",
            "D. Heat maps"
        ],
        "answer": "C. Server locations"
    },
    {
        "question": "Which documentation is crucial for identifying all software licenses within an organization?",
        "options": [
            "A. Rack diagram",
            "B. Logical network diagram",
            "C. Software asset inventory",
            "D. Service-level agreement (SLA)"
        ],
        "answer": "C. Software asset inventory"
    },
    {
        "question": "A company wants to track warranty expiration dates for all networking equipment. Which document should they maintain?",
        "options": [
            "A. Hardware asset inventory",
            "B. IPAM records",
            "C. Wireless heat map",
            "D. Cable map"
        ],
        "answer": "A. Hardware asset inventory"
    },
    {
        "question": "Which of the following is a primary concern addressed by a service-level agreement (SLA)?",
        "options": [
            "A. Network topology design",
            "B. Hardware warranty expiration dates",
            "C. Uptime and performance guarantees",
            "D. Physical security of network devices"
        ],
        "answer": "C. Uptime and performance guarantees"
    },
    {
        "question": "Which type of documentation helps track which user is assigned to a specific IP address at any given time?",
        "options": [
            "A. Logical network diagram",
            "B. IP address management (IPAM)",
            "C. Rack diagram",
            "D. Wireless survey"
        ],
        "answer": "B. IP address management (IPAM)"
    },
    {
        "question": "What is the main benefit of a physical network diagram?",
        "options": [
            "A. Shows real-world cable paths and connections",
            "B. Illustrates virtual routing configurations",
            "C. Displays software license allocation",
            "D. Defines security policies and procedures"
        ],
        "answer": "A. Shows real-world cable paths and connections"
    },
    {
        "question": "Which document would help a technician determine the correct location for installing new networking hardware in a server room?",
        "options": [
            "A. Logical topology diagram",
            "B. Rack diagram",
            "C. Cable map",
            "D. IPAM records"
        ],
        "answer": "B. Rack diagram"
    },
    {
        "question": "A network administrator is designing a structured cabling system for a new building. Which document will best assist in planning cable routes?",
        "options": [
            "A. Network topology diagram",
            "B. Rack diagram",
            "C. Cable map",
            "D. Wireless heat map"
        ],
        "answer": "C. Cable map"
    },
    {
        "question": "What is a key consideration when documenting a Layer 1 network diagram?",
        "options": [
            "A. VLAN assignments",
            "B. IP subnetting structure",
            "C. Cable types and physical connections",
            "D. Routing protocols used"
        ],
        "answer": "C. Cable types and physical connections"
    },
    {
        "question": "Which type of diagram is most useful when troubleshooting network segmentation issues?",
        "options": [
            "A. Rack diagram",
            "B. Cable map",
            "C. Logical network diagram",
            "D. Wireless survey"
        ],
        "answer": "C. Logical network diagram"
    },
    {
        "question": "Which of the following is an example of Layer 2 network documentation?",
        "options": [
            "A. VLAN assignments",
            "B. Routing table configurations",
            "C. Fiber optic cable routes",
            "D. Wireless signal coverage"
        ],
        "answer": "A. VLAN assignments"
    },
    {
        "question": "What type of documentation is essential for maintaining accurate records of all network switches, firewalls, and access points?",
        "options": [
            "A. Service-level agreement",
            "B. Network asset inventory",
            "C. Wireless heat map",
            "D. Logical topology diagram"
        ],
        "answer": "B. Network asset inventory"
    },
    {
        "question": "A technician is troubleshooting a recurring issue in a company's wireless network. Which document would best help identify interference or dead zones?",
        "options": [
            "A. Network topology diagram",
            "B. Wireless survey/heat map",
            "C. Asset inventory",
            "D. IPAM database"
        ],
        "answer": "B. Wireless survey/heat map"
    },
    {
        "question": "Which of the following would NOT typically be included in an IPAM system?",
        "options": [
            "A. DHCP lease tracking",
            "B. MAC address assignments",
            "C. Wireless channel utilization",
            "D. Subnet allocations"
        ],
        "answer": "C. Wireless channel utilization"
    },
    {
        "question": "Which document outlines the expected response time and resolution process for a vendor providing network support?",
        "options": [
            "A. Rack diagram",
            "B. Asset inventory",
            "C. Service-level agreement (SLA)",
            "D. IPAM report"
        ],
        "answer": "C. Service-level agreement (SLA)"
    },
    {
        "question": "Which layer of the OSI model is primarily responsible for ensuring packets reach the correct destination based on logical addressing?",
        "options": [
            "A. Layer 1",
            "B. Layer 2",
            "C. Layer 3",
            "D. Layer 4"
        ],
        "answer": "C. Layer 3"
    },
    {
        "question": "A technician needs to verify warranty information for network switches. Which document should they check?",
        "options": [
            "A. Logical topology diagram",
            "B. Warranty support records",
            "C. Wireless heat map",
            "D. IPAM database"
        ],
        "answer": "B. Warranty support records"
    },
    {
        "question": "A company is moving to a new office and wants to document all existing software to ensure license compliance. Which document should be reviewed?",
        "options": [
            "A. Logical topology diagram",
            "B. Software asset inventory",
            "C. Service-level agreement",
            "D. Wireless heat map"
        ],
        "answer": "B. Software asset inventory"
    },
    {
        "question": "Which of the following best describes the purpose of an IP address management (IPAM) system?",
        "options": [
            "A. Managing and monitoring IP address allocations",
            "B. Enhancing wireless signal coverage",
            "C. Maintaining a backup of all VLAN assignments",
            "D. Documenting physical rack configurations"
        ],
        "answer": "A. Managing and monitoring IP address allocations"
    },
    {
        "question": "What is the purpose of a wireless site survey?",
        "options": [
            "A. To determine optimal access point placement",
            "B. To create a logical network diagram",
            "C. To manage IP address allocations",
            "D. To track physical asset locations"
        ],
        "answer": "A. To determine optimal access point placement"
    },
    {
        "question": "Which document would be most useful for troubleshooting a network outage affecting only a specific VLAN?",
        "options": [
            "A. Logical topology diagram",
            "B. Rack diagram",
            "C. Wireless heat map",
            "D. IPAM database"
        ],
        "answer": "A. Logical topology diagram"
    },
    {
        "question": "A company wants to ensure compliance with software licensing agreements. Which document should they maintain?",
        "options": [
            "A. Wireless heat map",
            "B. Asset inventory",
            "C. Service-level agreement (SLA)",
            "D. Cable map"
        ],
        "answer": "B. Asset inventory"
    },
    {
        "question": "Which documentation would best help a technician determine the proper switch port configuration for a specific network device?",
        "options": [
            "A. Rack diagram",
            "B. VLAN assignment documentation",
            "C. Wireless survey",
            "D. Cable map"
        ],
        "answer": "B. VLAN assignment documentation"
    },
    {
        "question": "What is the main benefit of maintaining an updated network asset inventory?",
        "options": [
            "A. Ensures efficient IP address allocation",
            "B. Provides real-time tracking of software updates",
            "C. Identifies devices for maintenance and replacement planning",
            "D. Enhances wireless network coverage"
        ],
        "answer": "C. Identifies devices for maintenance and replacement planning"
    },
    {
        "question": "A company needs to track the expiration dates of their software licenses. Which document should they use?",
        "options": [
            "A. Service-level agreement",
            "B. Software asset inventory",
            "C. IPAM database",
            "D. Wireless heat map"
        ],
        "answer": "B. Software asset inventory"
    },
    {
        "question": "What is the main risk of continuing to use hardware that has reached End-of-Life (EOL)?",
        "options": [
            "A. Increased warranty costs",
            "B. Lack of vendor support and security updates",
            "C. Higher initial purchasing costs",
            "D. Decreased network bandwidth"
        ],
        "answer": "B. Lack of vendor support and security updates"
    },
    {
        "question": "A network switch has reached End-of-Support (EOS). What is the best course of action?",
        "options": [
            "A. Continue using the switch and apply firmware updates",
            "B. Perform a software rollback to an older, stable version",
            "C. Plan for hardware replacement to avoid security vulnerabilities",
            "D. Disable unnecessary ports to reduce exposure"
        ],
        "answer": "C. Plan for hardware replacement to avoid security vulnerabilities"
    },
    {
        "question": "Which document is most critical when decommissioning outdated networking hardware?",
        "options": [
            "A. Configuration management records",
            "B. Service-level agreement",
            "C. Wireless heat map",
            "D. Change request log"
        ],
        "answer": "A. Configuration management records"
    },
    {
        "question": "What is the primary purpose of applying firmware updates to networking equipment?",
        "options": [
            "A. To change the physical structure of the hardware",
            "B. To enhance security and fix known vulnerabilities",
            "C. To overclock the processor for better performance",
            "D. To downgrade to a previous software version"
        ],
        "answer": "B. To enhance security and fix known vulnerabilities"
    },
    {
        "question": "Which process ensures that network changes follow a structured approval and implementation workflow?",
        "options": [
            "A. Configuration baseline",
            "B. Change management",
            "C. End-of-life management",
            "D. IP address management"
        ],
        "answer": "B. Change management"
    },
    {
        "question": "What is the purpose of maintaining a backup configuration for networking devices?",
        "options": [
            "A. To use as a reference for firmware updates",
            "B. To allow quick recovery after hardware failure",
            "C. To track IP address changes",
            "D. To comply with service-level agreements"
        ],
        "answer": "B. To allow quick recovery after hardware failure"
    },
    {
        "question": "Which type of configuration is considered the standard for new deployments?",
        "options": [
            "A. Backup configuration",
            "B. Golden configuration",
            "C. End-of-support configuration",
            "D. Change request configuration"
        ],
        "answer": "B. Golden configuration"
    },
    {
        "question": "Which of the following is an example of a service request in network management?",
        "options": [
            "A. Replacing an end-of-life firewall",
            "B. Requesting access to a new VLAN",
            "C. Patching a critical firmware vulnerability",
            "D. Performing a factory reset on a router"
        ],
        "answer": "B. Requesting access to a new VLAN"
    },
    {
        "question": "A company wants to track all changes to its core switches, including firmware updates and reconfigurations. Which system should they use?",
        "options": [
            "A. IPAM",
            "B. Configuration management database (CMDB)",
            "C. Wireless heat map tool",
            "D. End-of-support tracker"
        ],
        "answer": "B. Configuration management database (CMDB)"
    },
    {
        "question": "What is a key benefit of applying patches and bug fixes to networking devices?",
        "options": [
            "A. Increases physical security of network cabinets",
            "B. Eliminates the need for firewalls",
            "C. Reduces vulnerabilities and improves stability",
            "D. Replaces end-of-life hardware"
        ],
        "answer": "C. Reduces vulnerabilities and improves stability"
    },
    {
        "question": "What is the best approach when a major software update causes unexpected downtime?",
        "options": [
            "A. Wait for vendor support to address the issue",
            "B. Roll back to the last known stable configuration",
            "C. Disable all network monitoring services",
            "D. Remove all devices from the network and reconfigure them"
        ],
        "answer": "B. Roll back to the last known stable configuration"
    },
    {
        "question": "Which documentation ensures consistency in network configurations across multiple locations?",
        "options": [
            "A. Baseline configuration",
            "B. End-of-life (EOL) policy",
            "C. Wireless survey",
            "D. Physical network diagram"
        ],
        "answer": "A. Baseline configuration"
    },
    {
        "question": "A company plans to replace all outdated routers with new models. What should be done first?",
        "options": [
            "A. Decommission the old routers immediately",
            "B. Install the new routers without any testing",
            "C. Develop a change management plan",
            "D. Remove all configurations before installation"
        ],
        "answer": "C. Develop a change management plan"
    },
    {
        "question": "What is the best practice before applying an OS update to critical network infrastructure?",
        "options": [
            "A. Apply the update immediately to minimize downtime",
            "B. Disable all security features before updating",
            "C. Test the update in a lab environment first",
            "D. Remove all access control lists before proceeding"
        ],
        "answer": "C. Test the update in a lab environment first"
    },
    {
        "question": "Which of the following is a key component of a production configuration?",
        "options": [
            "A. Experimental firmware versions",
            "B. Stable, tested settings for live network operations",
            "C. Unapproved changes for testing",
            "D. Unused VLAN assignments"
        ],
        "answer": "B. Stable, tested settings for live network operations"
    },
    {
        "question": "Which document is essential when tracking software license compliance?",
        "options": [
            "A. Service-level agreement",
            "B. Asset inventory",
            "C. Wireless heat map",
            "D. IP address allocation list"
        ],
        "answer": "B. Asset inventory"
    },
    {
        "question": "A network administrator needs to roll out a firmware update to multiple switches. What is the best way to ensure a smooth deployment?",
        "options": [
            "A. Apply the update without testing",
            "B. Update all switches at once to minimize disruption",
            "C. Test the update in a lab, then roll it out in phases",
            "D. Downgrade firmware versions first"
        ],
        "answer": "C. Test the update in a lab, then roll it out in phases"
    },
    {
        "question": "Which of the following should be updated regularly to reflect new configurations and hardware changes?",
        "options": [
            "A. Backup configuration",
            "B. Service request tracking system",
            "C. Configuration management database (CMDB)",
            "D. Wireless heat map"
        ],
        "answer": "C. Configuration management database (CMDB)"
    },
    {
        "question": "What is a key reason for maintaining backup configurations for networking devices?",
        "options": [
            "A. Allows for quick recovery after a failure",
            "B. Prevents unauthorized firmware updates",
            "C. Increases the performance of network devices",
            "D. Eliminates the need for change management"
        ],
        "answer": "A. Allows for quick recovery after a failure"
    },
    {
        "question": "What is a key reason organizations follow an End-of-Life (EOL) policy for hardware?",
        "options": [
            "A. To increase the resale value of old equipment",
            "B. To ensure continued vendor support and security updates",
            "C. To decrease network bandwidth usage",
            "D. To comply with data retention policies"
        ],
        "answer": "B. To ensure continued vendor support and security updates"
    },
    {
        "question": "Which of the following should be done when decommissioning an outdated network device?",
        "options": [
            "A. Perform a factory reset before disposal",
            "B. Transfer its configuration to all active devices",
            "C. Keep it powered on as a backup device",
            "D. Store it indefinitely in case of future use"
        ],
        "answer": "A. Perform a factory reset before disposal"
    },
    {
        "question": "What is the primary purpose of change management in networking?",
        "options": [
            "A. To increase employee access to network devices",
            "B. To ensure that all changes are documented, approved, and tested",
            "C. To prevent all modifications to the network",
            "D. To reduce the cost of network maintenance"
        ],
        "answer": "B. To ensure that all changes are documented, approved, and tested"
    },
    {
        "question": "Which document provides a structured approach to implementing network changes while minimizing disruptions?",
        "options": [
            "A. Change management policy",
            "B. Network baseline configuration",
            "C. Service-level agreement",
            "D. Wireless site survey report"
        ],
        "answer": "A. Change management policy"
    },
    {
        "question": "Which phase of the change management process includes user impact analysis and rollback planning?",
        "options": [
            "A. Request initiation",
            "B. Change review and approval",
            "C. Implementation",
            "D. Post-change validation"
        ],
        "answer": "B. Change review and approval"
    },
    {
        "question": "Which of the following is considered part of an organization’s asset inventory?",
        "options": [
            "A. List of approved wireless SSIDs",
            "B. A record of all hardware and software resources",
            "C. A catalog of user access privileges",
            "D. A physical layout of the data center"
        ],
        "answer": "B. A record of all hardware and software resources"
    },
    {
        "question": "Which of the following should be regularly updated to ensure an accurate view of all network hardware and software?",
        "options": [
            "A. Configuration baseline",
            "B. Asset inventory",
            "C. Change management request log",
            "D. SLA agreements"
        ],
        "answer": "B. Asset inventory"
    },
    {
        "question": "A company needs to track the status of service requests submitted by employees. Which system is best suited for this task?",
        "options": [
            "A. Patch management system",
            "B. Change request log",
            "C. Service request tracking system",
            "D. Network monitoring software"
        ],
        "answer": "C. Service request tracking system"
    },
    {
        "question": "Which of the following is an example of a production configuration?",
        "options": [
            "A. A lab environment used for testing firmware updates",
            "B. A stable, validated setup actively running on the network",
            "C. An experimental VLAN configuration",
            "D. A backup configuration stored on an offline server"
        ],
        "answer": "B. A stable, validated setup actively running on the network"
    },
    {
        "question": "Which of the following is the best method to apply critical software patches to a production environment?",
        "options": [
            "A. Apply them immediately to all systems",
            "B. Test them in a staging environment before deploying",
            "C. Wait for vendor recommendations before installing",
            "D. Disable security settings before patching"
        ],
        "answer": "B. Test them in a staging environment before deploying"
    },
    {
        "question": "Which configuration type should be used as a reference when setting up a new network device?",
        "options": [
            "A. End-of-life configuration",
            "B. Baseline configuration",
            "C. Randomized configuration",
            "D. Default factory settings"
        ],
        "answer": "B. Baseline configuration"
    },
    {
        "question": "What is a key benefit of implementing a configuration management system?",
        "options": [
            "A. Reduces the need for firewall rules",
            "B. Ensures consistent network settings and quick recovery",
            "C. Eliminates the need for software updates",
            "D. Increases bandwidth by optimizing routing paths"
        ],
        "answer": "B. Ensures consistent network settings and quick recovery"
    },
    {
        "question": "Which of the following would be considered a 'golden configuration'?",
        "options": [
            "A. A configuration stored in an end-of-life database",
            "B. A secure and optimized configuration used as a template",
            "C. A temporary configuration used during maintenance",
            "D. An untested setup used for experimentation"
        ],
        "answer": "B. A secure and optimized configuration used as a template"
    },
    {
        "question": "Which tool is used to manage software licensing compliance?",
        "options": [
            "A. Patch management system",
            "B. Configuration management database (CMDB)",
            "C. IP address management system (IPAM)",
            "D. Service request tracking system"
        ],
        "answer": "B. Configuration management database (CMDB)"
    },
    {
        "question": "A network administrator needs to ensure firmware updates do not disrupt business operations. What should they do first?",
        "options": [
            "A. Apply the update to all devices simultaneously",
            "B. Test the update in a lab environment",
            "C. Roll back all devices to factory settings",
            "D. Disable antivirus before applying the update"
        ],
        "answer": "B. Test the update in a lab environment"
    },
    {
        "question": "Which of the following is a best practice when implementing configuration changes on a critical network?",
        "options": [
            "A. Apply all changes during business hours",
            "B. Implement and verify changes in a test environment first",
            "C. Ignore rollback plans to reduce complexity",
            "D. Apply changes without logging them"
        ],
        "answer": "B. Implement and verify changes in a test environment first"
    },
    {
        "question": "Which of the following must be included in a change request document?",
        "options": [
            "A. Justification for the change and rollback plan",
            "B. List of users affected but no rollback details",
            "C. The vendor’s contact information",
            "D. A summary of unrelated network changes"
        ],
        "answer": "A. Justification for the change and rollback plan"
    },
    {
        "question": "What is the purpose of firmware in network devices?",
        "options": [
            "A. To improve network speeds",
            "B. To provide the software that controls the device's hardware functions",
            "C. To replace physical network hardware",
            "D. To function as a firewall"
        ],
        "answer": "B. To provide the software that controls the device's hardware functions"
    },
    {
        "question": "Which of the following describes a proper change management process?",
        "options": [
            "A. Immediate implementation followed by documentation",
            "B. Planning, approval, testing, implementation, and validation",
            "C. Random changes implemented when needed",
            "D. Testing in production before approval"
        ],
        "answer": "B. Planning, approval, testing, implementation, and validation"
    },
    {
        "question": "A network administrator needs to monitor traffic on a specific switch port for troubleshooting purposes. Which of the following features should the administrator enable?",
        "options": [
            "A. Port mirroring",
            "B. Network discovery",
            "C. Traffic analysis",
            "D. Configuration monitoring"
        ],
        "answer": "A. Port mirroring"
    },
    {
        "question": "A company is deploying a new network monitoring tool and wants to automatically detect all devices on the network. Which of the following features should the administrator configure?",
        "options": [
            "A. Port mirroring",
            "B. Network discovery",
            "C. Traffic analysis",
            "D. Availability monitoring"
        ],
        "answer": "B. Network discovery"
    },
    {
        "question": "A network administrator is troubleshooting a network performance issue and needs to analyze traffic patterns. Which of the following tools would provide the MOST detailed information?",
        "options": [
            "A. Port mirroring",
            "B. Network discovery",
            "C. Traffic analysis",
            "D. Configuration monitoring"
        ],
        "answer": "C. Traffic analysis"
    },
    {
        "question": "A company is using a monitoring tool to track the uptime of critical network devices. Which of the following features is being used?",
        "options": [
            "A. Performance monitoring",
            "B. Availability monitoring",
            "C. Configuration monitoring",
            "D. Network discovery"
        ],
        "answer": "B. Availability monitoring"
    },
    {
        "question": "A network administrator is configuring a monitoring tool to track CPU and memory usage on network devices. Which of the following features is being configured?",
        "options": [
            "A. Performance monitoring",
            "B. Availability monitoring",
            "C. Configuration monitoring",
            "D. Traffic analysis"
        ],
        "answer": "A. Performance monitoring"
    },
    {
        "question": "A company is using a monitoring tool to ensure that all network devices are running the correct firmware version. Which of the following features is being used?",
        "options": [
            "A. Performance monitoring",
            "B. Availability monitoring",
            "C. Configuration monitoring",
            "D. Network discovery"
        ],
        "answer": "C. Configuration monitoring"
    },
    {
        "question": "A network administrator is troubleshooting a network issue and needs to capture traffic from a specific switch port. Which of the following features should the administrator enable?",
        "options": [
            "A. Port mirroring",
            "B. Network discovery",
            "C. Traffic analysis",
            "D. Availability monitoring"
        ],
        "answer": "A. Port mirroring"
    },
    {
        "question": "A company is deploying a new network monitoring tool and wants to schedule regular scans to detect new devices. Which of the following features should the administrator configure?",
        "options": [
            "A. Ad hoc network discovery",
            "B. Scheduled network discovery",
            "C. Traffic analysis",
            "D. Configuration monitoring"
        ],
        "answer": "B. Scheduled network discovery"
    },
    {
        "question": "A network administrator is troubleshooting a network performance issue and needs to analyze traffic patterns. Which of the following tools would provide the MOST detailed information?",
        "options": [
            "A. Port mirroring",
            "B. Network discovery",
            "C. Traffic analysis",
            "D. Configuration monitoring"
        ],
        "answer": "C. Traffic analysis"
    },
    {
        "question": "A company is using a monitoring tool to track the uptime of critical network devices. Which of the following features is being used?",
        "options": [
            "A. Performance monitoring",
            "B. Availability monitoring",
            "C. Configuration monitoring",
            "D. Network discovery"
        ],
        "answer": "B. Availability monitoring"
    },
    {
        "question": "A network administrator is configuring a monitoring tool to track CPU and memory usage on network devices. Which of the following features is being configured?",
        "options": [
            "A. Performance monitoring",
            "B. Availability monitoring",
            "C. Configuration monitoring",
            "D. Traffic analysis"
        ],
        "answer": "A. Performance monitoring"
    },
    {
        "question": "A company is using a monitoring tool to ensure that all network devices are running the correct firmware version. Which of the following features is being used?",
        "options": [
            "A. Performance monitoring",
            "B. Availability monitoring",
            "C. Configuration monitoring",
            "D. Network discovery"
        ],
        "answer": "C. Configuration monitoring"
    },
    {
        "question": "A network administrator is troubleshooting a network issue and needs to capture traffic from a specific switch port. Which of the following features should the administrator enable?",
        "options": [
            "A. Port mirroring",
            "B. Network discovery",
            "C. Traffic analysis",
            "D. Availability monitoring"
        ],
        "answer": "A. Port mirroring"
    },
    {
        "question": "A company is deploying a new network monitoring tool and wants to schedule regular scans to detect new devices. Which of the following features should the administrator configure?",
        "options": [
            "A. Ad hoc network discovery",
            "B. Scheduled network discovery",
            "C. Traffic analysis",
            "D. Configuration monitoring"
        ],
        "answer": "B. Scheduled network discovery"
    },
    {
        "question": "A network administrator is troubleshooting a network performance issue and needs to analyze traffic patterns. Which of the following tools would provide the MOST detailed information?",
        "options": [
            "A. Port mirroring",
            "B. Network discovery",
            "C. Traffic analysis",
            "D. Configuration monitoring"
        ],
        "answer": "C. Traffic analysis"
    },
    {
        "question": "A company is using a monitoring tool to track the uptime of critical network devices. Which of the following features is being used?",
        "options": [
            "A. Performance monitoring",
            "B. Availability monitoring",
            "C. Configuration monitoring",
            "D. Network discovery"
        ],
        "answer": "B. Availability monitoring"
    },
    {
        "question": "A network administrator is configuring a monitoring tool to track CPU and memory usage on network devices. Which of the following features is being configured?",
        "options": [
            "A. Performance monitoring",
            "B. Availability monitoring",
            "C. Configuration monitoring",
            "D. Traffic analysis"
        ],
        "answer": "A. Performance monitoring"
    },
    {
        "question": "A company is using a monitoring tool to ensure that all network devices are running the correct firmware version. Which of the following features is being used?",
        "options": [
            "A. Performance monitoring",
            "B. Availability monitoring",
            "C. Configuration monitoring",
            "D. Network discovery"
        ],
        "answer": "C. Configuration monitoring"
    },
    {
        "question": "A network administrator is troubleshooting a network issue and needs to capture traffic from a specific switch port. Which of the following features should the administrator enable?",
        "options": [
            "A. Port mirroring",
            "B. Network discovery",
            "C. Traffic analysis",
            "D. Availability monitoring"
        ],
        "answer": "A. Port mirroring"
    },
    {
        "question": "A company is deploying a new network monitoring tool and wants to schedule regular scans to detect new devices. Which of the following features should the administrator configure?",
        "options": [
            "A. Ad hoc network discovery",
            "B. Scheduled network discovery",
            "C. Traffic analysis",
            "D. Configuration monitoring"
        ],
        "answer": "B. Scheduled network discovery"
    },
    {
        "question": "A network administrator is troubleshooting a network performance issue and needs to analyze traffic patterns. Which of the following tools would provide flow data to help identify the source of the issue?",
        "options": [
            "A. SNMP",
            "B. NetFlow",
            "C. Syslog",
            "D. SIEM"
        ],
        "answer": "B. NetFlow"
    },
    {
        "question": "A company is experiencing intermittent network outages, and the network administrator needs to capture and analyze individual packets to diagnose the issue. Which of the following tools should the administrator use?",
        "options": [
            "A. NetFlow",
            "B. Wireshark",
            "C. Syslog",
            "D. SIEM"
        ],
        "answer": "B. Wireshark"
    },
    {
        "question": "A network administrator is setting up a monitoring system to detect unusual network activity. Which of the following is the PRIMARY purpose of establishing baseline metrics?",
        "options": [
            "A. To identify normal network behavior",
            "B. To capture and analyze individual packets",
            "C. To aggregate logs from multiple devices",
            "D. To integrate with third-party APIs"
        ],
        "answer": "A. To identify normal network behavior"
    },
    {
        "question": "A company is using a SIEM system to monitor security events. Which of the following is the PRIMARY purpose of log aggregation in this context?",
        "options": [
            "A. To capture individual packets",
            "B. To centralize and analyze logs from multiple sources",
            "C. To establish baseline metrics",
            "D. To integrate with third-party APIs"
        ],
        "answer": "B. To centralize and analyze logs from multiple sources"
    },
    {
        "question": "A network administrator is configuring a Syslog collector to centralize logs from network devices. Which of the following is the PRIMARY benefit of using a Syslog collector?",
        "options": [
            "A. To capture flow data",
            "B. To aggregate logs for easier analysis",
            "C. To establish baseline metrics",
            "D. To integrate with third-party APIs"
        ],
        "answer": "B. To aggregate logs for easier analysis"
    },
    {
        "question": "A company is using a SIEM system to monitor security events. Which of the following is the PRIMARY purpose of anomaly alerting in this context?",
        "options": [
            "A. To capture individual packets",
            "B. To notify administrators of unusual activity",
            "C. To establish baseline metrics",
            "D. To integrate with third-party APIs"
        ],
        "answer": "B. To notify administrators of unusual activity"
    },
    {
        "question": "A network administrator is integrating a monitoring tool with a third-party API to automate tasks. Which of the following is the PRIMARY benefit of API integration in this context?",
        "options": [
            "A. To capture flow data",
            "B. To centralize logs from multiple devices",
            "C. To enable automation and interoperability",
            "D. To establish baseline metrics"
        ],
        "answer": "C. To enable automation and interoperability"
    },
    {
        "question": "A company is using NetFlow to monitor network traffic. Which of the following is the PRIMARY purpose of flow data in this context?",
        "options": [
            "A. To capture individual packets",
            "B. To analyze traffic patterns and identify bottlenecks",
            "C. To centralize logs from multiple devices",
            "D. To establish baseline metrics"
        ],
        "answer": "B. To analyze traffic patterns and identify bottlenecks"
    },
    {
        "question": "A network administrator is troubleshooting a security incident and needs to analyze logs from multiple devices. Which of the following tools would be MOST appropriate for this task?",
        "options": [
            "A. NetFlow",
            "B. Wireshark",
            "C. SIEM",
            "D. Syslog collector"
        ],
        "answer": "C. SIEM"
    },
    {
        "question": "A company is using a monitoring tool to detect unusual network activity. Which of the following is the PRIMARY purpose of anomaly alerting in this context?",
        "options": [
            "A. To capture individual packets",
            "B. To notify administrators of unusual activity",
            "C. To establish baseline metrics",
            "D. To integrate with third-party APIs"
        ],
        "answer": "B. To notify administrators of unusual activity"
    },
    {
        "question": "A network administrator is configuring a monitoring tool to integrate with a third-party API. Which of the following is the PRIMARY benefit of API integration in this context?",
        "options": [
            "A. To capture flow data",
            "B. To centralize logs from multiple devices",
            "C. To enable automation and interoperability",
            "D. To establish baseline metrics"
        ],
        "answer": "C. To enable automation and interoperability"
    },
    {
        "question": "A company is using Wireshark to troubleshoot a network issue. Which of the following is the PRIMARY purpose of packet capture in this context?",
        "options": [
            "A. To analyze traffic patterns",
            "B. To capture and inspect individual packets",
            "C. To centralize logs from multiple devices",
            "D. To establish baseline metrics"
        ],
        "answer": "B. To capture and inspect individual packets"
    },
    {
        "question": "A network administrator is setting up a Syslog collector to centralize logs from network devices. Which of the following is the PRIMARY benefit of using a Syslog collector?",
        "options": [
            "A. To capture flow data",
            "B. To aggregate logs for easier analysis",
            "C. To establish baseline metrics",
            "D. To integrate with third-party APIs"
        ],
        "answer": "B. To aggregate logs for easier analysis"
    },
    {
        "question": "A company is using a SIEM system to monitor security events. Which of the following is the PRIMARY purpose of log aggregation in this context?",
        "options": [
            "A. To capture individual packets",
            "B. To centralize and analyze logs from multiple sources",
            "C. To establish baseline metrics",
            "D. To integrate with third-party APIs"
        ],
        "answer": "B. To centralize and analyze logs from multiple sources"
    },
    {
        "question": "A network administrator is troubleshooting a network performance issue and needs to analyze traffic patterns. Which of the following tools would provide flow data to help identify the source of the issue?",
        "options": [
            "A. SNMP",
            "B. NetFlow",
            "C. Syslog",
            "D. SIEM"
        ],
        "answer": "B. NetFlow"
    },
    {
        "question": "A company is experiencing intermittent network outages, and the network administrator needs to capture and analyze individual packets to diagnose the issue. Which of the following tools should the administrator use?",
        "options": [
            "A. NetFlow",
            "B. Wireshark",
            "C. Syslog",
            "D. SIEM"
        ],
        "answer": "B. Wireshark"
    },
    {
        "question": "A network administrator is setting up a monitoring system to detect unusual network activity. Which of the following is the PRIMARY purpose of establishing baseline metrics?",
        "options": [
            "A. To identify normal network behavior",
            "B. To capture and analyze individual packets",
            "C. To aggregate logs from multiple devices",
            "D. To integrate with third-party APIs"
        ],
        "answer": "A. To identify normal network behavior"
    },
    {
        "question": "A company is using a SIEM system to monitor security events. Which of the following is the PRIMARY purpose of log aggregation in this context?",
        "options": [
            "A. To capture individual packets",
            "B. To centralize and analyze logs from multiple sources",
            "C. To establish baseline metrics",
            "D. To integrate with third-party APIs"
        ],
        "answer": "B. To centralize and analyze logs from multiple sources"
    },
    {
        "question": "A network administrator is configuring a Syslog collector to centralize logs from network devices. Which of the following is the PRIMARY benefit of using a Syslog collector?",
        "options": [
            "A. To capture flow data",
            "B. To aggregate logs for easier analysis",
            "C. To establish baseline metrics",
            "D. To integrate with third-party APIs"
        ],
        "answer": "B. To aggregate logs for easier analysis"
    },
    {
        "question": "A company is using a SIEM system to monitor security events. Which of the following is the PRIMARY purpose of anomaly alerting in this context?",
        "options": [
            "A. To capture individual packets",
            "B. To notify administrators of unusual activity",
            "C. To establish baseline metrics",
            "D. To integrate with third-party APIs"
        ],
        "answer": "B. To notify administrators of unusual activity"
    },
    {
        "question": "A network administrator is configuring SNMP to monitor network devices. Which of the following is the PRIMARY purpose of SNMP traps?",
        "options": [
            "A. To poll devices for performance data",
            "B. To send alerts to the SNMP manager when an event occurs",
            "C. To configure devices remotely",
            "D. To store historical performance data"
        ],
        "answer": "B. To send alerts to the SNMP manager when an event occurs"
    },
    {
        "question": "A company is using SNMPv2c to monitor its network devices. Which of the following is a key security concern with SNMPv2c?",
        "options": [
            "A. Lack of encryption for community strings",
            "B. Inability to send traps",
            "C. Limited support for MIBs",
            "D. High CPU usage on devices"
        ],
        "answer": "A. Lack of encryption for community strings"
    },
    {
        "question": "A network administrator is configuring SNMPv3 on a router. Which of the following features is supported in SNMPv3 but not in SNMPv2c?",
        "options": [
            "A. Community strings",
            "B. Authentication and encryption",
            "C. Traps",
            "D. MIBs"
        ],
        "answer": "B. Authentication and encryption"
    },
    {
        "question": "A network administrator is troubleshooting an SNMP monitoring issue and notices that the SNMP manager is not receiving traps from a device. Which of the following is the MOST likely cause?",
        "options": [
            "A. The device does not support SNMP",
            "B. The SNMP manager is not configured to listen for traps",
            "C. The MIB is outdated",
            "D. The community string is incorrect"
        ],
        "answer": "B. The SNMP manager is not configured to listen for traps"
    },
    {
        "question": "A company is using SNMP to monitor network performance. Which of the following is the PRIMARY purpose of a Management Information Base (MIB)?",
        "options": [
            "A. To define the structure of data used by SNMP",
            "B. To encrypt SNMP traffic",
            "C. To authenticate SNMP requests",
            "D. To store historical performance data"
        ],
        "answer": "A. To define the structure of data used by SNMP"
    },
    {
        "question": "A network administrator is configuring SNMPv3 on a switch. Which of the following is required to ensure secure communication?",
        "options": [
            "A. Community strings",
            "B. Authentication and encryption settings",
            "C. MIB files",
            "D. SNMP traps"
        ],
        "answer": "B. Authentication and encryption settings"
    },
    {
        "question": "A network administrator is troubleshooting an SNMP issue and notices that the SNMP manager is unable to poll data from a device. Which of the following is the MOST likely cause?",
        "options": [
            "A. The device does not support SNMP",
            "B. The SNMP manager is not configured to send traps",
            "C. The community string is incorrect",
            "D. The MIB is outdated"
        ],
        "answer": "C. The community string is incorrect"
    },
    {
        "question": "A company is upgrading its SNMP monitoring from SNMPv2c to SNMPv3. Which of the following is the PRIMARY benefit of this upgrade?",
        "options": [
            "A. Improved performance",
            "B. Enhanced security with authentication and encryption",
            "C. Support for additional MIBs",
            "D. Reduced CPU usage on devices"
        ],
        "answer": "B. Enhanced security with authentication and encryption"
    },
    {
        "question": "A network administrator is configuring SNMP on a router and needs to ensure that only authorized devices can access SNMP data. Which of the following should the administrator configure?",
        "options": [
            "A. Community strings",
            "B. MIB files",
            "C. SNMP traps",
            "D. Authentication and encryption settings"
        ],
        "answer": "D. Authentication and encryption settings"
    },
    {
        "question": "A network administrator is troubleshooting an SNMP issue and notices that the SNMP manager is not receiving performance data from a device. Which of the following is the MOST likely cause?",
        "options": [
            "A. The device does not support SNMP",
            "B. The SNMP manager is not configured to poll data",
            "C. The MIB is outdated",
            "D. The community string is incorrect"
        ],
        "answer": "D. The community string is incorrect"
    },
    {
        "question": "A company is using SNMP to monitor network devices. Which of the following is the PRIMARY purpose of SNMP polling?",
        "options": [
            "A. To send alerts to the SNMP manager when an event occurs",
            "B. To collect performance data from devices at regular intervals",
            "C. To configure devices remotely",
            "D. To store historical performance data"
        ],
        "answer": "B. To collect performance data from devices at regular intervals"
    },
    {
        "question": "A network administrator is configuring SNMPv3 on a firewall. Which of the following is a key advantage of SNMPv3 over SNMPv2c?",
        "options": [
            "A. Support for community strings",
            "B. Enhanced security with authentication and encryption",
            "C. Reduced CPU usage on devices",
            "D. Support for additional MIBs"
        ],
        "answer": "B. Enhanced security with authentication and encryption"
    },
    {
        "question": "A network administrator is troubleshooting an SNMP issue and notices that the SNMP manager is not receiving traps from a device. Which of the following is the MOST likely cause?",
        "options": [
            "A. The device does not support SNMP",
            "B. The SNMP manager is not configured to listen for traps",
            "C. The MIB is outdated",
            "D. The community string is incorrect"
        ],
        "answer": "B. The SNMP manager is not configured to listen for traps"
    },
    {
        "question": "A company is using SNMP to monitor network performance. Which of the following is the PRIMARY purpose of a Management Information Base (MIB)?",
        "options": [
            "A. To define the structure of data used by SNMP",
            "B. To encrypt SNMP traffic",
            "C. To authenticate SNMP requests",
            "D. To store historical performance data"
        ],
        "answer": "A. To define the structure of data used by SNMP"
    },
    {
        "question": "A network administrator is configuring SNMPv3 on a switch. Which of the following is required to ensure secure communication?",
        "options": [
            "A. Community strings",
            "B. Authentication and encryption settings",
            "C. MIB files",
            "D. SNMP traps"
        ],
        "answer": "B. Authentication and encryption settings"
    },
    {
        "question": "A network administrator is troubleshooting an SNMP issue and notices that the SNMP manager is unable to poll data from a device. Which of the following is the MOST likely cause?",
        "options": [
            "A. The device does not support SNMP",
            "B. The SNMP manager is not configured to send traps",
            "C. The community string is incorrect",
            "D. The MIB is outdated"
        ],
        "answer": "C. The community string is incorrect"
    },
    {
        "question": "A company is upgrading its SNMP monitoring from SNMPv2c to SNMPv3. Which of the following is the PRIMARY benefit of this upgrade?",
        "options": [
            "A. Improved performance",
            "B. Enhanced security with authentication and encryption",
            "C. Support for additional MIBs",
            "D. Reduced CPU usage on devices"
        ],
        "answer": "B. Enhanced security with authentication and encryption"
    },
    {
        "question": "A network administrator is configuring SNMP on a router and needs to ensure that only authorized devices can access SNMP data. Which of the following should the administrator configure?",
        "options": [
            "A. Community strings",
            "B. MIB files",
            "C. SNMP traps",
            "D. Authentication and encryption settings"
        ],
        "answer": "D. Authentication and encryption settings"
    },
    {
        "question": "A network administrator is troubleshooting an SNMP issue and notices that the SNMP manager is not receiving performance data from a device. Which of the following is the MOST likely cause?",
        "options": [
            "A. The device does not support SNMP",
            "B. The SNMP manager is not configured to poll data",
            "C. The MIB is outdated",
            "D. The community string is incorrect"
        ],
        "answer": "D. The community string is incorrect"
    },
    {
        "question": "A company is using SNMP to monitor network devices. Which of the following is the PRIMARY purpose of SNMP polling?",
        "options": [
            "A. To send alerts to the SNMP manager when an event occurs",
            "B. To collect performance data from devices at regular intervals",
            "C. To configure devices remotely",
            "D. To store historical performance data"
        ],
        "answer": "B. To collect performance data from devices at regular intervals"
    }
]
@bot.callback_query_handler(func=lambda call: call.data == "restart_quiz")
def restart_quiz(call):
    user_id = call.message.chat.id
    try:
        # Shuffle the question sequence
        question_sequence = list(range(len(questions)))
        random.shuffle(question_sequence)  # Shuffle the order of questions

        # Reset progress with the new shuffled sequence
        user_progress[user_id] = {
            'question_index': 0,
            'completed_questions': set(),
            'correct_answers': 0,
            'question_sequence': question_sequence,  # Use the shuffled sequence
            'selected_answers': {}
        }
        # Pass both user_id and progress to save_progress
        save_progress(user_id, user_names.get(user_id, "Unknown"), user_progress[user_id])
        send_next_question(call.message)  # Send the first question again
    except Exception as e:
        logging.error(f"Error in restart_quiz for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while restarting the quiz. Please try again.")

@bot.callback_query_handler(func=lambda call: call.data == "revisit_incorrect")
def revisit_incorrect(call):
    user_id = call.message.chat.id
    try:
        progress = user_progress.get(user_id, {})
        
        if not progress or not progress['selected_answers']:
            bot.send_message(user_id, "You haven't answered any questions incorrectly.")
            return
        
        # Identify incorrect questions
        incorrect_questions = [
            int(q) for q, ans in progress['selected_answers'].items()
            if ans != questions[int(q)]['answer'][0]
        ]
        
        if not incorrect_questions:
            bot.send_message(user_id, "Great job! You got all questions correct.")
            return
        
        # Shuffle the incorrect questions
        random.shuffle(incorrect_questions)  # Shuffle the order of incorrect questions

        # Save the updated progress
        save_progress(user_id, user_names.get(user_id, "Unknown"), progress)
        
        # Start the quiz with the incorrect questions
        send_next_question(call.message)
    except Exception as e:
        logging.error(f"Error in revisit_incorrect for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while revisiting incorrect questions. Please try again.")

# Command to reset the quiz progress
@bot.message_handler(commands=['reset'])
def reset_progress(message):
    user_id = message.chat.id
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM progress WHERE user_id = ?', (user_id,))
            conn.commit()

        user_progress.pop(user_id, None)  # Remove progress from memory if cached
        bot.send_message(user_id, "Your quiz progress has been reset. You can start fresh using /start.")
    except sqlite3.Error as e:
        logging.error(f"Database error in reset_progress for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while resetting your progress. Please try again.")
    except Exception as e:
        logging.error(f"Unexpected error in reset_progress for user {user_id}: {e}")
        bot.send_message(user_id, "An unexpected error occurred. Please try again.")

@bot.message_handler(commands=['start', 'resume'])
def start_quiz(message):
    user_id = message.chat.id
    try:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("Start Quiz", callback_data="start_quiz"),
            InlineKeyboardButton("TOP USERS", callback_data="view_scores")
        )
        start_message = (
            "🎉 Welcome to the Network+ N10-009 Quiz Bot! 🎉\n\n"
            "This Practice Quiz focuses on sections 1.0 Network N10-009 Objectives. "
            "Test your knowledge, challenge yourself, and see if you can make it to the TOP USERS leaderboard! 🏆\n\n"
            "Are you ready to prove your networking skills? Let's get started! 💪"
        )
        bot.send_message(user_id, start_message, reply_markup=markup)

        progress = user_progress.get(user_id)
        
        if progress is None:
            # Shuffle the question sequence for new users
            question_sequence = list(range(len(questions)))
            random.shuffle(question_sequence)  # Shuffle the order of questions

            progress = {
                'question_index': 0,
                'completed_questions': set(),
                'correct_answers': 0,
                'question_sequence': question_sequence,  # Use the shuffled sequence
                'selected_answers': {}
            }
            logging.info(f"New user started: {user_id}")
        else:
            logging.info(f"Loaded progress for user {user_id}: {progress}")

        user_progress[user_id] = progress
        save_progress(user_id, user_names.get(user_id, "Unknown"), progress)  # Save the initialized progress
        send_next_question(message)
    except Exception as e:
        logging.error(f"Error in start_quiz for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while starting the quiz. Please try again.")

def send_next_question(message, edit=False, go_back=False):
    user_id = message.chat.id
    try:
        progress = user_progress[user_id]

        if go_back:
            # Navigate to the previous question
            if progress['question_index'] > 0:
                progress['question_index'] -= 1  # Move to the previous question
            else:
                # If already at the first question, do nothing
                bot.answer_callback_query(message.id, "You're already at the first question.")
                return
            question_index = progress['question_sequence'][progress['question_index']]  # Get the actual question index from the shuffled sequence
        else:
            # Use the question_sequence to determine which questions to show
            remaining_questions = [
                q for q in progress['question_sequence']
                if q not in progress['completed_questions']
            ]

            if not remaining_questions:
                # If all questions in the sequence are answered, show completion message
                total_questions = len(progress['question_sequence'])
                answered_questions = len(progress['completed_questions'])
                percentage_correct = (progress['correct_answers'] / total_questions) * 100 if total_questions else 0

                final_message = (
                    f"<code>{answered_questions} of {total_questions}</code>\n"
                    f"<code>Correct Answers: {progress['correct_answers']} [{percentage_correct:.0f}%]</code>\n\n"
                    "You've answered all the questions! Great job! ✅"
                )

                # Add inline buttons below the message
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(
                    InlineKeyboardButton("Start Quiz Again", callback_data="restart_quiz"),
                    InlineKeyboardButton("Revisit Incorrect Questions", callback_data="revisit_incorrect")
                )

                bot.send_message(user_id, final_message, parse_mode="HTML", reply_markup=markup)
                return

            # Set the next question index
            question_index = remaining_questions[0]
            progress['question_index'] = progress['question_sequence'].index(question_index)  # Update question_index to the position in the shuffled sequence

        # Update the question_index in progress
        question_data = questions[question_index]

        # Calculate progress based on the question_sequence
        total_questions = len(progress['question_sequence'])
        answered_questions = len(progress['completed_questions'])
        correct_answers = progress['correct_answers']
        percentage_complete = (answered_questions / total_questions) * 100
        percentage_correct = (correct_answers / total_questions) * 100 if total_questions else 0

        # Calculate the user's rank
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) + 1 
                FROM progress 
                WHERE correct_answers > ? AND username IS NOT NULL AND username != ''
            """, (correct_answers,))
            rank = cursor.fetchone()[0]

        # Prepare question text with rank
        question_text = (
            f"<blockquote><b><code>🌐 RANK: {rank}</code></b>\n"
            f"<code>⏳ {answered_questions} of {total_questions}</code>\n"
            f"<code>✅ Correct Answers: {correct_answers} [{percentage_correct:.0f}%]</code></blockquote>\n\n"
            f"<blockquote><b>{question_data['question']}</b></blockquote>\n\n"
)

        

        # Add options to the question text
        for option in question_data['options']:
            question_text += f"{option}\n"

        # Create inline keyboard with A, B, C, D buttons, Previous button, and Next button (if applicable)
        markup = InlineKeyboardMarkup(row_width=2)
        for option in question_data['options']:
            # Extract the letter (A, B, C, or D) from the option
            option_letter = option[0]  # The first character is the letter (e.g., "A")
            callback_data = f"{question_index}_{option_letter}"  # Use the letter in the callback data

            # If the question has been answered, show the selected answer with a tick or cross
            if str(question_index) in progress['selected_answers']:
                selected_answer = progress['selected_answers'][str(question_index)]
                if option_letter == selected_answer:
                    if selected_answer == question_data['answer'][0]:  # Compare with the correct answer
                        option_letter += " ✅"  # Add a checkmark for correct answers
                    else:
                        option_letter += " ❌"  # Add a cross for incorrect answers
                elif option_letter == question_data['answer'][0]:
                    option_letter += " ✅"  # Show the correct answer with a checkmark
                callback_data = "disabled"  # Disable the button after answering

            # Add the button with the letter (A, B, C, or D) as the text
            markup.add(InlineKeyboardButton(option_letter, callback_data=callback_data))

        # Add Previous and Next buttons (only show Next button if the question has been answered)
        if progress['question_index'] > 0:
            markup.add(InlineKeyboardButton("Previous Question", callback_data="previous_question"))
        if str(question_index) in progress['selected_answers']:
            markup.add(InlineKeyboardButton("Next Question", callback_data="next_question"))

        if edit:
            try:
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    text=question_text,
                    parse_mode="HTML",
                    reply_markup=markup
                )
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" not in str(e):
                    raise e
        else:
            bot.send_message(user_id, question_text, parse_mode="HTML", reply_markup=markup)

        save_progress(user_id, user_names.get(user_id, "Unknown"), progress)
    except Exception as e:
        logging.error(f"Error in send_next_question for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while loading the next question. Please try again.")

@bot.callback_query_handler(func=lambda call: True)
def handle_answer(call):
    user_id = call.message.chat.id
    try:
        progress = user_progress.get(user_id)

        if not progress:
            bot.answer_callback_query(call.id, "Please start the quiz using /start or /resume.")
            return

        if call.data == "previous_question":
            send_next_question(call.message, edit=True, go_back=True)
            return

        if call.data == "next_question":
            send_next_question(call.message, edit=True)
            return

        if call.data == "disabled":
            bot.answer_callback_query(call.id, "You've already answered this question.")
            return

        question_index, selected_option = call.data.split("_")
        question_index = int(question_index)
        question_data = questions[question_index]

        # Update progress and feedback
        if question_index not in progress['completed_questions']:
            progress['completed_questions'].add(question_index)  # Mark question as completed

        progress['selected_answers'][str(question_index)] = selected_option

        # Prepare the updated inline keyboard with feedback
        markup = InlineKeyboardMarkup(row_width=1)
        for option in question_data['options']:
            display_text = option[:25] + "..." if len(option) > 44 else option  # Shorten long options

            if option.startswith(selected_option):
                if selected_option == question_data['answer'][0]:
                    display_text += " ✅"
                    progress['correct_answers'] += 1  # Increment correct answers
                else:
                    display_text += " ❌"
            elif option.startswith(question_data['answer'][0]):
                display_text += " ✅"

            markup.add(InlineKeyboardButton(display_text, callback_data="disabled"))

        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )

        if selected_option == question_data['answer'][0]:
            bot.answer_callback_query(call.id, "Correct! ✅")
            send_next_question(call.message, edit=True)
        else:
            bot.answer_callback_query(call.id, "Incorrect ❌")
            time.sleep(4)  # Introduce a 4-second delay before the next question
            send_next_question(call.message, edit=True)
    except Exception as e:
        logging.error(f"Error in handle_answer for user {user_id}: {e}")
        bot.send_message(user_id, "An error occurred while processing your answer. Please try again.")

# Initialize database
init_db()

# Start the bot
bot.polling()

