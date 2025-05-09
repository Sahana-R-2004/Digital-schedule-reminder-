from app import app, db  # Make sure 'app' is the name of your Flask app file
with app.app_context():
    db.create_all()
    print("Database created successfully!")
