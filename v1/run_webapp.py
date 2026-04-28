from src.webapp import app
import os

app.config['JSON_AS_ASCII'] = False

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port="2323", debug=debug_mode)
