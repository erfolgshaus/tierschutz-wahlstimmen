from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'geheime_fraktionsplattform'

DATABASE = 'database.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE password = ?", (password,))
        user = cur.fetchone()
        if user:
            session['user_id'] = user['id']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

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
                name = request.form['name']
                briefwahl = 1 if 'briefwahl' in request.form else 0
                cur.execute("INSERT INTO entries (user_id, name, briefwahl) VALUES (?, ?, ?)",
                            (session['user_id'], name, briefwahl))
                conn.commit()
            elif 'delete' in request.form:
                cur.execute("DELETE FROM entries WHERE id = ? AND user_id = ?", 
                            (request.form['delete'], session['user_id']))
                conn.commit()
        
        cur.execute("SELECT * FROM entries WHERE user_id = ?", (session['user_id'],))
        entries = cur.fetchall()
        return render_template('member_dashboard.html', entries=entries)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
