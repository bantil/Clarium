import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import hashlib
import openai  # For GPT‑4 API calls

# Try to load configuration settings from config.py, else use defaults.
try:
    from config import URL, OUTPUT_FOLDER, EO_CSV_FILENAME, ANALYSIS_CSV_FILENAME, XPOSTS_CSV_FILENAME
except ImportError:
    URL = "https://www.whitehouse.gov/briefing-room/presidential-actions/"
    OUTPUT_FOLDER = "output"
    EO_CSV_FILENAME = "executive_orders.csv"
    ANALYSIS_CSV_FILENAME = "analysis.csv"
    XPOSTS_CSV_FILENAME = "x_posts.csv"

# Create the output folder if it doesn't exist.
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Build full file paths using the output folder and filenames.
EO_CSV_FILE = os.path.join(OUTPUT_FOLDER, EO_CSV_FILENAME)
ANALYSIS_FILE = os.path.join(OUTPUT_FOLDER, ANALYSIS_CSV_FILENAME)
XPOSTS_FILE = os.path.join(OUTPUT_FOLDER, XPOSTS_CSV_FILENAME)

# Function to load a prompt from a file
def load_prompt(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

# Load prompts from external files in the 'prompts' folder.
FULL_ANALYSIS_PROMPT = load_prompt(os.path.join("prompts", "full_analysis_prompt.txt"))
X_POSTS_PROMPT = load_prompt(os.path.join("prompts", "x_posts_prompt.txt"))

def generate_id(title, link):
    """
    Generate a unique alphanumeric identifier using the title and link.
    """
    unique_string = title + link
    return hashlib.md5(unique_string.encode()).hexdigest()[:10]

def scrape_executive_orders(limit=1):
    """
    Scrapes the latest executive orders from the specified URL.
    """
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

def load_existing_orders():
    """
    Loads the IDs of existing executive orders from the CSV.
    """
    if os.path.exists(EO_CSV_FILE):
        return pd.read_csv(EO_CSV_FILE)["ID"].tolist()
    return []

def save_executive_orders_to_csv(eos):
    """
    Saves the basic executive order details (without analysis or X posts) to a CSV file.
    """
    df_new = pd.DataFrame(eos)[["ID", "Title", "Date", "Link"]]
    if os.path.exists(EO_CSV_FILE):
        df_existing = pd.read_csv(EO_CSV_FILE)
        df_combined = pd.concat([df_existing, df_new]).drop_duplicates(subset=["ID"], keep="last")
        df_combined.to_csv(EO_CSV_FILE, index=False)
    else:
        df_new.to_csv(EO_CSV_FILE, index=False)
    print(f"[{datetime.now()}] Saved {len(df_new)} new Executive Orders to CSV.")

def save_analysis_to_csv(analysis_records):
    """
    Saves the full analysis for each EO to a separate CSV file.
    Each record contains the unique ID and its analysis (with markdown formatting).
    """
    df_new = pd.DataFrame(analysis_records)  # Expected keys: "ID", "Analysis"
    if os.path.exists(ANALYSIS_FILE):
        df_existing = pd.read_csv(ANALYSIS_FILE)
        df_combined = pd.concat([df_existing, df_new]).drop_duplicates(subset=["ID"], keep="last")
        df_combined.to_csv(ANALYSIS_FILE, index=False)
    else:
        df_new.to_csv(ANALYSIS_FILE, index=False)
    print(f"[{datetime.now()}] Saved {len(df_new)} analysis records to CSV.")

def save_x_posts_to_csv(x_posts_records):
    """
    Saves the X posts to a separate CSV file.
    Each record contains the EO unique ID and one X post (with markdown formatting).
    """
    df_new = pd.DataFrame(x_posts_records)  # Expected keys: "ID", "X_Post"
    if os.path.exists(XPOSTS_FILE):
        df_existing = pd.read_csv(XPOSTS_FILE)
        df_combined = pd.concat([df_existing, df_new]).drop_duplicates(subset=["ID", "X_Post"], keep="last")
        df_combined.to_csv(XPOSTS_FILE, index=False)
    else:
        df_new.to_csv(XPOSTS_FILE, index=False)
    print(f"[{datetime.now()}] Saved {len(df_new)} new X posts to CSV.")

def fetch_eo_content(link):
    """
    Fetches the content from a given URL and extracts text from the
    <div> element with the class 'entry-content'.
    """
    try:
        response = requests.get(link)
        if response.status_code != 200:
            print(f"[{datetime.now()}] Error fetching content from {link}. Status Code: {response.status_code}")
            return ""
        soup = BeautifulSoup(response.text, 'html.parser')
        content_div = soup.find("div", class_="entry-content")
        if content_div:
            return content_div.get_text(separator="\n", strip=True)
        else:
            print(f"[{datetime.now()}] 'entry-content' div was not found on {link}.")
            return ""
    except Exception as e:
        print(f"[{datetime.now()}] An error occurred: {e}")
        return ""

def generate_full_analysis(eo_text, prompt):
    """
    Calls GPT‑4 with the provided text and prompt to generate a full analysis.
    """
    messages = [
        {"role": "system", "content": "You are a highly specialized government policy analyst AI with expertise in analyzing U.S. executive orders and legislation."},
        {"role": "user", "content": f"{prompt}\n\n{eo_text}"}
    ]
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=800  # Adjust as needed
        )
        output = response.choices[0].message.content.strip()
        return output
    except Exception as e:
        print(f"[{datetime.now()}] Error calling GPT-4 for full analysis: {e}")
        return None

def generate_x_posts(eo_text, prompt):
    """
    Calls GPT‑4 with the provided text and prompt to generate X posts.
    """
    messages = [
        {"role": "system", "content": "You are a policy communications AI focused on creating neutral, factual, and engaging social media posts summarizing executive orders and legislation."},
        {"role": "user", "content": f"{prompt}\n\n{eo_text}"}
    ]
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=300  # Adjust as needed
        )
        output = response.choices[0].message.content.strip()
        return output
    except Exception as e:
        print(f"[{datetime.now()}] Error calling GPT-4 for X posts: {e}")
        return None

def parse_x_posts(x_posts_text):
    """
    Parses the GPT‑4 response for X posts into a list of individual posts.
    Assumes the response is a markdown bullet list.
    Each bullet point starts with a dash followed by a space.
    """
    posts = []
    for line in x_posts_text.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            post = line[2:].strip()
            posts.append(post)
    return posts

if __name__ == "__main__":
    print(f"[{datetime.now()}] Executing the scraper script...")
    existing_orders = load_existing_orders()
    executive_orders = scrape_executive_orders()

    # Process only new executive orders (those not already saved)
    new_orders = [eo for eo in executive_orders if eo["ID"] not in existing_orders]

    analysis_records = []   # List of dicts: {"ID": ..., "Analysis": ...}
    x_posts_records = []    # List of dicts: {"ID": ..., "X_Post": ...}

    for eo in new_orders:
        print(f"[{datetime.now()}] Fetching content for EO: {eo['Title']}")
        eo_text = fetch_eo_content(eo["Link"])
        if not eo_text:
            print(f"[{datetime.now()}] No content found for {eo['Title']}. Skipping GPT-4 processing.")
            continue

        print(f"[{datetime.now()}] Generating full analysis for EO: {eo['Title']}")
        full_analysis = generate_full_analysis(eo_text, FULL_ANALYSIS_PROMPT)
        if full_analysis:
            analysis_records.append({"ID": eo["ID"], "Analysis": full_analysis})
            print(f"[{datetime.now()}] Full analysis generated for {eo['Title']}")
        else:
            print(f"[{datetime.now()}] Full analysis generation failed for {eo['Title']}")

        print(f"[{datetime.now()}] Generating X posts for EO: {eo['Title']}")
        x_posts_text = generate_x_posts(eo_text, X_POSTS_PROMPT)
        if x_posts_text:
            posts = parse_x_posts(x_posts_text)
            for post in posts:
                x_posts_records.append({"ID": eo["ID"], "X_Post": post})
            print(f"[{datetime.now()}] X posts generated for {eo['Title']}")
        else:
            print(f"[{datetime.now()}] X posts generation failed for {eo['Title']}")

    if new_orders:
        save_executive_orders_to_csv(new_orders)
        if analysis_records:
            save_analysis_to_csv(analysis_records)
        if x_posts_records:
            save_x_posts_to_csv(x_posts_records)
        print(f"[{datetime.now()}] Successfully processed new Executive Orders.")
        for eo in new_orders:
            print(f"[{datetime.now()}] New EO: {eo['Title']} - ID: {eo['ID']}")
    else:
        print(f"[{datetime.now()}] No new Executive Orders found.")
