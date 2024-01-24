from flask import Flask, request, render_template, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, send
import random
import string

app = Flask(__name__)
app.config["SECRET_KEY"] = "thisisforfun"
socketio = SocketIO(app)

# a mock db to persist data

rooms = {}

# build the routes: a route is a function that defines how the server
# server responds to a request from a client which is usually associated
# with a URL path. a route can return a response to the client, such
# as an HTML page, a JSON object, or a status code.

""" in this app having two routes
/ - home
/room - where the chat room is served where users can send and recieve messages
        from other users present in the same room.
"""

def generate_room_code(length, existing_codes):
    while True:
        code_chars = [random.choice(string.ascii_letters) for _ in range(length)]
        code = ''.join(code_chars)
        if code not in existing_codes:
            return code

@app.route('/', methods=['GET','POST'])
def home():
    session.clear()
    if request.method == 'POST':
        name = request.form.get('name')
        create = request.form.get('create', False)
        code = request.form.get('code')
        join = request.form.get('join', False)
        print(join,code)
        if not name:
            return render_template("home.html", error="Enter User Name", code=code)
        if create != False:
            room_code = generate_room_code(6, list(rooms.keys()))
            new_room = {
                'members': 0,
                'messages': []
            }
            rooms[room_code] = new_room
        if join != False:
            if not code:
                return render_template('home.html', error="enter room code", name=name)
            if code not in rooms:
                return render_template('home.html', error="enter correct room code", name=name)
            room_code = code
        session['room'] = room_code
        session['name'] = name
        return redirect(url_for('room'))
    else:
        return render_template('home.html')

@app.route('/room')
def room():
    room = session.get('room')
    name = session.get('name')
    if name is None or room is None or room not in rooms:
        return redirect(url_for('home'))
    messages = rooms[room]['messages']
    return render_template('room.html', room=room, user=name, messages=messages)

# build socketio event handlers
'''
    we have three SocketIO events to handle:
        connect - when a client connects to the server
        message - when either the client or server sends a message to each other
        disconnect - when the user leaves the room
'''
'''
    When the server receives a connect event from the client side,
    this function will be called. It uses the room id and user name
    passed by the client to let the user join the chat room, then
    redirects the user to the chat room page with the message
    "<user> has entered the chat".
'''

@socketio.on('connect')
def handle_connect():
    name = session.get('name')
    room = session.get('room')
    if name is None or room is None:
        return
    if room not in rooms:
        leave_room(room)
    join_room(room)
    send({
        "sender":"",
        "message":f"{name} joined"
    }, to=room)
    rooms[room]['members'] += 1

'''
    Next, we need to handle the message event. The server will receive
    a message event from the client when the user sends a chat message.

    This event handler expects a data payload where it retrieves the
    user’s message. It will then send the message to the chat room for
    everyone to see and save it in the mock database rooms.
'''
@socketio.on('message')
def handle_message(payload):
    room = session.get('room')
    name = session.get('name')
    if room not in rooms:
        return
    message = {
        "sender":name,
        "message":payload["message"]
    }
    send(message, to=room)
    rooms[room]['messages'].append(message)
'''typing status ..'''
# @socketio.on('typing')
# def handle_typing(payload):
#     room = session.get('room')
#     name = session.get('name')
#     if room not in rooms:
#         return
#     # message = {
#     #     "sender":name,
#     #     "message":payload["message"]
#     # }
#     send(name, to=room)
    # rooms[room]['messages'].append(message)

'''
    we need to handle the disconnect event, or when a user leaves a chat room.

    This event handler just removes the user from the chat room and lets 
    everyone knows the user has left by sending a message event to the 
    chat room. When there’s no one left in a chat room, it will be deleted 
    from the mock database.
'''
@socketio.on('disconnect')
def handle_disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)
    if room in rooms:
        rooms[room]['members'] -= 1
        if rooms[room]['members'] <= 0:
            del rooms[room]
        send({
            "message":f"{name} left",
            "sender":""
        }, to=room)


if __name__ == "__main__" :
    socketio.run(app, debug=True, host="0.0.0.0")