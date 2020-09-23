from copy import deepcopy
from io import StringIO
from lxml import etree

from bases.FrameworkServices.UrlService import UrlService

priority = 90000

update_every = 15

CHARTS = {
    'downstream_frequency': {
        'options': [None, 'Frequency', 'mHz', 'Downstream', 'arris_surfboard.downstream_frequency', 'line'],
        'lines': [
            ['downstream_{n}_frequency', '{n}', 'absolute', 1, 100],
        ],
    },
    'downstream_power': {
        'options': [None, 'Power', 'dBmV', 'Downstream', 'arris_surfboard.downstream_power', 'line'],
        'lines': [
            ['downstream_{n}_power', '{n}', 'absolute', 1, 100],
        ],
    },
    'downstream_signal_to_noise': {
        'options': [None, 'Signal to Noise', 'dB', 'Downstream', 'arris_surfboard.downstream_signal_to_noise', 'line'],
        'lines': [
            ['downstream_{n}_signal_to_noise', '{n}', 'absolute', 1, 10000],
        ],
    },
    'downstream_corrected_errors': {
        'options': [None, 'Corrected Errors', 'correcteds', 'Downstream', 'arris_surfboard.downstream_corrected_errors', 'line'],
        'lines': [
            ['downstream_{n}_corrected_errors', '{n}', 'incremental'],
        ],
    },
    'downstream_uncorrected_errors': {
        'options': [None, 'Uncorrected Errors', 'uncorrectables', 'Downstream', 'arris_surfboard.downstream_uncorrected_errors', 'line'],
        'lines': [
            ['downstream_{n}_uncorrected_errors', '{n}', 'incremental'],
        ],
    },
    'upstream_frequency': {
        'options': [None, 'Frequency', 'mHz', 'Upstream', 'arris_surfboard.upstream_frequency', 'line'],
        'lines': [
            ['upstream_{n}_frequency', '{n}', 'absolute', 1, 100],
        ],
    },
    'upstream_width': {
        'options': [None, 'Width', 'mHz', 'Upstream', 'arris_surfboard.upstream_width', 'line'],
        'lines': [
            ['upstream_{n}_width', '{n}', 'absolute', 1, 100],
        ],
    },
    'upstream_power': {
        'options': [None, 'Power', 'dBmV', 'Upstream', 'arris_surfboard.upstream_power', 'line'],
        'lines': [
            ['upstream_{n}_power', '{n}', 'absolute', 1, 1000],
        ],
    }
}

# Why would we want an order different than what we already defined 🤷 ?
ORDER = [i for i in CHARTS]

html_parser = etree.HTMLParser()


class Service(UrlService):
    def __init__(self, configuration=None, name=None):
        if configuration is None:
            configuration = {}
        configuration.setdefault('url', 'http://192.168.100.1/cmconnectionstatus.html')
        # My modem's status page takes several seconds to load, does yours?
        configuration.setdefault('timeout', (update_every - 2))

        super(Service, self).__init__(configuration=configuration, name=name)

        self.order = ORDER
        self.definitions = deepcopy(CHARTS)

    def create_definitions(self, num_streams=0):
        for chart in self.definitions.values():
            lines = chart['lines']
            line_tmpl = lines.pop()

            for n in range(1, num_streams + 1):
                line = list(line_tmpl)
                line[0] = line[0].format(n=n)
                line[1] = line[1].format(n=n)
                lines.append(line)

    def get_stream_rows(self):
        try:
            html = self._get_raw_data()
            root = etree.parse(StringIO(html), html_parser)

            stream_rows = {'down': {}, 'up': {}}

# Channel info dict of dicts:
#           ┌────────────┐
#           │   Direct   │
#           └────────────┘
#                  │  ┌────────────┐
#                  └─▶│  Channel   │
#                     └────────────┘
#                            │  ┌────────────┐
#                            └─▶│   Metric   │
#                               └────────────┘

            # Evaluate the "downstrem" then "upstream" channel info
            for direction in ['down', 'up']:
                tbls = root.xpath('//table')
                for tbl in tbls:
                    # look for Down/upstream Bonded Channels table
                    if tbl.xpath(f'.//*[contains(text(),"{direction[1:]}stream Bonded Channels")]'):

                        table_rows = tbl.getchildren()
                        for table_row in table_rows:
                            # first row has only the "<direction>stream ..." th
                            # second starts with "Channel" header
                            tds = table_row.xpath('./td')
                            if len(tds) == 0 or tds[0].text.startswith("Channel"):
                                self.debug(f'Skipping Header line: "{tds}"')
                                continue

                            vals = [col.text.encode('UTF-8').decode().strip() for col in tds]
                            # Upstream has 7 values, Downstream has 8
                            if len(vals) < 7 or len(vals) > 8:
                                self.debug(f"Skipping: Not enough, or too many columns {len(vals)}")
                                continue

                            if direction == "down":
                                channel = table_row[0].text
                                channel_data = {
                                    'frequency': float(table_row[3].text.split(' ', 1)[0]) / 10000,  # mHz
                                    'power': float(table_row[4].text.split(' ', 1)[0]) * 100,  # dBmV
                                    'signal_to_noise': float(table_row[5].text.split(' ', 1)[0]) * 10000,  # dB
                                    'corrected_errors': int(table_row[6].text),  # int
                                    'uncorrected_errors': int(table_row[7].text),  # int
                                }
                            elif direction == "up":

                                # On the 8200 there is a channel "#" at col 0
                                # and a channel "id" at col 1, I picked channel
                                # id, since that seems more useful.
                                channel = table_row[1].text
                                channel_data = {
                                    'frequency': float(table_row[4].text.split(' ', 1)[0]) / 10000,  # mHz
                                    'width': float(table_row[5].text.split(' ', 1)[0]) / 10000,  # mHz
                                    'power': float(table_row[6].text.split(' ', 1)[0]) * 1000,  # dBmV
                                }
                            self.debug(f"{direction}stream channel: {channel} channel_data: {channel_data}")
                            stream_rows[direction][channel] = channel_data

            self.debug(stream_rows)
            return stream_rows

        except (ValueError, AttributeError):
            self.debug("Unable to parse html rows")
            return ()

    def _get_data(self):
        return_data = {}
        stream_rows = self.get_stream_rows()
        for direction in ["down", "up"]:
            self.debug(f"Direction: {direction}")
            if direction == "down":
                channel_metrics = [
                    'frequency',
                    'power',
                    'signal_to_noise',
                    'corrected_errors',
                    'uncorrected_errors'
                ]
            elif direction == "up":
                channel_metrics = [
                    'frequency',
                    'width',
                    'power'
                ]

            # We're going to return a consistently sorted list, of the channels
            # in numerical order,
            for channel in sorted(stream_rows[direction]):
                for key in channel_metrics:
                    return_data[f'{direction}stream_{channel}_{key}'] = stream_rows[direction][channel][key]
        return return_data

    def check(self):
        if not (self.url and isinstance(self.url, str)):
            self.error('URL is not defined or type is not <str>')
            return False

        self._manager = self._build_manager()
        if not self._manager:
            return False

        try:
            # Parse data from the URL
            data = self._get_data()
            # I create the deffinitions after pulling and parsing the data to
            # avoid having to query the UI twice.
            self.create_definitions(len(data))

        except Exception as error:
            self.error('_get_data() failed. Url: {url}. Error: {error}'.format(url=self.url, error=error))
            return False

        if isinstance(data, dict) and data:
            return True
        self.error('_get_data() returned no data or type is not <dict>')
        return False
