from playwright.sync_api import sync_playwright, Playwright, TimeoutError
#from bs4 import BeautifulSoup
#from rich import print
import re, ffmpeg, os, shutil, subprocess
from moviepy import VideoFileClip

def get_video_duration(filepath):
    clip = VideoFileClip(filepath)
    duration = clip.duration  # Trenger kanskje ikke denne da ffmpeg probe funker plutselig??
    clip.close()
    return duration

filepath = r"D:\Midlertidig film folder\The Texas Chainsaw Massacre 2 [1986]\Alternate Opening Sequence.mkv"
duration = get_video_duration(filepath)
print(f"Duration: {duration:.2f} seconds")

publisher = "arrow"
movie = 'texas chainsaw massacre 2 [1986]'
file_folder = 'D:\\Midlertidig film folder\\' + movie
format_disc = ""

def get_format(format_disc):
    format_map = {
        "dvd": re.compile(r"^(?!.*Blu-ray).*", re.I),  # filtrerer ut blu-ray links
        "blu_ray": re.compile(r"\(Blu-ray\)", re.I),
        "blu_ray_4k": re.compile(r"\(Blu-ray 4K\)", re.I),
    }
    
    return format_map.get(format_disc, re.compile(r"\(Blu-ray\)")) #defaulter til Blu-ray

def get_title_year(movie):

    yearRegex = re.compile(r'\[(\d{4})\]$')
    mo = yearRegex.search(movie) # mo = match object
    year = mo.group(1) if mo else None
    print(year)
    title = re.sub(yearRegex, '', movie).removeprefix('The ').removeprefix('A ').strip()
    #title_regex = re.compile(r'(?:\bAKA\b\s*)?(\b' + re.escape(title) + r'\b)(?:\s*\bAKA\b)?(?:\s*\((?:The|A)\))?'
    print(title)
    title_regex = re.compile(r'(\bAKA\b\s\b'
                             + title
                             + r'\b\s(?:\(.*\)\s)?\bAKA\b\s.*?|^\b'
                             + title
                             + r'\b\s(?:\(.*\)\s)?\bAKA\b\s.*?|\bAKA\b\s\b'
                             + title + r'\b\s(?:\(.*\)\s)?)'
                             + r'^\b' + title + r'\b\s(?:\(.*\)\s)?', re.I)
    return [title, title_regex, year]


def convert_to_seconds(time):
    minutes, seconds = map(int, time.split(':'))
    return minutes * 60 + seconds

def video_renamer(file_folder, extras, t_rex):
    for moviefile in os.listdir(file_folder):
        print(os.path.join(file_folder, moviefile))
        try:
            # Dette bestemte seg randomly for å funke allikevel????? Men whatever, bruker heller moviepy
            #duration = ffmpeg.probe(os.path.join(file_folder, moviefile), loglevel='quiet')["format"]["duration"]
            duration = get_video_duration(os.path.join(file_folder, moviefile))
            print(duration)
        except ffmpeg.Error as e:
            print(f'Error probing file {moviefile}: {e}')
        #for ex in extras:
                
        
        
#duration = ffmpeg.probe(local_file_path)["format"]["duration"] # kode fra stackoverflow for å hente lengde til fil

def get_search_url(title, year):
    return f"https://www.dvdcompare.net/comparisons/adv_search_results.php?title_search={title}&year_search={year}&and_or=and" 

def run(playwright: Playwright):
    
    
    movie_title, title_regex, movie_year = get_title_year(movie)
    print(str(movie_title) + ' ' + movie_year)
    format_regex = get_format(format_disc)
    # negative lookahead funker ikke om den delen av regexen ikke er først(??)
    #regex_filter = f"{format_regex}.*{movie_title}.*" if format_disc == "dvd" else f"{movie_title}.*{format_regex}"
    #print(regex_filter)
    #{movie_title}.*{format_string}
    
    search_url = get_search_url(movie_title, movie_year)
    chrome = playwright.chromium
    browser = chrome.launch()
    page = browser.new_page()
    page.goto(search_url)
    print(page.url)
    try:
        if page.is_visible('.fc-consent-root'):
            print('dum overlay')
            page.evaluate("document.querySelector('.fc-consent-root').remove();")
            page.wait_for_selector('.fc-consent-root', state='detached', timeout=5000)
            print('fjernet overlay root')
    except TimeoutError:
        print('ingen overlay???') # fjerner mystisk overlay som gaslighter meg
    # finner rett link basert på disk-formatet,
    # målet med advanced search er at det kun er maks 3 linker å velge mellom
    # men inkluderer filmens navn i filteringen uansett
    # nvm jeg er dum
    links = page.get_by_role("link")
    for i in range(links.count()):
        link = links.nth(i)
        print(link.inner_text())
        if format_regex.search(link.inner_text()):
            print('fant format')
            print(link.inner_text())
            print('leter etter ' + str(title_regex))
            if title_regex.search(link.inner_text()):
                print('klikker link')
                link.click()
                break
    #page.get_by_role("link").filter(has_text=format_regex).filter(has_text=title_regex).click()
    print(page.url)
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

    time_regex = re.compile(r'\((\d{1,2}:\d{2}).*?\):?')
    timed_extras = [ex for ex in extras if time_regex.findall(ex)]
    
    #for ex in extras:
       # print(ex + ": " + str(type(ex)))
        
    print(timed_extras)
    #for row in table.get_by_role("row").all():
       # print("yeah boii")
       # print(row.text_content())
    # nope ny plan for hele denne greia:
    #extras_regex = re.compile(
    #r'^\s*[-•*–]?\s*'  # sjekker om det er sånn listetegn
    #r'(?:"([^"]*)"\s*)?'  # tittel i hermetegn om det er der
    #r'((?:.(?!\b\d{4}\b))*)' #Ekstra info
    #r'(?:\s*.*?(\d{4}).*?\s*)?'  # årstall om oppgitt NB må finpusses
    #r'(?:(.*?)\s*)?'  # Ekstra info NB får bare med info fra før årstall
    #r'\s*\((\d{1,2}:\d{2}).*?\)'  # Lengde på klipp
    #)

    year_regex = re.compile(r'\b\d{4}\b')
    quoted_text_regex = re.compile(r'"([^"]+)"')

    
    for ex in timed_extras:
        #mo = extras_regex.search(ex)
        #print("Grupper:", mo.groups() if mo else "Ingen match")
        title = quoted_text_regex.search(ex)
        year = year_regex.search(ex)
        time = time_regex.search(ex)
        remaining_text = ex
        print_list = [ex]
        if title:
            title_text = title.group(1)
            print_list.append(title_text)
            remaining_text = remaining_text.replace(title.group(0), '').strip()
        if year:
            year_text = year.group(0)
            print_list.append(year_text)
            remaining_text = remaining_text.replace(year.group(0), '').strip()
        if time:
            time_text = time.group(1)
            print_list.append(time_text)
            remaining_text = remaining_text.replace(time.group(0), '').strip()
        remaining_text = re.sub(r'\s+', ' ', remaining_text).strip()
        print_list.append(remaining_text)
        print(print_list)

    #video_renamer(file_folder, timed_extras, time_regex)
    
with sync_playwright() as playwright:
    run(playwright)


# MAL FOR URL:
# https://www.dvdcompare.net/comparisons/adv_search_results.php?title_search=texas%+chainsaw&year_search=1986&and_or=and
