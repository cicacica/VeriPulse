## Getting Started

Always use `uv` to run anything in this project.

### 1. Install dependencies
```bash
uv sync
uv pip install -e vendor/qutip-qtrl
```

### 2. Register the Jupyter kernel
```bash
uv run python -m ipykernel install --user --name veripulse --display-name "VeriPulse"
```

### 3. Run tests
```bash
uv run pytest
```

### 4. Launch Jupyter
```bash
uv run jupyter lab
```

Then select the **VeriPulse** kernel in Jupyter.


