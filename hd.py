import requests
from bs4 import BeautifulSoup
import re
import subprocess
from urllib.parse import urljoin

def download_from_hdtoday(url, output_filename="video.mp4"):
    # Step 1: Get the page content
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    session = requests.Session()
    response = session.get(url, headers=headers)
    
    if response.status_code != 200:
        print("Failed to fetch the page")
        return
    
    # Step 2: Parse the page to find video sources
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Look for iframes or video tags (this will vary by site)
    iframe = soup.find('iframe')
    if iframe:
        iframe_src = iframe.get('src')
        if iframe_src:
            # Handle relative URLs
            iframe_url = urljoin(url, iframe_src)
            print(f"Found iframe: {iframe_url}")
            # You would need to repeat the process for the iframe content
    
    # Alternative: Look for video sources in script tags
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string:
            # Search for common video URL patterns
            matches = re.findall(r'(https?://[^\s]+\.(?:m3u8|mp4|mkv)[^\s"]*)', script.string)
            if matches:
                video_url = matches[0]
                print(f"Found video URL: {video_url}")
                
                # Step 3: Download the video
                try:
                    # Option 1: Using requests (for direct MP4 links)
                    if video_url.endswith('.mp4'):
                        print("Downloading MP4...")
                        video_response = session.get(video_url, headers=headers, stream=True)
                        with open(output_filename, 'wb') as f:
                            for chunk in video_response.iter_content(chunk_size=1024):
                                if chunk:
                                    f.write(chunk)
                        print("Download complete!")
                        return
                    
                    # Option 2: For HLS streams (.m3u8), use yt-dlp (recommended)
                    print("Downloading HLS stream...")
                    subprocess.run([
                        'yt-dlp',
                        '-o', output_filename,
                        video_url
                    ], check=True)
                    print("Download complete!")
                    return
                
                except Exception as e:
                    print(f"Download failed: {e}")
                    return
    
    print("No video source found on the page")

# Example usage
download_from_hdtoday("https://hdtoday.to/watch-movie/watch-pirates-of-the-caribbean-the-curse-of-the-black-pearl-hd-19756.1613490", "poc.mp4")