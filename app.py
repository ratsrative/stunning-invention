# auth.py - RECTIFIED VERSION
import streamlit as st
from streamlit_oauth import OAuth2Component
# You might need PyYAML for this, add to requirements.txt if you get errors
# import yaml
import json # Potentially useful if secrets are read complexly, but often not needed directly here

def get_oauth_config():
    """Loads OAuth configuration from Streamlit secrets."""
    try:
        config = st.secrets["google_oauth"]
        # Basic validation to check if required keys exist
        required_keys = ["client_id", "client_secret", "redirect_uri", "scope"]
        if not all(key in config for key in required_keys):
             missing = [key for key in required_keys if key not in config]
             st.error(f"Missing required keys in [google_oauth] section of secrets.toml: {', '.join(missing)}")
             return None
        return config
    except KeyError:
        st.error("OAuth configuration ([google_oauth] section) not found in secrets.toml")
        st.info("Please create a .streamlit/secrets.toml file with google_oauth credentials.")
        return None
    except Exception as e:
        st.error(f"Error reading OAuth configuration from secrets.toml: {e}")
        return None


def authenticate_user():
    """Handles Google OAuth authentication."""
    st.sidebar.title("Authentication") # Add a title to the sidebar section

    # --- Core Authentication Logic wrapped in a try-except ---
    try:
        oauth_config = get_oauth_config()
        if not oauth_config:
            # get_oauth_config already showed an error, just return None
            return None

        authorize_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        token_endpoint = "https://oauth2.googleapis.com/token"

        # Initialize the OAuth2Component. Use a unique key.
        # The key must be consistent across reruns for the component to work correctly.
        oauth2 = OAuth2Component(
            oauth_config["client_id"],
            oauth_config["client_secret"],
            authorize_endpoint,
            token_endpoint,
            oauth_config["redirect_uri"],
            oauth_config["scope"],
            key="google_oauth_login_component" # Use a static key string
        )

        # Check if the token exists in Streamlit's session state
        # Initialize session state variables if they don't exist
        if 'token' not in st.session_state:
            st.session_state['token'] = None
        if 'user_info' not in st.session_state:
            st.session_state['user_info'] = None
        if 'user_id' not in st.session_state:
             st.session_state['user_id'] = None
        if 'user_email' not in st.session_state:
             st.session_state['user_email'] = None


        if st.session_state['token'] is None:
            # User is not authenticated, display the login button
            st.sidebar.write("Please log in:")
            result = oauth2.authorize_button(
                name="Continue with Google",
                icon="https://www.google.com/favicon.ico",
                redirect_uri=oauth_config["redirect_uri"], # Pass redirect_uri here too
                # You might need additional parameters like prompt="consent"
                # or access_type="offline" depending on your needs
            )

            if result:
                # If the authorization flow completed and returned a result (token)
                st.session_state['token'] = result
                # The result dict should contain 'user_info' if 'profile' and 'email' scopes were requested
                st.session_state['user_info'] = result.get('user_info')
                if st.session_state['user_info']:
                     # Store the unique Google user ID and email
                     st.session_state['user_id'] = st.session_state['user_info'].get('sub')
                     st.session_state['user_email'] = st.session_state['user_info'].get('email')
                st.rerun() # Rerun the app to transition from login state

            # If result is None, the button was just displayed, authentication is pending
            return None # User is not yet authenticated or authentication failed

        else:
            # User is authenticated, display user information and a logout button
            user_info = st.session_state.get('user_info')
            if user_info:
                st.sidebar.write(f"Welcome, {user_info.get('name', 'User')}!")
                st.sidebar.write(f"Email: {user_info.get('email', 'N/A')}")

            # Add a logout button in the sidebar
            # Use a unique key for the button
            if st.sidebar.button("Logout", key="google_logout_button"):
                # Clear all authentication-related session state variables
                st.session_state['token'] = None
                st.session_state['user_info'] = None
                st.session_state['user_id'] = None
                st.session_state['user_email'] = None
                st.rerun() # Rerun to show the login button again

            # Return the unique user identifier if authenticated
            return st.session_state.get('user_id') # Use .get() for safety


    except Exception as e:
        # --- This is the crucial part for catching the AttributeError ---
        # Catch any unexpected error that occurs during the authentication logic
        st.error(f"An unexpected error occurred during authentication process: {e}")
        st.info("Please check your secrets.toml and Google Cloud OAuth setup.")
        # Optionally display the full traceback in the app for debugging
        st.exception(e)
        # Print traceback to the terminal where Streamlit is running
        import traceback
        print("--- Authentication Error Traceback ---")
        traceback.print_exc()
        print("------------------------------------")

        # Clear authentication state on error to avoid being stuck
        st.session_state['token'] = None
        st.session_state['user_info'] = None
        st.session_state['user_id'] = None
        st.session_state['user_email'] = None

        return None # Indicate authentication failed
