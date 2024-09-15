from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import UserProfile, UserData, InteractionType  # Adjust import paths as needed

# Configure your database connection
engine = create_engine('sqlite:///path_to_your_database.db')  # Replace with your actual database URI
Session = sessionmaker(bind=engine)
session = Session()

try:
    # Fetch all UserProfile entries to fix JSON data
    user_profiles = session.query(UserProfile).all()
    for profile in user_profiles:
        # If fields are stored as JSON strings, convert them to lists
        if isinstance(profile.preferred_categories, str):
            profile.preferred_categories = []  # Set to empty list or appropriate default
        if isinstance(profile.preferred_modules, str):
            profile.preferred_modules = []  # Set to empty list or appropriate default

        # Save changes
        session.add(profile)

    # Commit the updates to the database
    session.commit()
    print("Successfully updated UserProfile JSON fields.")

    # Optionally, reset UserData if needed
    user_data_entries = session.query(UserData).all()
    default_interaction_type = session.query(InteractionType).filter_by(name='viewed').first()

    if not default_interaction_type:
        raise Exception("Default interaction type 'viewed' not found in the interaction_types table.")

    for user_data in user_data_entries:
        if not user_data.interaction_type_id:
            user_data.interaction_type_id = default_interaction_type.id

        session.add(user_data)

    # Commit changes to UserData
    session.commit()
    print("Successfully updated UserData fields.")

except Exception as e:
    # Roll back in case of an error
    session.rollback()
    print(f"An error occurred: {e}")

finally:
    # Close the session
    session.close()