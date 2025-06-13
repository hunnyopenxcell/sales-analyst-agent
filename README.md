# Sales Representative Performance Analytics Dashboard

This is an AI-powered Streamlit application designed to analyze sales representative performance, provide actionable insights, and automate feedback delivery.

## Features

- **Dynamic Data Source Selection**: Seamlessly switch between different sales channels (e.g., `D2B` and `T2C`) directly from the UI. The application dynamically loads the relevant sales data.
- **Overall Performance Analysis**:
    - Generates a high-level performance snapshot for a selected sales representative.
    - Identifies the **Top 3** and **Bottom 3** performing customers based on sales volume in the current year.
- **AI-Powered Recommendations**:
    - Utilizes an AI agent (GPT-4o) to generate personalized, actionable recommendations based on the performance analysis.
    - The AI provides suggestions for both top-performing customers (e.g., upselling opportunities) and underperforming customers (e.g., re-engagement strategies).
- **Automated Email Notifications**:
    - Automatically sends the AI-generated performance review and recommendations to the sales representative via email.
    - Provides an on-screen preview of the email content.
- **Interactive Intra-Month Analysis**:
    - An interactive tool to perform a granular, date-based comparison of sales performance.
    - Users can select a month and an analysis day (10th, 20th, or 30th) to compare current year sales against the same period in the previous year.

## Setup and Installation

### 1. Prerequisites

- Python 3.8+
- An active Google API key with the Gemini API enabled.
- An email account (e.g., Gmail) configured for SMTP access.

### 2. Clone the Repository

```bash
git clone <your-repository-url>
cd sales-analyst-agent
```

### 3. Create and Activate a Virtual Environment

It is highly recommended to use a virtual environment to manage project dependencies.

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

### 4. Install Dependencies

Install the required Python libraries using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 5. Set Up Data Directory

Create a directory named `sales_reps_data` in the root of the project and place your sales data Excel files inside it. The application expects the following file naming convention:
- `sales_reps_data/TP Sales Data - D2B Jan to May 2024.xlsx`
- `sales_reps_data/TP Sales Data - D2B Jan to May 2025.xlsx`
- `sales_reps_data/TP Sales Data - T2C Jan to May 2024.xlsx`
- `sales_reps_data/TP Sales Data - T2C Jan to May 2025.xlsx`

### 6. Configure Streamlit Secrets

Create a secrets file for Streamlit to securely store your API keys and email credentials.

1.  Create a directory `.streamlit` in the project root.
2.  Inside this directory, create a file named `secrets.toml`.

Add the following content to `secrets.toml` and replace the placeholder values with your actual credentials:

```toml
# .streamlit/secrets.toml

# Google API Key for Gemini
GOOGLE_API_KEY = "your-google-api-key"

# Email Configuration
SENDER_EMAIL = "your-email@example.com"
SENDER_PASSWORD = "your-email-app-password"  # Use an app-specific password for services like Gmail
SMTP_SERVER = "smtp.gmail.com"  # Example for Gmail
SMTP_PORT = 587
```

## Running the Application

Once the setup is complete, you can run the Streamlit application with the following command:

```