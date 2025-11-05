from flask import Flask, make_response

app = Flask(__name__)

@app.route('/')
def index():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simple Test</title>
        <meta charset="UTF-8">
    </head>
    <body>
        <h1>JavaScript Test</h1>
        <div id="output">Loading...</div>
        
        <script>
            console.log('Script started');
            document.getElementById('output').textContent = 'JavaScript is working!';
            console.log('Script finished');
        </script>
    </body>
    </html>
    """
    response = make_response(html)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
