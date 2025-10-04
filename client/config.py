import os

import toml


def write_toml_file(file_path, data):
    """
    Write a dictionary to a TOML file.

    :param file_path: Path to the TOML file.
    :param data: Dictionary to write to the file.
    """
    with open(file_path, "w", encoding="utf-8") as f:
        toml.dump(data, f)


def get_streamlit_config():
    port = os.getenv("CLIENT_PORT", "8501")
    config = {
        "server": {
            "port": port,
            "headless": True,
        },
        "browser": {
            "gatherUsageStats": False,
        },
        "theme": {
            "base": "dark",
            "primaryColor": "#13984dff",
        },
    }
    return config


def get_streamlit_secrets():
    """
    Get the Streamlit secret configuration.

    :return: Dictionary containing the Streamlit secret configuration.
    """
    secrets = {
        "auth": {
            "client_id": os.getenv("OAUTH_CLIENT_ID"),
            "client_secret": os.getenv("OAUTH_CLIENT_SECRET"),
            "server_metadata_url": os.getenv("OAUTH_SERVER_METADATA_URL"),
            "redirect_uri": os.getenv("OAUTH_REDIRECT_URI"),
            "cookie_secret": os.getenv("OAUTH_COOKIE_SECRET"),
        }
    }
    return secrets


def run():
    """
    Main function to write the Streamlit configuration and secrets to files.
    """
    config = get_streamlit_config()
    secrets = get_streamlit_secrets()

    if not os.path.exists(".streamlit"):
        os.makedirs(".streamlit")
    # Write the configuration to a file
    write_toml_file(".streamlit/config.toml", config)

    # Write the secrets to a file
    write_toml_file(".streamlit/secrets.toml", secrets)


if __name__ == "__main__":
    run()
