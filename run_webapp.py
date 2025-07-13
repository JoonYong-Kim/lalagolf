
from src.webapp import app

app.config['JSON_AS_ASCII'] = False

if __name__ == "__main__":
    app.run(debug=True)
