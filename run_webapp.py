
from src.webapp import app

app.config['JSON_AS_ASCII'] = False

if __name__ == "__main__":
    app.run(host="0.0.0.0", port="2323", debug=True)
