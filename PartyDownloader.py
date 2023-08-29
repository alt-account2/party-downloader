import requests
import time
from tqdm import tqdm
import os
from bs4 import BeautifulSoup
import concurrent.futures
from urllib.parse import urlparse


class PartyDownloader:
    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/87.0.4280.88 Safari/537.36"
            }
        )
        self._max_workers: int = 5  # Adjust this value as needed
        self._request_delay: float = .5  # Adjust this value as needed
        self._number_of_pages: int = 0
        self._links: list = []
        self._base_url: str = ""
        self._model: str = ""

    def _get_number_of_pages(self):
        errs: int = 0
        self._number_of_pages = 0
        while True:
            try:
                random_page = self._session.get(self._base_url)
                if random_page.status_code != 200:
                    raise Exception("Status code is not 200")
                random_page = BeautifulSoup(random_page.text, 'html.parser')
                if random_page.find("menu") is None:
                    self._number_of_pages = 1
                else:
                    self._number_of_pages = int(
                        random_page.find("menu").find_all("a")[-1].get("href").split("=")[1]) // 50 + 1
                break
            except:
                errs += 1
                if errs > 2:
                    print("Error getting number of pages")
                    break
                time.sleep(1)

    def _get_coomer_links(self):
        links = []
        progress_bar = tqdm(total=self._number_of_pages, unit="page")

        def process_page(i):
            url = self._base_url + f"?o={i}"
            try:
                soup = BeautifulSoup(self._session.get(url, timeout=15).text, 'html.parser')
                page_links = []
                for art in soup.find_all("article"):
                    post_url = self._base_url + "/post/" + art.find("a").get("href").split("post/")[1]
                    post_soup = BeautifulSoup(self._session.get(post_url, timeout=15).text, 'html.parser')
                    for a in post_soup.find_all("a", {"class": "fileThumb"}):
                        page_links.append(a.get("href"))
                    for a in post_soup.find_all("a", {"class": "post__attachment-link"}):
                        page_links.append(a.get("href"))
                    time.sleep(.1)
                return page_links
            except requests.RequestException:
                return []

        # Process pages and gather links
        with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = []
            for i in range(0, self._number_of_pages * 50, 50):
                future = executor.submit(process_page, i)
                futures.append(future)
            for future in concurrent.futures.as_completed(futures):
                links.extend(future.result())
                time.sleep(self._request_delay)
                progress_bar.update(1)

        links = [urlparse(l) for l in links]
        # if coomer.party.txt exists, check if the links are already there
        if os.path.exists(f"{self._model}/coomer.party.txt"):
            with open(f"{self._model}/coomer.party.txt", "r") as f:
                old_links = f.read().split("\n")
            old_links = [urlparse(l) for l in old_links]
            links = list(set(links + old_links))
        with open(f"{self._model}/coomer.party.txt", "w") as f:
            f.write("\n".join([l.geturl() for l in links]))

        self._links = links

    def _download_links(self, times=0):
        failed = []

        def download_link(link, ts=0):
            try:
                response = self._session.get(link.geturl())
                response.raise_for_status()
                return link, response.content
            except requests.RequestException as e:
                # tqdm.write(f"Failed to download {link} due to {e}")
                # print the error message and return None
                if ts < 1:
                    time.sleep(self._request_delay)
                    return download_link(link, ts + 1)
                return link, None

        def update_progress_bar(future):
            link, content = future.result()
            if content is None:
                failed.append(link)
            progress_bar.update(1)

        # Filter out links that have already been downloaded
        download_queue = []
        for link in self._links:
            name = os.path.join(self._model, link.path.split("/")[-1])
            if not os.path.exists(name):
                download_queue.append(link)
        links = download_queue

        progress_bar = tqdm(total=len(links), desc="Downloading files", unit="files", position=0)
        with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_link = {executor.submit(download_link, link, 0): link for link in links}
            for future in concurrent.futures.as_completed(future_to_link):
                link, content = future.result()
                if content is not None:
                    name = os.path.join(self._model, link.path.split("/")[-1])
                    with open(name, 'wb') as f:
                        f.write(content)
                update_progress_bar(future)
                time.sleep(self._request_delay)

        if len(failed) > 0:
            if times < 1:
                print("Retrying failed downloads")
                return self._download_links(times + 1)
            tqdm.write(f"Failed to download {len(failed)} files")
            with open(f"{self._model}/coomer.party.failed.txt", "w") as f:
                f.write("\n".join([l.geturl() for l in failed]))

    def download_coomer_files(self, model, *, full_path=None):
        print(f"Downloading {model}")
        self._model = model

        if full_path is not None:
            if model is None:
                raise Exception("You need to specify model if you specify full_path")
            self._base_url = full_path
        else:
            self._base_url = f"https://coomer.party/onlyfans/user/{model}"

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
            }
        )

        self._get_number_of_pages()
        self._get_coomer_links()
        self._download_links()


model = "bustanutters"
# create folder if it doesn't exist (use the oneliner)
os.makedirs(model, exist_ok=True)
party_downloader = PartyDownloader()
party_downloader.download_coomer_files(model)
