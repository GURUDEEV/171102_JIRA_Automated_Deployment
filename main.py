import streamlit as st
import pandas as pd
import base64
import re
from utils.sentiment_analyzer import SentimentAnalyzer
from assets.smileys import SMILEY_ICONS

# Page configuration
st.set_page_config(
    page_title="Retrospective Sentiment Analysis",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown(
    """
    <style>
    .stDataFrame {
        font-size: 14px;
    }
    .sentiment-score {
        font-weight: bold;
        padding: 4px 8px;
        border-radius: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

def get_smiley_html(category: str) -> str:
    """Convert SVG to base64 for HTML embedding"""
    svg = SMILEY_ICONS.get(category, SMILEY_ICONS['neutral'])
    b64 = base64.b64encode(svg.encode('utf-8')).decode('utf-8')
    return f'<img src="data:image/svg+xml;base64,{b64}" width="24" height="24">'

def sanitize_text(text: str) -> str:
    """Sanitize text by removing special characters, bullets, newlines, and extra spaces"""
    if not isinstance(text, str):
        return ""
    
    # Remove special characters (e.g., $, %, +, etc.)
    text = re.sub(r'[^\w\s.,!?]', ' ', text)
    
    # Remove bullets (•, -, *, etc.)
    text = re.sub(r'[\•\-\*]', ' ', text)
    
    # Remove newlines and extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def analyze_retrodata(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze sentiment for each row in the dataframe"""
    analyzer = SentimentAnalyzer()

    sentiment_columns = [
        'What Did Not Go Well?',
        'What Went Well?',
        'Reason for Churn',
        'Improvement opportunity',
        'Reason for reported success rate'
    ]

    for col in sentiment_columns:
        if col in df.columns:
            # Sanitize the text in the column
            df[col] = df[col].apply(sanitize_text)
            
            # Analyze sentiment for each row in the column
            sentiments = []
            for text in df[col]:
                sentiment = analyzer.analyze_text(str(text))  # handle potential non-string values
                sentiments.append(sentiment)
            
            # Add sentiment information to the dataframe
            df[f'{col}_Sentiment_Score'] = [s['compound'] for s in sentiments]
            df[f'{col}_Sentiment_Category'] = [s['category'] for s in sentiments]
            df[f'{col}_Color'] = [s['color'] for s in sentiments]

    return df

def main():
    st.title("Retrospective Sentiment Analysis")

    # File upload
    uploaded_file = st.file_uploader("Upload your retrospective Excel file", type=['xlsx'])

    if uploaded_file is not None:
        try:
            # Read Excel file
            df = pd.read_excel(uploaded_file, engine='openpyxl')

            # Analyze sentiments
            df = analyze_retrodata(df)

            # Filtering options
            st.subheader("Filter Options")
            col1, col2 = st.columns(2)

            with col1:
                sentiment_filter = st.multiselect(
                    "Filter by sentiment",
                    options=['very_negative', 'negative', 'neutral', 'positive', 'very_positive'],
                    default=[]
                )

            with col2:
                sort_by = st.selectbox(
                    "Sort by",
                    options=[col for col in df.columns if col.endswith('_Sentiment_Score')],
                    index=0
                )

            # Apply filters
            if sentiment_filter:
                filtered_df = df[
                    df['What Did Not Go Well?_Sentiment_Category'].isin(sentiment_filter) |
                    df['What Went Well?_Sentiment_Category'].isin(sentiment_filter) |
                    df['Reason for Churn_Sentiment_Category'].isin(sentiment_filter) |
                    df['Improvement opportunity_Sentiment_Category'].isin(sentiment_filter) |
                    df['Reason for reported success rate_Sentiment_Category'].isin(sentiment_filter)
                ]
            else:
                filtered_df = df

            # Sort dataframe
            filtered_df = filtered_df.sort_values(by=sort_by, ascending=False)

            # Display results
            st.subheader("Analysis Results")

            # Common columns to display on the left
            common_columns = ['issue_key', 'team_id', 'sprint', 'updated']

            # Get the corresponding text column for the sort_by column
            text_column = sort_by.replace("_Sentiment_Score", "")

            # Custom display function for the dataframe
            def format_row(row):
                formatted_row = {}
                # Add common columns
                for col in common_columns:
                    if col in row:
                        formatted_row[col] = row[col]
                
                # Add the text and score for the selected column
                if text_column in row and sort_by in row:
                    score_html = f'<span style="background-color: {row[sort_by.replace("_Sentiment_Score", "_Color")]}; color: black" class="sentiment-score">{row[sort_by]:.2f}</span>'
                    formatted_row[text_column] = row[text_column]
                    formatted_row[f'{text_column} Score'] = score_html
                
                return pd.Series(formatted_row)

            # Apply formatting to the dataframe
            display_df = filtered_df.apply(format_row, axis=1)
            
            # Display the formatted dataframe
            st.write(display_df.to_html(escape=False), unsafe_allow_html=True)

            # Display statistics
            st.subheader("Summary Statistics")
            col1, col2, col3 = st.columns(3)

            with col1:
                avg_sentiment = filtered_df[sort_by].mean() if sort_by in filtered_df.columns else "N/A"
                st.metric("Average Sentiment", f"{avg_sentiment:.2f}" if avg_sentiment != "N/A" else "N/A")

            with col2:
                most_common_sentiment = filtered_df[sort_by.replace("_Sentiment_Score", "_Sentiment_Category")].mode()[0] if sort_by.replace("_Sentiment_Score", "_Sentiment_Category") in filtered_df.columns else "N/A"
                st.metric("Most Common Sentiment", most_common_sentiment)

            with col3:
                st.metric("Total Rows", len(filtered_df))

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    main()
