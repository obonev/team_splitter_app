from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'

games = {}  # Dictionary to store game details (game_id: {creator, participants, team_size})

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/create', methods=['POST'])
def create_game():
    game_id = str(random.randint(1000, 9999))
    session['game_id'] = game_id
    session['is_creator'] = True
    games[game_id] = {"creator": session['is_creator'], "participants": [], "team_size": 3}  # Default team size
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
    games[game_id]['team_size'] = team_size
    return redirect(url_for('game', game_id=game_id))

@app.route('/join', methods=['POST'])
def join_game():
    game_id = request.form.get('game_id')
    if game_id in games:
        session['game_id'] = game_id
        session['is_creator'] = False
        return redirect(url_for('game', game_id=game_id))
    return redirect(url_for('welcome'))

@app.route('/game/<game_id>')
def game(game_id):
    is_creator = session.get('is_creator')
    return render_template('game.html', game_id=game_id, is_creator=is_creator)

@app.route('/add', methods=['POST'])
def add_name():
    name = request.form.get('name')
    game_id = session.get('game_id')
    if name and game_id in games:
        games[game_id]['participants'].append(name)
        return jsonify({"message": f"{name} added!"}), 200
    return jsonify({"error": "Unable to add participant"}), 400

@app.route('/sort', methods=['GET'])
def sort_teams():
    game_id = session.get('game_id')
    team_size = games[game_id]['team_size']
    participants = games[game_id]['participants']
    random.shuffle(participants)
    teams = [participants[i:i + team_size] for i in range(0, len(participants), team_size)]
    games[game_id]['teams'] = teams
    return jsonify({"teams": teams}), 200

@app.route('/get_teams')
def get_teams():
    game_id = session.get('game_id')
    teams = games[game_id].get('teams', [])
    return jsonify({"teams": teams})