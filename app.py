from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3
import os
import re
import uuid

app = Flask(__name__)
app.secret_key = 'geheime_fraktionsplattform'

# Datenbank 1 (bestehende Logik)
DATABASE = 'database.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Datenbank 2 (dauerhafte Einträge im Volume)
WAHLSTIMMEN_DB = '/data/wahlstimmen.db'

def get_wahl_db():
    conn = sqlite3.connect(WAHLSTIMMEN_DB)
    conn.row_factory = sqlite3.Row
    return conn

# Tabelle in wahlstimmen.db erzeugen, falls nicht vorhanden
os.makedirs("/data", exist_ok=True)
if not os.path.exists(WAHLSTIMMEN_DB):
    conn = get_wahl_db()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wahlstimmen (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                name TEXT,
                bezirk TEXT,
                stimmen INTEGER
            )
        """)

@app.route('/ping')
def ping():
    return "OK", 200

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        password = request.form['password']
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE password = ?", (password,))
            user = cur.fetchone()
            if user:
                session['user_id'] = user['id']
                session['is_admin'] = user['is_admin']
                return redirect(url_for('dashboard'))
            else:
                error = "Falsches Passwort"
        except Exception as e:
            error = f"Fehler beim Login: {str(e)}"
    return render_template('login.html', error=error)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    error = None
    try:
        conn = get_db()
        cur = conn.cursor()

        if session.get('is_admin'):
            cur.execute("""
                SELECT users.name, COUNT(entries.id) as total, 
                       SUM(entries.briefwahl) as briefwahl
                FROM users LEFT JOIN entries ON users.id = entries.user_id
                GROUP BY users.id
            """)
            summary = cur.fetchall()
            return render_template('admin_dashboard.html', summary=summary)

        else:
            if request.method == 'POST':
                if 'name' in request.form:
                    raw_name = request.form['name']
                    name = re.sub(r'\s+', ' ', raw_name).strip()

                    cur.execute("SELECT 1 FROM entries WHERE LOWER(TRIM(name)) = LOWER(?)", (name,))
                    exists = cur.fetchone()
                    if exists:
                        error = "Die Person ist schon eingetragen."
                    else:
                        cur.execute("INSERT INTO entries (user_id, name, briefwahl) VALUES (?, ?, ?)",
                                    (session['user_id'], name, 0))
                        conn.commit()

                        # ⬇️ Zusätzlich in wahlstimmen.db speichern
                        wahl_conn = get_wahl_db()
                        with wahl_conn:
                            wahl_conn.execute(
                                "INSERT INTO wahlstimmen (id, user_id, name, bezirk, stimmen) VALUES (?, ?, ?, ?, ?)",
                                (str(uuid.uuid4()), session['user_id'], name, "unbekannt", 1)
                            )

                elif 'delete' in request.form:
                    cur.execute("DELETE FROM entries WHERE id = ? AND user_id = ?", 
                                (request.form['delete'], session['user_id']))
                    conn.commit()

                elif 'toggle_briefwahl' in request.form:
                    entry_id = request.form['toggle_briefwahl']
                    cur.execute("SELECT briefwahl FROM entries WHERE id = ? AND user_id = ?", 
                                (entry_id, session['user_id']))
                    current = cur.fetchone()
                    new_value = 0 if current['briefwahl'] else 1
                    cur.execute("UPDATE entries SET briefwahl = ? WHERE id = ? AND user_id = ?", 
                                (new_value, entry_id, session['user_id']))
                    conn.commit()

            cur.execute("SELECT * FROM entries WHERE user_id = ?", (session['user_id'],))
            entries = cur.fetchall()
            return render_template('member_dashboard.html', entries=entries, error=error)

    except Exception as e:
        return f"<h1>Fehler im Dashboard:</h1><p>{str(e)}</p>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Admin-Test-Route (optional): Alle Einträge aus der zweiten DB anzeigen
@app.route('/wahlstimmen', methods=['GET'])
def alle_wahlstimmen():
    conn = get_wahl_db()
    cursor = conn.execute("SELECT * FROM wahlstimmen")
    daten = [dict(row) for row in cursor.fetchall()]
    return jsonify(daten)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
