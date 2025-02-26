import requests  # Library for making HTTP requests to web pages
from bs4 import BeautifulSoup  # Library for parsing HTML content and extracting data
import pandas as pd  # Library for handling structured data (not used yet but useful for storing results)
import schedule  # Library for scheduling tasks to run at specific intervals
import time  # Library for adding delays (if needed)
from datetime import datetime  # Library for timestamping logs
import os  # Library for checking if a file exists
import hashlib  # Library for generating unique identifiers

# URL of the White House Executive Orders page
URL = "https://www.whitehouse.gov/briefing-room/presidential-actions/"

# CSV files to store executive orders and tweets
CSV_FILE = "executive_orders.csv"
TWEET_FILE = "tweets.csv"

# Function to generate a unique alphanumeric identifier
def generate_id(title, link):
    unique_string = title + link
    return hashlib.md5(unique_string.encode()).hexdigest()[:10]  # Shorten to 10 characters

# Function to scrape the latest Executive Orders
def scrape_executive_orders(limit=5):
    print(f"[{datetime.now()}] Starting to scrape Executive Orders...")
    response = requests.get(URL)
    if response.status_code != 200:
        print(f"[{datetime.now()}] Failed to retrieve the page. Status Code: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("li", class_="wp-block-post")
    print(f"[{datetime.now()}] Found {len(articles)} articles on the page.")

    executive_orders = []
    for idx, article in enumerate(articles[:limit]):
        print(f"[{datetime.now()}] Processing article {idx + 1}...")
        title_tag = article.find("h2", class_="wp-block-post-title")
        title = title_tag.get_text(strip=True) if title_tag else "No title found"
        link_tag = title_tag.find("a") if title_tag else None
        link = link_tag["href"] if link_tag else "No link found"
        date_tag = article.find("time")
        date = date_tag.get_text(strip=True) if date_tag else "No date available"
        unique_id = generate_id(title, link)

        print(f"[{datetime.now()}] Extracted EO: {title} ({date}) - {link} - ID: {unique_id}")

        executive_orders.append({
            "ID": unique_id,
            "Title": title,
            "Date": date,
            "Link": link
        })

    print(f"[{datetime.now()}] Finished scraping executive orders.")
    return executive_orders

# Function to load existing executive orders from CSV
def load_existing_orders():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)["ID"].tolist()
    return []

# Function to save executive orders to a CSV file
def save_to_csv(executive_orders):
    df_new = pd.DataFrame(executive_orders)
    if os.path.exists(CSV_FILE):
        df_existing = pd.read_csv(CSV_FILE)
        df_combined = pd.concat([df_existing, df_new]).drop_duplicates(subset=["ID"], keep="last")
        df_combined.to_csv(CSV_FILE, index=False)
    else:
        df_new.to_csv(CSV_FILE, index=False)
    print(f"[{datetime.now()}] Saved {len(df_new)} new Executive Orders to CSV.")

# Function to save tweets to a separate CSV file
def save_tweets_to_csv(executive_orders):
    tweets = [{"ID": eo["ID"], "Tweet": f"New Executive Order: {eo['Title']} - {eo['Link']}"} for eo in executive_orders]
    df_tweets = pd.DataFrame(tweets)

    if os.path.exists(TWEET_FILE):
        df_existing_tweets = pd.read_csv(TWEET_FILE)
        df_combined_tweets = pd.concat([df_existing_tweets, df_tweets]).drop_duplicates(subset=["ID"], keep="last")
        df_combined_tweets.to_csv(TWEET_FILE, index=False)
    else:
        df_tweets.to_csv(TWEET_FILE, index=False)
    print(f"[{datetime.now()}] Saved {len(df_tweets)} new tweets to CSV.")

# Running the scraper
if __name__ == "__main__":
    print(f"[{datetime.now()}] Executing the scraper script...")
    existing_orders = load_existing_orders()
    executive_orders = scrape_executive_orders()

    new_orders = [eo for eo in executive_orders if eo["ID"] not in existing_orders]

    if new_orders:
        save_to_csv(new_orders)
        save_tweets_to_csv(new_orders)
        print(f"[{datetime.now()}] Successfully retrieved new Executive Orders.")
        for eo in new_orders:
            print(f"[{datetime.now()}] New EO: {eo['Title']} - {eo['Link']} - ID: {eo['ID']}")
    else:
        print(f"[{datetime.now()}] No new Executive Orders found.")
