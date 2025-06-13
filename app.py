import streamlit as st
import pandas as pd
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="Sales Rep Performance Analytics",
    page_icon="📊",
    layout="wide"
)

# --- AI & Email Configuration ---
# Load secrets from Streamlit's secrets management
try:
    # openai.api_key = st.secrets["OPENAI_API_KEY"]
    SENDER_EMAIL = st.secrets["email"]["SENDER_EMAIL"]
    SENDER_PASSWORD = st.secrets["email"]["SENDER_PASSWORD"]
    SMTP_SERVER = st.secrets["email"]["SMTP_SERVER"]
    SMTP_PORT = st.secrets["email"]["SMTP_PORT"]
except KeyError:
    st.error("ERROR: OpenAI or Email credentials are not set in st.secrets.")
    st.stop()


# --- Caching Data Loading ---
@st.cache_data
def load_data(source):
    """Loads, cleans, and merges sales data from two Excel files based on the selected source."""
    try:
        # Construct file paths dynamically based on the selected source
        path_2024 = f"sales_reps_data/TP Sales Data - {source} Jan to May 2024.xlsx"
        path_2025 = f"sales_reps_data/TP Sales Data - {source} Jan to May 2025.xlsx"

        df_2024 = pd.read_excel(path_2024)
        df_2025 = pd.read_excel(path_2025)

        # Combine the two dataframes
        df = pd.concat([df_2024, df_2025], ignore_index=True)

        # Data Cleaning and Preparation
        df['Trans Date'] = pd.to_datetime(df['Trans Date'], errors='coerce')
        # Ensure correct data types
        df['Qty in HLs'] = pd.to_numeric(df['Qty in HLs'], errors='coerce')
        df.dropna(subset=['Qty in HLs', 'Zone', 'account_name', 'Year', 'Month', 'Trans Date'], inplace=True)

        return df
    except FileNotFoundError as e:
        st.error(f"Error: Missing sales data files for source '{source}'. Please check the '/sales_data' directory.")
        st.info(f"Could not find: {e.filename}")
        return None


# --- Core Analytics Functions ---
def get_overall_analysis(df, rep_id):
    """Performs overall sales analysis: Top/Bottom 3 customers and YoY growth."""
    rep_df = df[df['Zone'] == rep_id].copy()
    if rep_df.empty:
        return None, None, None

    # --- Top & Bottom 3 Customers by Volume in 2025 ---
    df_2025 = rep_df[rep_df['Year'] == 2025]
    if df_2025.empty:
        # Return empty dataframes if no data for 2025
        return pd.Series(dtype='float64'), pd.Series(dtype='float64'), pd.DataFrame()

    customer_performance = df_2025.groupby('account_name')['Qty in HLs'].sum().sort_values(ascending=False)
    top_3_customers = customer_performance.head(3)
    bottom_3_customers = customer_performance.tail(3)

    # --- YoY Growth Comparison ---
    yoy_df = rep_df.groupby(['account_name', 'Year'])['Qty in HLs'].sum().unstack()
    yoy_df.columns = ['Volume_2024', 'Volume_2025']
    yoy_df.fillna(0, inplace=True)
    yoy_df['YoY_Change'] = yoy_df['Volume_2025'] - yoy_df['Volume_2024']

    # Handle division by zero for YoY Growth %
    yoy_df['YoY_Growth_%'] = 100 * (yoy_df['YoY_Change'] / yoy_df['Volume_2024'])
    yoy_df.replace([float('inf'), -float('inf')], 100.0, inplace=True) # If LY was 0, show 100% growth
    yoy_df['YoY_Growth_%'].fillna(0, inplace=True)

    return top_3_customers, bottom_3_customers, yoy_df.reset_index()


def get_date_based_analysis(df, rep_id, reference_date):
    """
    Performs a detailed, date-based sales analysis for a specific representative's customers.
    - Volume by reference_date of this month
    - Volume by reference_date of same month last year
    - % achieved
    """
    rep_df = df[df['Zone'] == rep_id].copy()
    if rep_df.empty:
        return pd.DataFrame()

    current_month_num = reference_date.month
    current_month_name = reference_date.strftime('%B') # Full month name for display
    current_year = reference_date.year
    day_of_month = reference_date.day
    last_year = current_year - 1

    # Standardize month data for robust filtering
    # A copy is made to avoid SettingWithCopyWarning
    df_with_month_num = rep_df.copy()
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    df_with_month_num['MonthNum'] = df_with_month_num['Month'].str.strip().str.lower().str[:3].map(month_map)
    df_with_month_num.dropna(subset=['MonthNum'], inplace=True) # Drop rows where month could not be parsed
    df_with_month_num['MonthNum'] = df_with_month_num['MonthNum'].astype(int)

    # Filter for the relevant month in both years
    monthly_df = df_with_month_num[df_with_month_num['MonthNum'] == current_month_num].copy()

    # Get a list of all customers for this rep from the monthly data
    customers = sorted(monthly_df['account_name'].unique())
    analysis_results = []

    for customer in customers:
        customer_df = monthly_df[monthly_df['account_name'] == customer]

        # Volume for the current period (up to day_of_month)
        volume_current_year = customer_df[
            (customer_df['Year'] == current_year) &
            (customer_df['Trans Date'].dt.day <= day_of_month)
        ]['Qty in HLs'].sum()

        # Volume for the same period last year
        volume_last_year = customer_df[
            (customer_df['Year'] == last_year) &
            (customer_df['Trans Date'].dt.day <= day_of_month)
        ]['Qty in HLs'].sum()

        # Calculate % achieved
        if volume_last_year > 0:
            achieved_percent = (volume_current_year / volume_last_year) * 100
        elif volume_current_year > 0:
            achieved_percent = 100.0  # Represent as 100% growth if LY was 0 but TY has sales
        else:
            achieved_percent = 0.0

        analysis_results.append({
            'Customer Name': customer,
            f'Volume by Day {day_of_month} ({current_month_name} {current_year})': f"{volume_current_year:.2f}",
            f'Volume by Day {day_of_month} ({current_month_name} {last_year})': f"{volume_last_year:.2f}",
            '% Achieved': f"{achieved_percent:.1f}%"
        })

    result_df = pd.DataFrame(analysis_results)
    return result_df


# --- AI Agent Function ---
def get_ai_recommendations_for_email(rep_id, top_customers, bottom_customers):
    """Uses an AI agent to generate insights and recommendations for the automated email."""

    if top_customers.empty and bottom_customers.empty:
        return "No data available to generate recommendations."

    # Create a detailed prompt for the AI agent
    prompt = f"""
    You are an expert Sales Analyst Agent. Your task is to provide a concise, actionable performance review for a sales representative, which will be sent via email.

    **Sales Representative Zone:** {rep_id}

    **Analysis of Top and Bottom Customers (Based on Jan-May 2025 Volume):**

    **Top 3 Performing Customers (by Volume):**
    {top_customers.to_string()}

    **Bottom 3 Performing Customers (by Volume):**
    {bottom_customers.to_string()}

    **Instructions for Email Content:**
    Based on the top and bottom customer data, please generate a concise, actionable performance review suitable for an email.
    1.  **Overall Summary:** A brief, encouraging opening paragraph summarizing the performance highlights.
    2.  **Top Performers Analysis & Recommendations:** Congratulate the rep on the success with top customers. Provide specific, forward-looking recommendations for them (e.g., "For [Customer Name], consider introducing new premium products like 'Heineken Silver' or 'Edelweiss' to build on their strong performance.").
    3.  **Underperforming/Opportunity Areas Analysis & Recommendations:** For the bottom customers, adopt a supportive tone, framing them as "growth opportunities." Suggest actionable recovery strategies (e.g., "For [Customer Name], let's try to re-engage them to understand their recent needs or check for competitor activity.").
    4.  **Closing Statement:** End with a positive and motivating closing remark.

    The tone should be professional, data-driven, and supportive.
    """

    try:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful sales analyst assistant specialized in writing performance emails."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error calling OpenAI API: {e}")
        return "Could not generate AI recommendations due to an API error."


# --- Email Function ---
def send_email(recipient_email, subject, body):
    """Sends an email with the analysis and recommendations."""
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False


# --- Main Streamlit App ---
st.title("📊 Sales Representative Performance Dashboard")
st.markdown("An AI-powered tool to analyze sales performance and generate actionable insights.")

# --- Data Source Selection ---
st.sidebar.title("Configuration")
st.sidebar.header("Select Data Source")

def clear_state_on_source_change():
    """Clear session state when the data source changes to avoid conflicts."""
    # We keep 'data_source' itself but clear everything else
    keys_to_keep = ['data_source']
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]

# Add a radio button to select the data channel (D2B or T2C)
selected_source = st.sidebar.radio(
    "Channel",
    ["D2B", "T2C"],
    key="data_source",
    on_change=clear_state_on_source_change # Important to reset state
)

# Load data based on the selected source
data = load_data(selected_source)


if data is not None:
    st.header(f"Analyze Performance for Channel: {selected_source}")
    sales_reps = sorted(data['Zone'].unique())

    if 'selected_rep' not in st.session_state:
        st.session_state['selected_rep'] = None

    for rep in sales_reps:
        if st.button(f"Analyze {rep}", key=rep):
            st.session_state['selected_rep'] = rep
            # Clear all previous results when switching reps
            for key in list(st.session_state.keys()):
                if key not in ['selected_rep', 'data_source']:
                    del st.session_state[key]

    if st.session_state.get('selected_rep') is not None:
        selected_rep = st.session_state['selected_rep']
        st.markdown("---")
        st.header(f"📈 Performance Analysis for: {selected_rep}")

        # --- Overall Performance Section ---
        st.subheader("Overall Performance (Jan-May 2025)")
        st.markdown("This section analyzes total sales volume for 2025 to identify top and bottom customers and automatically emails the summary to the rep.")

        # Button to trigger analysis and email
        if st.button(f"🚀 Analyze Overall Performance & Auto-Send Email", key=f"overall_{selected_rep}"):
            with st.spinner(f"Analyzing overall data for {selected_rep}..."):
                top_3, bottom_3, yoy_df = get_overall_analysis(data, selected_rep)
                # Store results in session state
                st.session_state['top_3'] = top_3
                st.session_state['bottom_3'] = bottom_3
                st.session_state['yoy_df'] = yoy_df
                st.session_state['overall_analysis_run_for'] = selected_rep

            if top_3 is not None and not top_3.empty:
                with st.spinner("🤖 AI generating email content..."):
                    ai_email_content = get_ai_recommendations_for_email(selected_rep, top_3, bottom_3)
                    st.session_state['ai_email_content'] = ai_email_content

                with st.spinner("📧 Automatically sending email..."):
                    rep_email_map = {"D2B": "salesrep.d2b@example.com"}
                    rep_email = rep_email_map.get(selected_rep, "default.rep@example.com")
                    email_subject = f"Your Performance Review & Recommendations: {selected_rep}"
                    full_email_body = f"Hi {selected_rep},\n\nHere is your performance summary and some recommendations from our analytics system.\n\n---\n\n{st.session_state['ai_email_content']}"

                    # Note: Email sending is commented out for demonstration.
                    # Uncomment the line below to enable it.
                    # send_email(rep_email, email_subject, full_email_body)
                    st.success(f"Email with recommendations has been automatically sent to {rep_email} (Sending is disabled in this demo).")
            else:
                st.error(f"No 2025 data found for Sales Rep {selected_rep} to generate an analysis.")

        # Display cached results if they exist for the current rep
        if st.session_state.get('overall_analysis_run_for') == selected_rep:
            st.subheader("Performance Snapshot")
            col1, col2 = st.columns(2)
            with col1:
                st.success("Top 3 Customers (by Volume)")
                st.dataframe(st.session_state.get('top_3', pd.Series(dtype='float64')))
            with col2:
                st.warning("Bottom 3 Customers (by Volume)")
                st.dataframe(st.session_state.get('bottom_3', pd.Series(dtype='float64')))

            # st.subheader("Year-over-Year (YoY) Growth Analysis")
            # st.dataframe(st.session_state.get('yoy_df', pd.DataFrame()), use_container_width=True)

            if 'ai_email_content' in st.session_state:
                st.subheader("💡 AI-Generated Recommendations (Email Preview)")
                st.markdown(st.session_state['ai_email_content'])

        # --- Intra-Month Performance Section ---
        st.markdown("---")
        st.subheader("📅 Intra-Month Performance Comparison")
        st.markdown("Use this interactive tool to compare sales volume up to a specific day of the month against the same period last year. This does **not** trigger an email.")

        # Let's provide a dropdown for the months available in the data (Jan-May)
        month_name_to_num = {
            "January": 1, "February": 2, "March": 3, "April": 4, "May": 5
        }
        selected_month_name = st.selectbox(
            "Select a month to analyze",
            options=list(month_name_to_num.keys()),
            key=f"month_select_{selected_rep}"
        )

        analysis_month = month_name_to_num[selected_month_name]
        analysis_year = 2025

        col1, col2, col3, _ = st.columns([1, 1, 1, 2])
        analysis_day = 0
        if col1.button("Analyze up to 10th", key=f"10th_{selected_rep}"):
            analysis_day = 10
        if col2.button("Analyze up to 20th", key=f"20th_{selected_rep}"):
            analysis_day = 20
        if col3.button("Analyze up to 30th", key=f"30th_{selected_rep}"):
            analysis_day = 30

        if analysis_day > 0:
            # Store the day and month name for consistent display after rerun
            st.session_state['analysis_day'] = analysis_day
            st.session_state['selected_month_name'] = selected_month_name

            reference_date = datetime(analysis_year, analysis_month, analysis_day)
            with st.spinner(f"Analyzing data for {selected_rep} for {selected_month_name} up to day {analysis_day}..."):
                analysis_df = get_date_based_analysis(data, selected_rep, reference_date)
                st.session_state['date_analysis_df'] = analysis_df
                st.session_state['date_analysis_run_for'] = selected_rep

        if st.session_state.get('date_analysis_run_for') == selected_rep and 'date_analysis_df' in st.session_state:
            display_month = st.session_state.get('selected_month_name', 'the selected month')
            display_day = st.session_state.get('analysis_day', '')
            st.markdown(f"**Comparison for month of {display_month} up to day {display_day}**")
            st.dataframe(st.session_state['date_analysis_df'], use_container_width=True)
