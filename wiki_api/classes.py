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

    def __init__(self, page_title, request_size=1000):

        self.n_bins = 15
        self.edits_per_bin = 50
        self.vandalism_response_limit = 2
        self.vandalism_threshold = 2000
        self.vandalism_similarity = 0.95

        self.hist_color = 'lightcyan'
        self.edit_size_request = request_size

        self.title = page_title
        self.formatted_title = self._format_title()
        self.url = "https://en.wikipedia.org/w/index.php?title={0}&offset=&limit={1}&action=history".format(self.formatted_title, self.edit_size_request)
        self.response = self._simple_get()
        self.soup = BeautifulSoup(self.response, 'html.parser')
        self.raw_dates = []
        self.raw_edit_strs = []
        self.datetimes = []
        self.error_log = ErrorLog()
        self.dates = []
        self.bytes = []
        self.vandalism_flag = []
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

        for idx, child in enumerate(self.soup('li')):

            text = child.text

            if "curprev" in text:

                split_out = text.split("\u200e")
                datetime_str = split_out[0].split("curprev ")[-1] #21:44, 30 May 2020
                dt = datetime.datetime.strptime(datetime_str, "%H:%M, %d %B %Y")

                byte_str = split_out[2].split("bytes ")[-1]
                byte_str = byte_str.replace(",", "")
                try:
                    bytes = int(byte_str)

                    self.raw_dates.append(datetime_str)
                    self.raw_edit_strs.append(text)
                    self.datetimes.append(dt)
                    self.dates.append(dt)
                    self.bytes.append(bytes)
                    self.vandalism_flag.append(False)

                except ValueError:
                    self.error_log.add(idx, child, byte_str, datetime_str)
        #self.n_bins = int(len(self.bytes)/self.edits_per_bin)

    def _format_dates(self):
        self.dates = [datestr2num(rd) for rd in self.raw_dates]

    def _filter_data(self):

        self.otsu_thresh = 0.5*threshold_otsu(abs(np.array(self.bytes)))

        ii = 0
        while ii < len(self.bytes):
            if abs(self.bytes[ii]) > self.otsu_thresh:
                self.bytes.pop(ii)
                self.dates.pop(ii)
            else:
                ii += 1

    def _filter_vandalism(self):
        """
        doesn't work lol
        :return:
        """

        for ii in range(len(self.bytes)):
            if abs(self.bytes[ii]) > self.vandalism_threshold:

                while True:

                    offset = 1

                    if (ii + offset) < len(self.bytes):
                        date_diff = abs(self.dates[ii] - self.dates[ii+offset])
                        if abs((self.bytes[ii] - self.bytes[ii+offset])/self.bytes[ii]) < (1-self.vandalism_similarity):
                            self.vandalism_flag[ii] = True
                            self.vandalism_flag[ii+offset] = True
                            continue

                        if date_diff > self.vandalism_response_limit:
                            break

                    if (ii - offset) < len(self.bytes):
                        date_diff = abs(self.dates[ii] - self.dates[ii-offset])
                        if abs((self.bytes[ii] - self.bytes[ii-offset])/self.bytes[ii]) < (1-self.vandalism_similarity):
                            self.vandalism_flag[ii] = True
                            self.vandalism_flag[ii-offset] = True
                            continue

                        if date_diff > self.vandalism_response_limit:
                            break

                    offset += 1


    def _create_ticks(self):

        oldest_year = int(self.raw_dates[-1][-4:])
        recent_year = int(self.raw_dates[0][-4:])

        ticks = [datestr2num("01/01/{0}".format(Y)) for Y in range(oldest_year+1, recent_year+1)]
        labels = [str(Y) for Y in range(oldest_year+1, recent_year+1)]

        return ticks, labels

    def __repr__(self):
        return "{0}\ncaptured edits: {1}\nfiltered edits: {2}\notsu: {3}\nnewest edit: {4}\noldest edit: {5}".format(self.title,
                                                                                                                     len(self.bytes),
                                                                                                                     self.error_log.size(),
                                                                                                                     self.otsu_thresh,
                                                                                                                     self.raw_edit_strs[0],
                                                                                                                     self.raw_edit_strs[-1])

    def plot(self):

        color_list = ["r", "g"]
        plt.style.use('dark_background')
        fig0, ax0 = plt.subplots()
        for d, b in zip(self.dates, self.bytes):
            ax0.scatter(d, abs(b), c=color_list[b > 0], s=4, alpha=0.5)
        ax0.set_yscale('log')
        ticks, labels = self._create_ticks()
        ax0.set_xticks(ticks)
        ax0.set_xticklabels(labels, rotation=45)
        ax0.set_ylim(bottom=1)
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

class ErrorLog:

    def __init__(self):
        self.idxs = []
        self.children = []
        self.byte_strs = []
        self.datetimes = []

    def add(self, idx, child, byte_str, datetime):
        self.idxs.append(idx)
        self.children.append(child)
        self.byte_strs.append(byte_str)
        self.datetimes.append(datetime)

    def size(self):
        assert len(self.idxs)==len(self.children)==len(self.byte_strs)==len(self.datetimes), "ErrorLog lists are not the same length"
        return len(self.idxs)

