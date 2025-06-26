from chat_bot import BOT
import uuid
from flask import Flask, render_template, request, jsonify, url_for, redirect, flash, send_from_directory
from flask import session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, LoginManager, login_required, current_user, logout_user
import os
from forms import RegistrationForm, LoginForm
from langchain_core.messages import AIMessage,HumanMessage
import uuid
from datetime import datetime, timezone
from models import db, User, Session as ChatSession, Message, Emotion, TherapyResponse
from sqlalchemy import func
import math



app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')

chat_bot = BOT()

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///users.db")
db.init_app(app)

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)




@app.route('/',methods=['POST','GET'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            email = form.email.data
            password = form.password.data
            user = db.session.execute(db.select(User).where(User.email == email)).scalar()
            if not user:
                flash("That email does not exist, please try again.")
                return redirect(url_for('login'))
            elif not check_password_hash(user.password, password):
                flash('Password incorrect, please try again.')
                return redirect(url_for('login'))
            else:
                login_user(user)
                return redirect(url_for('dashboard'))
        else:
            return render_template("LOGIN_.html",form=form, logged_in=current_user.is_authenticated)
    else:
        return render_template("LOGIN_.html",form=form, logged_in=current_user.is_authenticated)



@app.route('/registration',methods=['POST','GET'])
def registration():
    form = RegistrationForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            username = form.username.data
            email = form.email.data
            user = db.session.execute(db.select(User).where(User.email == email)).scalar()
            if user:
                flash("You've already signed up with that email, log in instead!")
                return redirect(url_for('login'))

            password = generate_password_hash(
                password=form.password.data,
                method='pbkdf2:sha256',
                salt_length=10
            )
            new_user = User(
                user_id=str(uuid.uuid4()),
                username=username,
                email=email,
                password=password
            )

            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('dashboard'))
        else:
            return render_template("SIGNUP.html",form=form, logged_in=current_user.is_authenticated)
    else:
        return render_template("SIGNUP.html",form=form, logged_in=current_user.is_authenticated)
    


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('Dashboard.html')



@app.route('/insights')
@login_required
def insights():
    sessions = db.session.query(ChatSession).filter_by(user_id=current_user.get_id()).all()

    session_data = {}
    session_ids_seen = set()
    total_duration = 0
    session_count = 0

    for s in sessions:
        if s.start_time and s.end_time and s.session_id not in session_ids_seen:
            session_ids_seen.add(s.session_id)
            session_count += 1

            duration = (s.end_time - s.start_time).total_seconds() / 60
            total_duration += duration

            date_key = s.start_time.date().strftime("%Y-%m-%d")

            if date_key in session_data:
                session_data[date_key]["count"] += 1
                session_data[date_key]["total_minutes"] += duration
            else:
                session_data[date_key] = {
                    "count": 1,
                    "total_minutes": duration
                }

    avg_duration = math.ceil(total_duration / session_count) if session_count > 0 else 0

    sorted_dates = sorted(session_data.items())
    chart_labels = [date for date, _ in sorted_dates]
    chart_counts = [data["count"] for _, data in sorted_dates]

    return render_template(
        "Insights.html",
        chart_labels=chart_labels,
        chart_counts=chart_counts,
        session_count=session_count,
        avg_duration=avg_duration,
        username=current_user.username
    )


@app.route('/Lets_Talk')
@login_required
def LetsTalk():
    session['active'] = False

    session_id = session.get('session_id')
    if session_id and session_id in chat_bot.store:
        del chat_bot.store[session_id]
    session.pop('session_id', None)

    print(current_user.username)
    return render_template('LetsTalk.html',username=current_user.username)

@app.route('/Therapy_Sessions')
@login_required
def TherapySessions():

    # Fetch all sessions and their analysis for the current user
    sessions_with_analysis = db.session.query(
        ChatSession.session_id,
        ChatSession.start_time,
        ChatSession.end_time,
        TherapyResponse.response_text,
        TherapyResponse.created_at
    ).join(TherapyResponse, TherapyResponse.session_id == ChatSession.session_id)\
     .filter(ChatSession.user_id == current_user.get_id())\
     .order_by(ChatSession.start_time.desc()).all()

    return render_template(
        'TherapySessions.html',
        sessions=sessions_with_analysis,
        username=current_user.username
    )

@app.route('/self_care')
@login_required
def SelfCare():
    return render_template("SelfCare.html")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/get-response', methods=['POST'])
@login_required
def get_response():
    if not session.get('active'):
        return jsonify({'reply': 'Please start a session to begin chatting.'})

    user_message = request.json.get('message', '').lower()
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'reply': 'No active session found. Please start a session.'})

    chat_bot.add_configuration(session_id)

    predicted_emotion, reply = chat_bot.chat(user_message)
    print(f"\n\n{predicted_emotion}\n\n")

    # Save user message
    user_msg_id = str(uuid.uuid4())
    msg = Message(
        message_id=user_msg_id,
        session_id=session_id,
        sender_type='user',
        content=user_message,
        timestamp=datetime.now(timezone.utc)
    )
    db.session.add(msg)

    # Save detected emotion
    emotion = Emotion(
        emotion_id=str(uuid.uuid4()),
        message_id=user_msg_id,
        emotion_type=predicted_emotion,
        confidence_score=1.0  # You can use actual confidence score if available
    )
    db.session.add(emotion)

    # Save bot response
    bot_msg = Message(
        message_id=str(uuid.uuid4()),
        session_id=session_id,
        sender_type='bot',
        content=reply,
        timestamp=datetime.now(timezone.utc)
    )
    db.session.add(bot_msg)

    db.session.commit()

    return jsonify({'reply': reply, 'emotion': predicted_emotion})







@app.route('/start-session', methods=['POST'])
@login_required
def start_session():
    session['active'] = True
    unique_session_id = f"user_{current_user.get_id()}_{uuid.uuid4()}"
    session['session_id'] = unique_session_id

    chat_bot.add_configuration(unique_session_id)

    # Log to DB
    new_chat_session = ChatSession(
        session_id=unique_session_id,
        user_id=current_user.get_id(),
        start_time=datetime.now(timezone.utc)
    )
    db.session.add(new_chat_session)
    db.session.commit()

    return jsonify({"status": "started"})



@app.route('/end-session', methods=['POST'])
@login_required
def end_session():
    analysis_text = "No conversation found."
    session['active'] = False
    session_id = session.get('session_id')

    if session_id:
        session_record = db.session.get(ChatSession, session_id)
        if session_record:
            session_record.end_time = datetime.now(timezone.utc)
            db.session.commit()

        # If message history exists, analyze it and store response
        if session_id in chat_bot.store:
            history = chat_bot.store[session_id].messages
            analysis_text = chat_bot.analyze_session(history)

            if analysis_text != "No conversation found.":
                # Store in TherapyResponse
                new_analysis = TherapyResponse(
                    response_id=str(uuid.uuid4()),
                    session_id=session_id,
                    response_text=analysis_text,
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(new_analysis)
                db.session.commit()

            del chat_bot.store[session_id]

    session.pop('session_id', None)

    return jsonify({
        "status": "ended",
        "analysis": analysis_text
    })

@app.route('/check-session', methods=['GET'])
@login_required
def check_session():
    return jsonify({"active": session.get('active', False)})


# if __name__ == '__main__':
#     app.run(host="0.0.0.0", port=5000, debug=True)
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)