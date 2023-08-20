from google_play_scraper import app
import os
import requests


result = app(
    'org.govtech.CalSync',
    lang='en',  # defaults to 'en'
    country='us'  # defaults to 'us'
)


def download_image(url, filename):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            file.write(response.content)
        return True
    else:
        return False


output_folder = "scraper_output"

file_list = os.listdir(output_folder)
screenshot_count = 0
for filename in file_list:
    if filename.startswith("screenshot_"):
        try:
            number = int(filename.split("_")[1].split(".")[0])
            screenshot_count = max(screenshot_count, number)
        except ValueError:
            continue
print(screenshot_count)


for screenshot in result['screenshots']:
    screenshot_count += 1

    url = screenshot.strip()
    filename = os.path.join(
        output_folder, f"screenshot_{screenshot_count}.png")
    success = download_image(url, filename)
    if success:
        print(f"Downloaded {filename}")
    else:
        print(f"Failed to download {filename}")
