## Quick Start

### Prerequisites

- Python 3.12
- pip
- Node.js 14+ (for building CSS)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/KazumaChoji/Cache.git
cd Cache
```

2. Create venv and install Python dependencies:
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Install Node.js dependencies and build CSS:
```bash
npm install
npm run build:css
```

4. (Optional) Set environment variables:
```bash
export MAPBOX_TOKEN="your_mapbox_token_here"
```

### Running the Application

Start the FastAPI server:
```bash
python main.py
```

Or use uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser to: **http://localhost:8000**

### Development

To watch for CSS changes during development:
```bash
npm run watch:css
```
