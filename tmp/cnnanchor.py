import requests
from bs4 import BeautifulSoup

# Fetch the page
url = "https://www.cnn.com"
headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers)
response.raise_for_status()

# Parse the HTML
soup = BeautifulSoup(response.text, 'html.parser')

# Extract and print all href values
for a in soup.find_all('a', href=True):
    href = a['href']
    print(href)
