from playwright.sync_api import sync_playwright, Playwright
#from bs4 import BeautifulSoup
#from rich import print
import re, ffmpeg, os, shutil, subprocess
from moviepy import VideoFileClip

def get_video_duration(filepath):
    clip = VideoFileClip(filepath)
    duration = clip.duration  # Duration in seconds
    clip.close()
    return duration

filepath = r"D:\Midlertidig film folder\The Texas Chainsaw Massacre 2 [1986]\Alternate Opening Sequence.mkv"
duration = get_video_duration(filepath)
print(f"Duration: {duration:.2f} seconds")

publisher = "arrow"
movie = 'The Texas Chainsaw Massacre 2 [1986]'
file_folder = 'D:\\Midlertidig film folder\\' + movie
format_disc = ""

def get_format(format_disc):
    format_map = {
        "dvd": "^(?!.*Blu-ray).*",  # filtrerer ut blu-ray links
        "blu_ray": r"\(Blu-ray\)",
        "blu_ray_4k": r"\(Blu-ray 4K\)",
    }
    
    return format_map.get(format_disc, r"\(Blu-ray\)") #defaulter til Blu-ray

def get_title_year(movie):

    yearRegex = re.compile(r'\[(\d{4})\]$')
    mo = yearRegex.search(movie)
    year = mo.group(1) if mo else None
    print(year)
    title = re.sub(yearRegex, '', movie).removeprefix('The ').removeprefix('A ').strip()
    print(title)
    
    return [title, year]

def convert_to_seconds(time):
    minutes, seconds = map(int, time.split(':'))
    return minutes * 60 + seconds

def video_renamer(file_folder, extras, t_rex):
    for moviefile in os.listdir(file_folder):
        print(os.path.join(file_folder, moviefile))
        try:
            duration = ffmpeg.probe(os.path.join(file_folder, moviefile))["format"]["duration"] # funker ikke med absolute path??
            print(duration)
        except ffmpeg.Error as e:
            print(f'Error probing file {moviefile}: {e}')
        #for ex in extras:
            
        
        
#duration = ffmpeg.probe(local_file_path)["format"]["duration"] # kode fra stackoverflow for å hente lengde til fil

def get_search_url(title, year):
    return f"https://www.dvdcompare.net/comparisons/adv_search_results.php?title_search={title}&year_search={year}&and_or=and" 

def run(playwright: Playwright):
    
    
    movie_title, movie_year = get_title_year(movie)
    print(movie_title + ' ' + movie_year)
    format_regex = get_format(format_disc)
    # negative lookahead funker ikke om den delen av regexen ikke er først(??)
    regex_filter = f"{format_regex}.*{movie_title}.*" if format_disc == "dvd" else f"{movie_title}.*{format_regex}"
    print(regex_filter)
    #{movie_title}.*{format_string}
    
    search_url = get_search_url(movie_title, movie_year)
    chrome = playwright.chromium
    browser = chrome.launch()
    page = browser.new_page()
    page.goto(search_url)
    
    # finner rett link basert på disk-formatet,
    # målet med advanced search er at det kun er maks 3 linker å velge mellom
    # men inkluderer filmens navn i filteringen uansett
    page.get_by_role("link").filter(has_text=re.compile(regex_filter, re.IGNORECASE)).click()
    # page.wait_for_navigation() dette funker ikke, kanskje bare for async?
    page.wait_for_load_state() #dette funket bedre, og var dypt nødvendig

    # finne rett table så jeg ikke scraper dvdcompare logoen
    table = page.locator("#content div table")
    
    # filtrere ut alle releases som ikke er av rett utgiver, altså finne din spesifikke disk-utgivelse
    releases = table.get_by_role("row").filter(has=page.get_by_role("heading").filter(has_text=f"{publisher}"))
    
    # finne Extras elementet
    extraEls = releases.get_by_role("listitem").filter(has=page.locator("div.label").filter(has_text="Extras:"))

    extras = []
    
    for extraEl in extraEls.all():
        extras.extend([line.strip() for line in extraEl.text_content().splitlines()])

    time_regex = re.compile(r'\((\d{1,2}:\d{2})\)$')
    timed_extras = [ex for ex in extras if time_regex.findall(ex)]
    
    #for ex in extras:
       # print(ex + ": " + str(type(ex)))
        
    print(timed_extras)
    #for row in table.get_by_role("row").all():
       # print("yeah boii")
       # print(row.text_content())

    video_renamer(file_folder, timed_extras, time_regex)
    
with sync_playwright() as playwright:
    run(playwright)


# MAL FOR URL:
# https://www.dvdcompare.net/comparisons/adv_search_results.php?title_search=texas%+chainsaw&year_search=1986&and_or=and
