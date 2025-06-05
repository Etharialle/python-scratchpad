# Python venvs

venv-start() {
    if [ -d "$HOME/venv/$1" ]; then
        source "$HOME/venv/$1/bin/activate"
        echo "Activated virtual environment: $1"
        if [ "$2" == "ros" ]; then
            echo "ros libraries initialized"
        else
            unset "PYTHONPATH"
        fi
    else
        echo "Virtual environment $1 does not exist."
    fi
}

# Function to deactivate virtual environment
venv-stop() {
    deactivate
    echo "Deactivated the virtual environment."
    source "$HOME/.bashrc"
}

# Function to create a venv
venv-create() {
    if [ -d "$HOME/venv/$1" ]; then
        echo "Virtual environment $1 already exists."
    else
        python3 -m venv "$HOME/venv/$1"
        echo "Virtual environment $1 created."
    fi
}