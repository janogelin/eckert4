import requests
from bs4 import BeautifulSoup

# Fetch the page
url = "https://www.cnn.com"
headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers)
response.raise_for_status()  # Raise error if request failed

# Parse the HTML
soup = BeautifulSoup(response.text, 'html.parser')

# Find and print all anchor text
for a in soup.find_all('a'):
    text = a.get_text(strip=True)
    if text:  # Skip empty links
        print(text)
