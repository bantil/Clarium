# config.py

# URL to scrape the Executive Orders from
URL = "https://www.whitehouse.gov/briefing-room/presidential-actions/"

# Define the output folder where CSV files will be stored
OUTPUT_FOLDER = "output"

# CSV file names (relative to the OUTPUT_FOLDER)
EO_CSV_FILENAME = "executive_orders.csv"    # Basic EO details
ANALYSIS_CSV_FILENAME = "analysis.csv"        # Full analysis (markdown formatted)
XPOSTS_CSV_FILENAME = "x_posts.csv"           # Social media posts (markdown formatted)
