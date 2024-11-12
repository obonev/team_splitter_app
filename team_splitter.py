from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import random
import logging

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure secret key

# Set up logging
logging.basicConfig(level=logging.DEBUG)

games = {}  # Dictionary to store game details

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/create', methods=['POST'])
def create_game():
    game_id = str(random.randint(1000, 9999))
    session['game_id'] = game_id
    session['is_creator'] = True
    games[game_id] = {
        "creator": session['is_creator'],
        "participants": [],
        "team_size": 3,
        "teams": [],
        "submitted_names": set()
    }
    logging.info(f"Created new game with ID: {game_id}")
    return redirect(url_for('team_size'))

@app.route('/team_size')
def team_size():
    if not session.get('is_creator'):
        return redirect(url_for('welcome'))
    return render_template('team_size.html')

@app.route('/set_team_size', methods=['POST'])
def set_team_size():
    team_size = int(request.form.get('team_size'))
    game_id = session.get('game_id')
    if game_id in games:
        games[game_id]['team_size'] = team_size
        logging.info(f"Set team size to {team_size} for game {game_id}")
        return redirect(url_for('game', game_id=game_id))
    return redirect(url_for('welcome'))

@app.route('/join', methods=['POST'])
def join_game():
    game_id = request.form.get('game_id')
    if game_id in games:
        session['game_id'] = game_id
        session['is_creator'] = False
        logging.info(f"User joined game {game_id}")
        return redirect(url_for('game', game_id=game_id))
    logging.warning(f"Attempted to join invalid game ID: {game_id}")
    return render_template('welcome.html', error="Invalid game ID")

@app.route('/game/<game_id>')
def game(game_id):
    is_creator = session.get('is_creator', False)
    user_id = session.get('user_id')
    
    if game_id not in games:
        logging.warning(f"Attempted to access invalid game ID: {game_id}")
        return redirect(url_for('welcome'))
    
    # Store game_id in session when accessing the game page
    session['game_id'] = game_id
    
    has_submitted = user_id in games[game_id]['submitted_names'] if game_id in games else False
    return render_template('game.html', game_id=game_id, is_creator=is_creator, has_submitted=has_submitted)

@app.route('/add', methods=['POST'])
def add_name():
    # Log request form data to check what is received
    logging.info(f"request.form data: {request.form}")

    name = request.form.get('name')
    game_id = session.get('game_id')
    user_id = session.get('user_id')

    logging.info(f"Attempting to add name: {name} for game_id: {game_id}, user_id: {user_id}")

    if not game_id:
        logging.error("No game_id in session")
        return jsonify({"error": "No active game session"}), 400

    if game_id not in games:
        logging.error(f"Invalid game ID: {game_id}")
        return jsonify({"error": "Invalid game ID"}), 400

    if not name or not name.strip():
        logging.error("No name provided in request")
        return jsonify({"error": "Name is required"}), 400

    if not user_id:
        user_id = str(random.randint(10000, 99999))
        session['user_id'] = user_id
        logging.info(f"Generated new user_id: {user_id}")

    if user_id in games[game_id]['submitted_names']:
        logging.warning(f"User {user_id} attempted to submit multiple names")
        return jsonify({"error": "You have already submitted a name"}), 400

    games[game_id]['participants'].append(name.strip())
    games[game_id]['submitted_names'].add(user_id)
    session['participant_name'] = name.strip()
    logging.info(f"Successfully added {name} to game {game_id}")
    return jsonify({"message": f"{name} added successfully!"}), 200

@app.route('/sort', methods=['GET'])
def sort_teams():
    game_id = session.get('game_id')
    if not game_id in games:
        return jsonify({"error": "Invalid game ID"}), 400

    team_size = games[game_id]['team_size']
    participants = games[game_id]['participants'].copy()
    random.shuffle(participants)
    teams = [participants[i:i + team_size] for i in range(0, len(participants), team_size)]
    games[game_id]['teams'] = teams
    logging.info(f"Sorted teams for game {game_id}")
    return jsonify({"teams": teams}), 200

@app.route('/get_teams')
def get_teams():
    game_id = session.get('game_id')
    if not game_id in games:
        return jsonify({"teams": []}), 400

    teams = games[game_id].get('teams', [])
    is_creator = session.get('is_creator', False)
    participant_name = session.get('participant_name', '')

    if is_creator:
        return jsonify({"teams": teams})
    else:
        # For participants, find their team
        for team_index, team in enumerate(teams):
            if participant_name in team:
                return jsonify({"teams": [team], "team_number": team_index + 1})
        return jsonify({"teams": []})

if __name__ == '__main__':
    app.run(debug=True)
