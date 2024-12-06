from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import random
import logging
import traceback
import os
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure secret key

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

games = {}  # Dictionary to store game details

def generate_user_id(game_id):
    """Generate a unique user ID for the game"""
    attempts = 0
    while attempts < 10:
        user_id = f"{game_id}-{random.randint(1000, 9999)}"
        # Check if this user_id exists in the specific game
        if game_id in games:
            if user_id not in games[game_id]['user_names']:
                return user_id
        else:
            return user_id
        attempts += 1
    
    # Fallback with microsecond precision if needed
    return f"{game_id}-{random.randint(10000, 99999)}-{int(time.time() * 1000) % 10000}"

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/create', methods=['POST'])
def create_game():
    try:
        game_id = str(random.randint(1000, 9999))
        user_id = generate_user_id(game_id)
        
        session.clear()
        session['game_id'] = game_id
        session['user_id'] = user_id
        session['is_creator'] = True
        
        games[game_id] = {
            "creator": user_id,
            "participants": [],
            "team_size": 3,
            "teams": [],
            "submitted_names": set(),
            "user_names": {}
        }
        
        logger.info(f"Game created - Game ID: {game_id}, Creator User ID: {user_id}")
        return redirect(url_for('team_size'))
    
    except Exception as e:
        logger.error(f"Error in create_game: {str(e)}")
        logger.error(traceback.format_exc())
        return f"An error occurred: {str(e)}", 500

@app.route('/team_size')
def team_size():
    if not session.get('is_creator'):
        return redirect(url_for('welcome'))
    return render_template('team_size.html')

@app.route('/set_team_size', methods=['POST'])
def set_team_size():
    try:
        team_size = int(request.form.get('team_size'))
        game_id = session.get('game_id')
        
        if game_id in games:
            games[game_id]['team_size'] = team_size
            return redirect(url_for('game', game_id=game_id))
        return redirect(url_for('welcome'))
    
    except Exception as e:
        logger.error(f"Error in set_team_size: {str(e)}")
        logger.error(traceback.format_exc())
        return f"An error occurred: {str(e)}", 500

@app.route('/join', methods=['POST'])
def join_game():
    try:
        game_id = request.form.get('game_id')
        if game_id in games:
            user_id = generate_user_id(game_id)
            
            session.clear()
            session['game_id'] = game_id
            session['user_id'] = user_id
            session['is_creator'] = False
            
            return redirect(url_for('game', game_id=game_id))
        return render_template('welcome.html', error="Invalid game ID")
    
    except Exception as e:
        logger.error(f"Error in join_game: {str(e)}")
        logger.error(traceback.format_exc())
        return f"An error occurred: {str(e)}", 500

@app.route('/game/<game_id>')
def game(game_id):
    try:
        is_creator = session.get('is_creator', False)
        user_id = session.get('user_id')
        
        if game_id not in games:
            return redirect(url_for('welcome'))
        
        session['game_id'] = game_id
        has_submitted = user_id in games[game_id]['submitted_names']
        return render_template('game.html', game_id=game_id, is_creator=is_creator, has_submitted=has_submitted)
    
    except Exception as e:
        logger.error(f"Error in game route: {str(e)}")
        logger.error(traceback.format_exc())
        return f"An error occurred: {str(e)}", 500

@app.route('/add', methods=['POST'])
def add_name():
    try:
        name = request.form.get('name')
        game_id = session.get('game_id')
        user_id = session.get('user_id')

        if not game_id or game_id not in games:
            return jsonify({"error": "Invalid game session"}), 400

        if not user_id:
            return jsonify({"error": "Invalid user session"}), 400

        if not name or not name.strip():
            return jsonify({"error": "Name is required"}), 400

        if user_id in games[game_id]['submitted_names']:
            return jsonify({"error": "You have already submitted your name"}), 400

        games[game_id]['submitted_names'].add(user_id)
        games[game_id]['participants'].append(name.strip())
        games[game_id]['user_names'][user_id] = name.strip()

        return jsonify({"message": "Participant added successfully"})
    
    except Exception as e:
        logger.error(f"Error in add_name: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/get_teams', methods=['GET'])
def get_teams():
    try:
        game_id = session.get('game_id')
        user_id = session.get('user_id')

        if not game_id or game_id not in games:
            return jsonify({"error": "Invalid game ID"}), 400

        if not games[game_id]['teams']:
            return jsonify({"teams": []})

        if user_id and not session.get('is_creator'):
            user_name = games[game_id]['user_names'].get(user_id)
            if user_name:
                for idx, team in enumerate(games[game_id]['teams']):
                    if user_name in team:
                        return jsonify({"teams": [team], "team_number": idx + 1})
            return jsonify({"teams": []})
        
        return jsonify({"teams": games[game_id]['teams']})
    
    except Exception as e:
        logger.error(f"Error in get_teams: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/sort', methods=['GET'])
def sort_teams():
    try:
        game_id = session.get('game_id')

        if not game_id or game_id not in games:
            return jsonify({"error": "Invalid game ID"}), 400

        if not session.get('is_creator'):
            return jsonify({"error": "Only the creator can sort teams"}), 403

        participants = games[game_id]['participants']
        team_size = games[game_id]['team_size']

        if len(participants) == 0:
            return jsonify({"error": "No participants to sort"}), 400

        # Shuffle participants to ensure randomness
        random.shuffle(participants)

        # Initialize empty teams
        num_teams = max(1, len(participants) // team_size + (1 if len(participants) % team_size != 0 else 0))
        teams = [[] for _ in range(num_teams)]

        # Distribute participants across teams
        for i, participant in enumerate(participants):
            teams[i % num_teams].append(participant)

        games[game_id]['teams'] = teams

        return jsonify({"teams": games[game_id]['teams']})
    
    except Exception as e:
        logger.error(f"Error in sort_teams: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
