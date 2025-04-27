# auth.py - REVISED AGAIN TO PREVENT AttributeError ON st.error IN HELPER
import streamlit as st
from streamlit_oauth import OAuth2Component
# You might need PyYAML for this, add to requirements.txt if you get errors
# import yaml
import json # Potentially useful if secrets are read complexly
import traceback # Import traceback to print full trace to console/logs

def get_oauth_config():
    """
    Loads OAuth configuration from Streamlit secrets.
    Returns the config dict or None if config is missing or invalid.
    Prints detailed errors to the console/server logs, does *not* use st.error
    internally for missing keys to avoid potential issues.
    """
    try:
        # Attempt to access the google_oauth section
        if "google_oauth" not in st.secrets:
             print(f"--- OAuth Configuration Error ---")
             print("OAuth configuration ([google_oauth] section) not found in secrets.toml")
             print("Please create a .streamlit/secrets.toml file with google_oauth credentials.")
             print(f"---------------------------------")
             return None # Indicate failure

        config = st.secrets["google_oauth"]
        required_keys = ["client_id", "client_secret", "redirect_uri", "scope"]
        missing_keys = [key for key in required_keys if key not in config]

        if missing_keys:
             # Print to console/logs instead of st.error here
             print(f"--- OAuth Configuration Error ---")
             print(f"Missing required keys in [google_oauth] section of secrets.toml: {', '.join(missing_keys)}")
             print(f"---------------------------------")
             return None # Indicate failure

        # Check if scope is a list, convert if it's a string (common mistake)
        if isinstance(config.get("scope"), str):
             print(f"--- OAuth Configuration Warning ---")
             print("OAuth scope in secrets.toml is a string, converting to list.")
             print(f"---------------------------------")
             config["scope"] = [s.strip() for s in config["scope"].split(',')] # Split string by comma and strip whitespace

        # Basic validation for non-empty strings
        for key in required_keys:
             if not isinstance(config.get(key), str) or not config.get(key).strip():
                  print(f"--- OAuth Configuration Error ---")
                  print(f"Required key '{key}' in [google_oauth] is missing or empty.")
                  print(f"---------------------------------")
                  return None


        return config # Return config if all checks pass

    except Exception as e:
        # Catch any other unexpected error during secrets reading
        print(f"--- OAuth Configuration Error ---")
        print(f"An unexpected error occurred reading OAuth configuration from secrets.toml: {e}")
        traceback.print_exc() # Print full traceback to console/logs
        print(f"---------------------------------")
        return None # Indicate failure


def authenticate_user():
    """
    Handles Google OAuth authentication.
    Returns the user_id string if authenticated, None otherwise.
    Displays user-facing st.error messages based on the outcome of get_oauth_config
    or errors during the OAuth flow itself.
    """
    st.sidebar.title("Authentication")

    # --- Core Authentication Logic ---
    try:
        # Get configuration first. This function prints detailed errors to logs.
        oauth_config = get_oauth_config()

        if oauth_config is None:
            # Configuration was invalid (missing section, missing keys, etc.)
            # get_oauth_config already printed details to logs.
            # Display a user-friendly error message in the app.
            st.error("OAuth configuration is invalid. Please check your `.streamlit/secrets.toml` file and the console/server logs for details.")
            # Ensure authentication state is clear
            st.session_state['token'] = None
            st.session_state['user_info'] = None
            st.session_state['user_id'] = None
            st.session_state['user_email'] = None
            return None # Cannot proceed without valid config

        # If config is valid, proceed with OAuth
        authorize_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        token_endpoint = "https://oauth2.googleapis.com/token"

        # Initialize the OAuth2Component. Use a unique key.
        # The key must be consistent across reruns. Changed key again for safety.
        oauth2 = OAuth2Component(
            oauth_config["client_id"],
            oauth_config["client_secret"],
            authorize_endpoint,
            token_endpoint,
            oauth_config["redirect_uri"],
            oauth_config["scope"],
            key="google_oauth_login_component_v4"
        )

        # Check/Initialize session state variables
        if 'token' not in st.session_state: st.session_state['token'] = None
        if 'user_info' not in st.session_state: st.session_state['user_info'] = None
        if 'user_id' not in st.session_state: st.session_state['user_id'] = None
        if 'user_email' not in st.session_state: st.session_state['user_email'] = None


        if st.session_state['token'] is None:
            # User is not authenticated, display the login button
            st.sidebar.write("Please log in:")
            # This call initiates the OAuth flow
            result = oauth2.authorize_button(
                name="Continue with Google",
                icon="https://www.google.com/favicon.ico",
                redirect_uri=oauth_config["redirect_uri"],
                # Add prompt="consent" if you want users to re-consent every time (optional)
                # Add access_type="offline" and include 'offline' in scopes if you need refresh tokens (more advanced)
            )

            if result:
                # If the authorization flow completed and returned a result (token)
                st.session_state['token'] = result
                # Check if result is a dict before accessing user_info
                st.session_state['user_info'] = result.get('user_info') if isinstance(result, dict) else None

                if st.session_state['user_info'] and isinstance(st.session_state['user_info'], dict):
                     st.session_state['user_id'] = st.session_state['user_info'].get('sub') # Unique Google user ID
                     st.session_state['user_email'] = st.session_state['user_info'].get('email')
                else:
                    # Handle cases where user_info is missing or not a dictionary after successful token retrieval
                    st.warning("Could not retrieve user information after login. Check if 'profile' and 'email' scopes are included and granted.")
                    st.session_state['user_id'] = None # Ensure user_id is explicitly None
                    st.session_state['user_email'] = None

                # Only rerun if we successfully got a user ID, otherwise stay on login screen
                if st.session_state['user_id']:
                     st.rerun()

            # If result is None, the button was just displayed, authentication is pending
            return None # User is not yet authenticated or login failed to get user_id

        else:
            # User is authenticated, display user information and a logout button
            user_info = st.session_state.get('user_info')
            if user_info and isinstance(user_info, dict):
                st.sidebar.write(f"Welcome, {user_info.get('name', 'User')}!")
                st.sidebar.write(f"Email: {user_info.get('email', 'N/A')}")
            else:
                # Fallback if user_info somehow got lost but token exists
                st.sidebar.write("Welcome!")
                st.sidebar.write("User info not available.")


            # Add a logout button in the sidebar
            if st.sidebar.button("Logout", key="google_logout_button_v4"): # Changed key
                # Clear all authentication-related session state variables
                st.session_state['token'] = None
                st.session_state['user_info'] = None
                st.session_state['user_id'] = None
                st.session_state['user_email'] = None
                st.rerun() # Rerun to show the login button again

            # Return the unique user identifier if authenticated
            return st.session_state.get('user_id') # Return the stored user ID


    except Exception as e:
        # Catch any unexpected error during the *authentication process itself*
        # This block catches errors happening during the OAuth2Component interaction etc.
        st.error(f"An unexpected error occurred during the authentication process: {e}")
        st.info("This often indicates a problem with your Google Cloud OAuth setup, Redirect URIs, or library compatibility.")
        st.info("Check the terminal/server logs for the full traceback and specific error message.")
        st.exception(e) # Display traceback in the app for easier debugging if possible
        print("\n--- Authentication Process Error Traceback (from auth.py) ---")
        traceback.print_exc() # Print full traceback to console/logs
        print("-------------------------------------------------------------\n")

        # Clear authentication state on error to avoid being stuck
        st.session_state['token'] = None
        st.session_state['user_info'] = None
        st.session_state['user_id'] = None
        st.session_state['user_email'] = None

        return None # Indicate authentication failed
