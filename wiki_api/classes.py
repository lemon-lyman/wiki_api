import requests
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from matplotlib.dates import datestr2num
import numpy as np
from skimage.filters import threshold_otsu
import datetime
import time


class Getter:

    def __init__(self, page_title):

        self.n_bins = 25
        self.hist_color = 'lightcyan'
        self.edit_size_request = 800

        self.title = page_title
        self.formatted_title = self._format_title()
        self.url = "https://en.wikipedia.org/w/index.php?title={0}&offset=&limit={1}&action=history".format(self.formatted_title, self.edit_size_request)
        self.response = self._simple_get()
        self.soup = BeautifulSoup(self.response, 'html.parser')
        self.raw_dates = []
        self.datetimes = []
        self.dates = []
        self.bytes = []
        self._parse_soup()
        self._format_dates()
        self._filter_data()

    def _format_title(self):
        return self.title.replace(" ", "_")

    def _simple_get(self):
        
        """
        Simple but robust url get. Copied from some stack overflow. Unfortunately, link lost.
        :param url:
        :return:
        """

        start_time = time.time()
        try:
            with closing(get(self.url, stream=True)) as resp:
                if self._is_good_response(resp):
                    print("Return time: ", time.time() - start_time)
                    return resp.content
                else:
                    print("Return time: ", time.time() - start_time)
                    return None

        except RequestException as e:
            log_error('Error during requests to {0} : {1}'.format(self.url, str(e)))
            return None

    def _is_good_response(self, resp):

        content_type = resp.headers['Content-Type'].lower()
        return (resp.status_code == 200
                and content_type is not None
                and content_type.find('html') > -1)

    def _parse_soup(self):

        count = 0
        for idx, child in enumerate(self.soup('li')):

            text = child.text

            if "curprev" in text:

                split_out = text.split("\u200e")
                datetime_str = split_out[0].split("curprev ")[-1] #21:44, 30 May 2020
                dt = datetime.datetime.strptime(datetime_str, "%H:%M, %d %B %Y")

                byte_str = split_out[2].split("bytes ")[-1]
                byte_str = byte_str.replace(",", "")
                bytes = int(byte_str)

                self.raw_dates.append(datetime_str)
                self.datetimes.append(dt)
                self.dates.append(dt)
                self.bytes.append(bytes)

        print("count: ", count)

    def _format_dates(self):
        self.dates = [datestr2num(rd) for rd in self.raw_dates]

    def _filter_data(self):

        self.otsu_thresh = threshold_otsu(abs(np.array(self.bytes)))

        ii = 0
        while ii < len(self.bytes):
            if abs(self.bytes[ii]) > self.otsu_thresh:
                self.bytes.pop(ii)
                self.dates.pop(ii)
            else:
                ii += 1

    def _create_ticks(self):

        oldest_year = int(self.raw_dates[-1][-4:])
        recent_year = int(self.raw_dates[0][-4:])

        ticks = [datestr2num("01/01/{0}".format(Y)) for Y in range(oldest_year+1, recent_year+1)]
        labels = [str(Y) for Y in range(oldest_year+1, recent_year+1)]

        return ticks, labels

    def __repr__(self):
        return "{0}\nmean bytes: {1}\nstd bytes: {2}".format(self.title,
                                                             np.mean(self.bytes),
                                                             np.std(self.bytes))

    def plot(self):

        color_list = ["r", "g"]
        plt.style.use('dark_background')
        fig0, ax0 = plt.subplots()
        for d, b in zip(self.dates, self.bytes):
            ax0.scatter(d, abs(b), c=color_list[b > 0], s=4)
        ticks, labels = self._create_ticks()
        ax0.set_xticks(ticks)
        ax0.set_xticklabels(labels)
        ax0.set_ylim(bottom=0)
        ax0.set_ylabel("Edit Size (bytes)")
        ax0.set_title(self.title)

        ax1 = ax0.twinx()
        ax1.hist(self.dates,
                 bins=np.linspace(min(self.dates),
                                  max(self.dates),
                                  self.n_bins),
                 zorder=-1,
                 alpha=0.2,
                 color=self.hist_color)
        ax1.tick_params(labelcolor=self.hist_color)
        ax1.set_ylabel("Frequency of Edits")
        plt.show()
