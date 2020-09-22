from copy import deepcopy
from io import StringIO
from lxml import etree
from re import sub as resub

from bases.FrameworkServices.UrlService import UrlService

priority = 90000

update_every = 10

CHARTS = {
    'modem_uptime': {
        'options': [None, 'Uptime', 'Seconds', 'Modem', 'arris_surfboard.uptime', 'line'],
        'lines': [
            ['modem_uptime', 'Seconds', 'absolute'],
        ],
    },
    'modem_swrev': {
        'options': [None, 'Software Release', 'swrev as number', 'Modem', 'arris_surfboard.swrev', 'line'],
        'lines': [
            ['modem_swrev', 'SW Rev', 'absolute'],
        ],
    }
}

html_parser = etree.HTMLParser()


class Service(UrlService):
    def __init__(self, configuration=None, name=None):
        if configuration is None:
            configuration = {}
        configuration.setdefault('url', 'http://192.168.100.1/cmswinfo.html')
        # My modem's status page takes several seconds to load, does yours?

        super(Service, self).__init__(configuration=configuration, name=name)
        self.modem_info_page = self.configuration.get('modem_info_page')
        self.request_timeout = update_every - 2
        self.debug(self.configuration)
        self.debug(f"self.request_timeout: {self.request_timeout}")
        self.definitions = deepcopy(CHARTS)
        # Persist the last data value in case of failure to return the last
        # value, instead of NaN
        self.last_data = {}

        # Since we already defined an order in CHARTS? 🤷
        self.order = list(self.definitions)

    def get_sw_info(self) -> dict:
        # This is very much a hack, I want to use the parent URL Class, so
        # I'll just overload the UrlService url and re-use it.
        modem_info = {}
        try:
            self.debug(f"Pulling Modem Software info")
            # Get the data from the info page, and remove *strong* tags
            html = resub("</?strong>", "", self._get_raw_data())
            root = etree.parse(StringIO(html), html_parser)
            tbls = root.xpath('//table')
            self.debug(f"Tables: {len(tbls)}")
            for tbl in tbls:
                # look for "Information" Table
                if tbl.xpath(f'.//*[contains(text(),"Information")]') or tbl.xpath(f'.//*[contains(text(),"Status")]'):
                    table_rows = tbl.getchildren()
                    self.debug(f"Table Rows: {len(table_rows)}")
                    for table_row in table_rows:
                        tds = table_row.xpath('./td')
                        if len(tds) == 0:
                            continue
                        unit = ""
                        if tds[0].text.startswith("Software Version"):
                            key = "swrev"
                            self.debug(f"{key}")

                            # SB8200.0200.174F.311915.NSH.RT.NA
                            # Remove all the letters and ., and cast to
                            # int and divide by a quadrillion to get into some
                            # reasonable scale :/
                            value = int(resub("[A-Za-z\\.]", "", table_row[1].text)) / 1000000000000000 
                        elif tds[0].text.startswith("Up Time"):
                            key = "uptime"
                            self.debug(f"{key}")

                            # Parse Up Time info into seconds
                            # 12 days 23h:59m:59s.00
                            uptime = table_row[1].text
                            days = int(uptime.split(" ")[0])

                            # Break the hours, minutes and seconds apart
                            # and cast them all to ints while doing it
                            hours, minutes, seconds = [int(i) for i in resub('[hms:\\.]', ' ', uptime.split(" ")[2]).split()[0:3]]
                            # Now multiply everything out into seconds
                            value = (days * 86400) + (hours * 3600) + (minutes * 60) + seconds
                            unit = "seconds"
                        else:
                            continue
                        self.debug(f"Found: {key}: {value} {unit}")
                        modem_info[f'modem_{key}'] = value

        except (ValueError, AttributeError):
            self.debug("Unable to parse html rows")
            return {}

        return modem_info

    def _get_data(self):
        return_data = {}
        modem_rows = self.get_sw_info()

        self.debug(modem_rows)
        return modem_rows

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
            self.last_data = data
            # I create the deffinitions after pulling and parsing the data to
            # avoid having to query the UI twice.
            self.debug(data)

        except Exception as error:
            self.error(f'_get_data() failed. Url: {self.url}. Error: {error}, returning {self.last_data}')
            if self.last_data:
                data = self.last_data
            else:
                return False

        if isinstance(data, dict) and data:
            return True
        self.error('_get_data() returned no data or type is not <dict>')
        return False
