"""Flask entry point. Run: python app.py"""
from flask import Flask
from web.routes import bp

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB uploads
app.register_blueprint(bp)

if __name__ == "__main__":
    app.run(debug=True)
