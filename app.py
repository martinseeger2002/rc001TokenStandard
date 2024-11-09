from rc001server import Flask, render_template_string
import subprocess
import sqlite3
import threading

app = Flask(__name__)

# Function to start the indexer
def start_indexer():
    subprocess.Popen(['python', 'rc001indexer.py'])

# Start the indexer in a separate thread
indexer_thread = threading.Thread(target=start_indexer)
indexer_thread.start()

# Function to read the database
def read_database(db_name):
    db_path = f'./db/{db_name}.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM items')
    rows = cursor.fetchall()
    conn.close()
    return rows

# HTML template with embedded JavaScript for auto-refresh
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="30">
    <title>RC001 Indexer</title>
</head>
<body>
    <h1>RC001 Indexer Database</h1>
    <table border="1">
        <tr>
            <th>Item No</th>
            <th>Inscription ID</th>
            <th>Serial Number</th>
            <th>Inscription Status</th>
            <th>Inscription Address</th>
        </tr>
        {% for row in rows %}
        <tr>
            <td>{{ row[0] }}</td>
            <td>{{ row[1] }}</td>
            <td>{{ row[2] }}</td>
            <td>{{ row[3] }}</td>
            <td>{{ row[4] }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

@app.route('/')
def index():
    db_name = 'RC001'  # Replace with your actual database name
    rows = read_database(db_name)
    return render_template_string(HTML_TEMPLATE, rows=rows)

if __name__ == '__main__':
    app.run(debug=True, port=5051) 