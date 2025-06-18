from flask import Flask, render_template
import datetime
import uuid
import socket
import os
from careers import careers_blueprint

app = Flask(__name__)

# Ensure the 'data' folder exists to store uploaded files
os.makedirs('data', exist_ok=True)

# Register the careers blueprint
app.register_blueprint(careers_blueprint, url_prefix='/careers')

@app.route('/')
def home():
    # Get the current date
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Get the unique system identifier (UUID)
    system_id = str(uuid.uuid4())  # Generates a random unique system identifier

    # Get the private IP address
    private_ip = socket.gethostbyname(socket.gethostname())  # Get the local IP address

    # Render the home template with the system info
    return render_template('home.html', current_date=current_date, system_id=system_id, private_ip=private_ip)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
