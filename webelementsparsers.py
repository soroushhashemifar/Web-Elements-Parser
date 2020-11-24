import re
from components import Product, OS, Browser, Bot, Device, Domain, Subdirectories, Query
import copy


class Parser:

    def parse(self):
        pass

    def components_as_dictionary(self):
        pass

    def components_as_flat_dictionary(self):
        pass


class UserAgentParser(Parser):

    ua_patterns = [  # User-agent patterns can be found on https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent
        ("firefox", r"Mozilla/.+\s\((.+;\s)+rv:.+\)\sGecko/.+\sFirefox/.+"),
        ("firefox", r"Mozilla/.+\s\((.+;\s)+rv:.+\).+"),
        ("opera", r"Mozilla/.+\s\(.+\)\sAppleWebKit/.+\s\(KHTML,\slike\sGecko\)\sChrome/.+\sSafari/.+\sOPR/.+"),
        ("chrome", r"Mozilla/.+\s\(.+\)\sAppleWebKit/.+\s\(KHTML,\slike\sGecko\)\sChrome/.+\sSafari/.+"),
        ("safari", r"Mozilla/.+\s\(.+\)\sAppleWebKit/.+\s\(KHTML,\slike\sGecko\)\s(Version/.+\s)?(Mobile/.+\s)?Safari/.+"),
        ("safari", r"Safari/.+\(.+\)"),
        ("safari", r"MobileSafari/.+(\s.+/.+)*"),
        ("ie", r"Mozilla/.+\s\(.+MSIE.+\)"),
        ("browserless", r"Mozilla/.+\s\(.+\)\sAppleWebKit/.+\s\(KHTML,\slike\sGecko\)"),
        ("browserless", r"curl/.+(\s\(.+\).+)?"),
        ("browserless", r"^.+/[\.\d]+$"),
        ("browserless", r"com\.apple\.WebKit\.WebContent/.+")
    ]

    def __init__(self, user_agent):
        self.user_agent = user_agent
        self.raw_components = []
        self.components = []
        self.browser = None
        self.bot_status = False
        self.layout_browser_engine = None

    def components_as_dictionary(self):
        components_list = []
        for component in self.components:
            components_list.append(
                (component.component_type, component.get_as_dict()))

        if self.layout_browser_engine is not None:
            components_list.append(
                ("layout_browser_engine", self.layout_browser_engine.get_as_dict()))
        components_list.append(("is_bot", self.bot_status))

        return dict(components_list)

    def components_as_flat_dictionary(self):
        flat_dictionary = {}
        components_dict = self.components_as_dictionary()
        self._mine_dictionary("", components_dict, flat_dictionary)

        return flat_dictionary

    def parse(self):
        self._preprocess_user_agent()
        self._check_bot()

        for ua_pattern in self.ua_patterns:
            if bool(re.match(ua_pattern[1], self.user_agent)):
                self.browser = ua_pattern[0]
                break

        if self.browser is None and not self.bot_status:
            return None
        elif self.browser is None and self.bot_status:
            return self

        self._separate_user_agent_components()
        self.components.append(Product(self.raw_components[0]))
        self._extract_details()

        return self

    def _preprocess_user_agent(self):
        space_included_platform = re.findall(
            r"^[\s\w]+/[\d\.]+", self.user_agent)
        if len(space_included_platform) > 0:
            self.user_agent = re.sub(
                r"^[\s\w]+/[\d\.]+", space_included_platform[0].replace(" ", ""), self.user_agent)

    def _separate_user_agent_components(self):
        current_word = ""
        inside_parentheses = False
        for char_index, char in enumerate(self.user_agent):
            if char == "(":
                inside_parentheses = True
                if current_word != "":
                    self.raw_components.append(current_word)

                current_word = ""
            elif char == ")":
                inside_parentheses = False
                if current_word != "":
                    self.raw_components.append(current_word)
                current_word = ""
            elif char == " ":
                if inside_parentheses:
                    current_word += char
                else:
                    if current_word != "":
                        self.raw_components.append(current_word)

                    current_word = ""
            else:
                current_word += char

            if char_index == len(self.user_agent)-1:
                if current_word != "":
                    self.raw_components.append(current_word)

    def _extract_details(self):
        if self.browser == "firefox":
            details = self.raw_components[1].split("; ")
            details.remove(details[-1])
            for term in details:
                if self._is_device(term):
                    self.components.append(Device(term))
                    details.remove(term)

            if self.bot_status:
                compatibility = [element for element in self.raw_components[2:]
                                 if "Firefox" not in element and bool(re.match(r".+/.+", element)) and not bool(re.match(r"compatible;\s.+https?://.+/.+", element))]
            else:
                compatibility = [element for element in self.raw_components[2:]
                                 if "Firefox" not in element and bool(re.match(r".+/.+", element))]

            browser = [element for element in self.raw_components[2:]
                       if "Firefox" in element]
            compatibility = [Product(item) for item in compatibility]
            if len(browser) == 1:
                browser = browser[0]
            else:
                browser = self.browser.capitalize() + "/"
            self.components.append(Browser(
                browser, compatibility=compatibility, gecko_release_version=details[-1]))

            self.components.append(OS(details))

        elif self.browser == "chrome":
            details = self.raw_components[1].split("; ")
            for term in details:
                if self._is_device(term):
                    self.components.append(Device(term))
                    details.remove(term)

            if self.bot_status:
                compatibility = [element for element in self.raw_components[4:]
                                 if "Chrome" not in element and bool(re.match(r".+/.+", element)) and not bool(re.match(r"compatible;\s.+https?://.+/.+", element))]
            else:
                compatibility = [element for element in self.raw_components[4:]
                                 if "Chrome" not in element and bool(re.match(r".+/.+", element))]

            self.components.append(OS(details))

            browser = [element for element in self.raw_components[2:]
                       if "Chrome" in element][0]
            compatibility = [Product(item) for item in compatibility]
            self.components.append(Browser(
                browser, compatibility=compatibility))
            self.layout_browser_engine = Product(self.raw_components[2])

        elif self.browser == "opera":
            details = self.raw_components[1].split("; ")
            for term in details:
                if self._is_device(term):
                    self.components.append(Device(term))
                    details.remove(term)

            if self.bot_status:
                compatibility = [element for element in self.raw_components[4:]
                                 if "OPR" not in element and bool(re.match(r".+/.+", element)) and not bool(re.match(r"compatible;\s.+https?://.+/.+", element))]
            else:
                compatibility = [element for element in self.raw_components[4:]
                                 if "OPR" not in element and bool(re.match(r".+/.+", element))]

            self.components.append(OS(details))

            browser = [element for element in self.raw_components[2:]
                       if "OPR" in element][0]
            compatibility = [Product(item) for item in compatibility]
            self.components.append(Browser(
                browser, compatibility=compatibility))
            self.layout_browser_engine = Product(self.raw_components[2])

        elif self.browser == "safari":
            if bool(re.match(r"Mozilla/.+", self.raw_components[0])):
                details = self.raw_components[1].split("; ")
                for term in details:
                    if self._is_device(term):
                        device_build = [
                            element for element in self.raw_components[4:] if "Mobile" in element]
                        device_build = device_build[0] if len(
                            device_build) == 1 else None
                        self.components.append(
                            Device(term, device_build=device_build))
                        details.remove(term)

                if self.bot_status:
                    compatibility = [element for element in self.raw_components[4:]
                                     if "Safari" not in element and "Version" not in element and "Mobile" not in element and bool(re.match(r".+/.+", element)) and not bool(re.match(r"compatible;\s.+https?://.+/.+", element))]
                else:
                    compatibility = [element for element in self.raw_components[4:]
                                     if "Safari" not in element and "Version" not in element and "Mobile" not in element and bool(re.match(r".+/.+", element))]

                version = [element for element in self.raw_components[4:]
                           if "Version" in element]
                version = version[0] if len(version) == 1 else None
                self.components.append(OS(details))

                browser = [element for element in self.raw_components[2:]
                           if "Safari" in element][0]
                compatibility = [Product(item) for item in compatibility]
                self.components.append(Browser(
                    browser, compatibility=compatibility, version=version))
                self.layout_browser_engine = Product(self.raw_components[2])

            elif bool(re.match(r"Safari/.+", self.raw_components[0])):
                if self.bot_status:
                    compatibility = [element for element in self.raw_components[1:]
                                     if bool(re.match(r".+/.+", element)) and not bool(re.match(r"compatible;\s.+https?://.+/.+", element))]
                else:
                    compatibility = [element for element in self.raw_components[1:] if bool(
                        re.match(r".+/.+", element))]

                os_type = [element for element in self.raw_components[1:]
                           if element not in compatibility]
                os = "macOS"+"; "+os_type[0] if len(os_type) > 0 else "macOS"
                self.components.append(OS(os))

                compatibility = [Product(item) for item in compatibility]
                self.components.append(
                    Browser(self.browser.capitalize()+"/", compatibility=compatibility))

            elif bool(re.match(r"MobileSafari/.+", self.raw_components[0])):
                if self.bot_status:
                    compatibility = [element for element in self.raw_components[1:]
                                     if bool(re.match(r".+/.+", element)) and not bool(re.match(r"compatible;\s.+https?://.+/.+", element))]
                else:
                    compatibility = [element for element in self.raw_components[1:] if bool(
                        re.match(r".+/.+", element))]

                self.components.append(OS("macOS"))

                compatibility = [Product(item) for item in compatibility]
                self.components.append(
                    Browser(self.browser.capitalize()+"/", compatibility=compatibility))

        elif self.browser == "ie":
            details = self.raw_components[1].split("; ")[3:]
            for term in details:
                if self._is_device(term):
                    self.components.append(Device(term))
                    details.remove(term)

            compatibility = details

            self.components.append(OS(self.raw_components[1].split("; ")[2]))

            compatibility = [Product(item) for item in compatibility]
            self.components.append(Browser(self.raw_components[1].split(
                "; ")[1].replace(" ", "/"), compatibility=compatibility))

        elif self.browser == "browserless":
            if bool(re.match(r"Mozilla/.+", self.raw_components[0])):
                details = self.raw_components[1].split("; ")
                for term in details:
                    if self._is_device(term):
                        device_build = [
                            element for element in self.raw_components[4:] if "Mobile" in element]
                        device_build = device_build[0] if len(
                            device_build) == 1 else None
                        self.components.append(
                            Device(term, device_build=device_build))
                        details.remove(term)

                if self.bot_status:
                    compatibility = [element for element in self.raw_components[4:]
                                     if "Mobile" not in element and bool(re.match(r".+/.+", element)) and not bool(re.match(r"compatible;\s.+https?://.+/.+", element))]
                else:
                    compatibility = [element for element in self.raw_components[4:]
                                     if "Mobile" not in element and bool(re.match(r".+/.+", element))]

                self.components.append(OS(details))

                compatibility = [Product(item) for item in compatibility]
                self.components.append(Browser(
                    "", compatibility=compatibility))
                self.layout_browser_engine = Product(self.raw_components[2])

            elif bool(re.match(r"curl/.+", self.raw_components[0])):
                if len(self.raw_components) > 1:
                    if self.bot_status:
                        compatibility = [element for element in self.raw_components[2:]
                                         if bool(re.match(r".+/.+", element)) and not bool(re.match(r"compatible;\s.+https?://.+/.+", element))]
                    else:
                        compatibility = [element for element in self.raw_components[2:] if bool(
                            re.match(r".+/.+", element))]

                    self.components.append(OS(self.raw_components[1]+"; "))

                    compatibility = [Product(item) for item in compatibility]
                    self.components.append(
                        Browser("", compatibility=compatibility))

            elif bool(re.match(r"com\.apple\.WebKit\.WebContent/.+", self.raw_components[0])):
                if self.bot_status:
                    compatibility = [element for element in self.raw_components[1:]
                                     if bool(re.match(r".+/.+", element)) and not bool(re.match(r"compatible;\s.+https?://.+/.+", element))]
                else:
                    compatibility = [element for element in self.raw_components[1:] if bool(
                        re.match(r".+/.+", element))]

                os_type = [element for element in self.raw_components[1:]
                           if element not in compatibility]
                os = "macOS"+"; "+os_type[0] if len(os_type) > 0 else "macOS"
                self.components.append(OS(os))

                compatibility = [Product(item) for item in compatibility]
                self.components.append(
                    Browser("", compatibility=compatibility))

        else:
            pass

    def _check_bot(self):
        bot = re.findall(r"\(compatible;\s.+https?://.+/.*\)", self.user_agent)
        if len(bot) > 0:
            self.bot_status = True
            self.components.append(Bot(bot[0][1:-1], URLParser))

        elif bool(re.match(r".+/.+\s?\(\+https?://.+/.*\)", self.user_agent)):
            self.bot_status = True
            self.components.append(
                Bot(re.findall(r"\(\+https?://.+/.*\)", self.user_agent)[0][1:-1], URLParser))

    def _is_device(self, term):
        if term in ["WOW64", "iPhone", "iPad", "iPod", "Macintosh", "Linux", "X11", "Win64", "Maemo", "Mobile", "Tablet"]:
            return True

        return False

    def _mine_dictionary(self, key_name, dictionary, new_dictionary):
        for key in dictionary.keys():
            if key_name == "":
                new_key = key
            else:
                new_key = key_name + "." + key

            if isinstance(dictionary[key], dict):
                self._mine_dictionary(new_key, dictionary[key], new_dictionary)

            elif isinstance(dictionary[key], list):
                new_key_temp = copy.deepcopy(new_key)
                for idx, element in enumerate(dictionary[key]):
                    new_key = new_key_temp + "." + str(idx+1)
                    if isinstance(element, dict):
                        self._mine_dictionary(
                            new_key, element, new_dictionary)

                    else:
                        new_dictionary[new_key] = element

            elif isinstance(dictionary[key], str) or isinstance(dictionary[key], int) or isinstance(dictionary[key], float) or isinstance(dictionary[key], bool):
                new_dictionary[new_key] = dictionary[key]


class URLParser(Parser):

    protocol_port_map_dict = {
        "acap": 674,
        "afp": 548,
        "dict": 2628,
        "dns": 53,
        "ftp": 21,
        "git": 9418,
        "gopher": 70,
        "http": 80,
        "https": 443,
        "imap": 143,
        "ipp": 631,
        "ipps": 631,
        "irc": 194,
        "ircs": 6697,
        "ldap": 389,
        "ldaps": 636,
        "mms": 1755,
        "msrp": 2855,
        "mtqp": 1038,
        "nfs": 111,
        "nntp": 119,
        "nntps": 563,
        "pop": 110,
        "prospero": 1525,
        "redis": 6379,
        "rsync": 873,
        "rtsp": 554,
        "rtsps": 322,
        "rtspu": 5005,
        "sftp": 22,
        "smb": 445,
        "snmp": 161,
        "ssh": 22,
        "svn": 3690,
        "telnet": 23,
        "ventrilo": 3784,
        "vnc": 5900,
        "wais": 210,
        "ws": 80,
        "wss": 443,
    }

    file_formats = [
        '7z', 'a', 'apk', 'ar', 'bz2', 'cab', 'cpio', 'deb', 'dmg', 'egg', 'gz', 'iso', 'jar', 'lha', 'mar', 'pea', 'rar', 'rpm', 's7z', 'shar', 'tar', 'tbz2', 'tgz', 'tlz', 'war', 'whl', 'xpi', 'zip', 'zipx', 'xz', 'pak',
        'aac', 'aiff', 'ape', 'au', 'flac', 'gsm', 'it', 'm3u', 'm4a', 'mid', 'mod', 'mp3', 'mpa', 'pls', 'ra', 's3m', 'sid', 'wav', 'wma', 'xm',
        'mobi', 'epub', 'azw1', 'azw3', 'azw4', 'azw6', 'azw', 'cbr', 'cbz',
        'c', 'cc', 'class', 'clj', 'cpp', 'cs', 'cxx', 'el', 'go', 'h', 'java', 'lua', 'm', 'm4', 'php', 'pl', 'po', 'py', 'rb', 'rs', 'sh', 'swift', 'vb', 'vcxproj', 'xcodeproj', 'xml', 'diff', 'patch', 'html', 'js',
        'exe', 'msi', 'bin', 'command', 'sh', 'bat', 'crx',
        'eot', 'otf', 'ttf', 'woff', 'woff2',
        '3dm', '3ds', 'max', 'bmp', 'dds', 'gif', 'jpg', 'jpeg', 'png', 'psd', 'xcf', 'tga', 'thm', 'tif', 'tiff', 'yuv', 'ai', 'eps', 'ps', 'svg', 'dwg', 'dxf', 'gpx', 'kml', 'kmz', 'webp',
        'ods', 'xls', 'xlsx', 'csv', 'ics', 'vcf',
        'ppt', 'odp',
        'doc', 'docx', 'ebook', 'log', 'md', 'msg', 'odt', 'org', 'pages', 'pdf', 'rtf', 'rst', 'tex', 'txt', 'wpd', 'wps',
        '3g2', '3gp', 'aaf', 'asf', 'avchd', 'avi', 'drc', 'flv', 'm2v', 'm4p', 'm4v', 'mkv', 'mng', 'mov', 'mp2', 'mp4', 'mpe', 'mpeg', 'mpg', 'mpv', 'mxf', 'nsv', 'ogg', 'ogv', 'ogm', 'qt', 'rm', 'rmvb', 'roq', 'srt', 'svi', 'vob', 'webm', 'wmv', 'yuv',
        'html', 'htm', 'css', 'js', 'jsx', 'less', 'scss', 'wasm', 'php'
    ]

    def __init__(self, url):
        self.url = url
        self.raw_components = []
        self.components = []
        self.protocol = None
        self.port = None
        self.fragment_identifiers = []
        self.target_accessed = "page"

    def components_as_dictionary(self):
        components_list = []
        for component in self.components:
            components_list.append(
                (component.component_type, component.get_as_dict()))

        components_list.append(("protocol", self.protocol))
        components_list.append(("port", self.port))
        components_list.append(
            ("fragment_identifiers", self.fragment_identifiers))
        components_list.append(("target_type", self.target_accessed))

        return dict(components_list)

    def components_as_flat_dictionary(self):
        flat_dictionary = {}
        components_dict = self.components_as_dictionary()
        self._mine_dictionary("", components_dict, flat_dictionary)

        return flat_dictionary

    def parse(self):
        if not bool(re.match(r"(?i)\b((?:\w+://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))", self.url)):
            return self

        self._detect_fragment_ids()

        protocol_domain_part = re.findall(
            r"(\w*://)*([\[\]:@A-Za-z_0-9.-]+).*", self.url)[0]
        if len(protocol_domain_part) > 0:
            if protocol_domain_part[0] != "":
                self.protocol = protocol_domain_part[0][:-3]

            self._detect_port()
            self.components.append(Domain(protocol_domain_part[1]))

            subdirectories = self.url.replace(
                "".join(protocol_domain_part), "")

            if bool(re.match(r".+\?.+=.+", subdirectories)):  # check whether the url is a query
                self.components.append(Query(subdirectories))
            elif bool(re.match(r"/.+", subdirectories)):
                self.components.append(Subdirectories(subdirectories))
                self.target_accessed = self._detect_target_typle()

        return self

    def _detect_target_typle(self):
        subdirectories = self.components[-1].get_as_dict()["subdirectories"]
        if len(subdirectories) > 0:
            last_directory = subdirectories[-1].split(".")
            if len(last_directory) > 1:
                if last_directory[-1] in self.file_formats:
                    return last_directory[-1]

    def _detect_fragment_ids(self):
        fragments = re.findall(r"#[A-Za-z_0-9]+$", self.url)
        if len(fragments) > 0:
            for idx, item in enumerate(fragments):
                self.url = self.url.replace(item, "")
                self.fragment_identifiers.append(item[1:])

    def _detect_port(self):
        port_found = re.findall(r"[A-Za-z_0-9.-]+:\d+/?", self.url)
        if len(port_found) > 0:
            self.port = re.findall(r":\d+", port_found[0])[0]
            self.url = self.url.replace(self.port, "")
            self.port = self.port[1:]
        elif self.protocol is not None:
            port_num = self.protocol_port_map_dict.get(self.protocol, -1)
            if port_num != -1:
                self.port = port_num

    def _mine_dictionary(self, key_name, dictionary, new_dictionary):
        for key in dictionary.keys():
            if key_name == "":
                new_key = key
            else:
                new_key = key_name + "." + key

            if new_key == "query.query":
                new_dictionary[new_key] = dictionary[key]
                continue

            if isinstance(dictionary[key], dict):
                self._mine_dictionary(new_key, dictionary[key], new_dictionary)

            elif isinstance(dictionary[key], list):
                new_key_temp = copy.deepcopy(new_key)
                for idx, element in enumerate(dictionary[key]):
                    new_key = new_key_temp + "." + str(idx+1)
                    if isinstance(element, dict):
                        self._mine_dictionary(
                            new_key, element, new_dictionary)

                    else:
                        new_dictionary[new_key] = element

            elif isinstance(dictionary[key], str) or isinstance(dictionary[key], int) or isinstance(dictionary[key], float) or isinstance(dictionary[key], bool):
                new_dictionary[new_key] = dictionary[key]


# uas = [
#     "Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)",
#     "Mozilla/5.0 (iPhone; CPU iPhone OS 7_0 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A465 Safari/9537.53 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
#     "Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)",
#     "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.93 Safari/537.36",
#     "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36",
#     "Mozilla/5.0 (Ubuntu; X11; Linux x86_64; rv:8.0) Gecko/20100101 Firefox/8.0",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:45.9) Gecko/20100101 Goanna/3.0 Firefox/45.9 PaleMoon/27.0.3",
#     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36 OPR/42.0.2393.85",
#     "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0)",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/601.7.7 (KHTML, like Gecko)",
#     "Safari/11601.7.7 CFNetwork/760.6.3 Darwin/15.6.0 (x86_64)",
#     'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/600.8.9 (KHTML, like Gecko) Version/8.0.8 Safari/600.8.9',
#     'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/601.7.7 (KHTML, like Gecko)',
#     'Mozilla/5.0 (iPhone; CPU iPhone OS 10_2 like Mac OS X) AppleWebKit/602.3.12 (KHTML, like Gecko) Mobile/14C92',
#     'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/534+ (KHTML, like Gecko) BingPreview/1.0b',
#     "curl/7.21.3 (amd64-portbld-freebsd8.2) libcurl/7.21.3 OpenSSL/0.9.8q zlib/1.2.3",
#     "curl/7.52.1",
#     'python-requests/2.12.1',
#     'Python-urllib/2.7',
#     "Mozilla/5.0 (compatible; MJ12bot/v1.4.7; http://mj12bot.com/)",
#     "com.apple.WebKit.WebContent/10600.8.9 CFNetwork/720.5.7 Darwin/14.5.0 (x86_64)",
#     "Sogou web spider/4.0(+http://www.sogou.com/docs/help/webmasters.htm#07)",
#     "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
#     "facebookexternalhit/1.1;kakaotalk-scrap/1.0;",
# ]

# for ua in uas[1:2]:
#     uap = UserAgentParser(ua)
#     uap.parse()

#     print(uap.components_as_dictionary())
#     print(uap.components_as_flat_dictionary())


# urls = [
#     "https://blog.hubspot.com:1234/en/marketing/parts-url",
#     "ftp://neilpatel.com/blog/complete-guide-structuring-urls/",
#     "neilpatel.com/blog/complete-guide-structuring-urls/",
#     "http://localhost:8889/notebooks/Feat%20Eng%20get%20req%20data.ipynb",
#     'http://www.cwi.nl:80/%7Eguido/Python.html',
#     "https://www.tutorialrepublic.com/html-tutorial/html-url.php",
#     "https://webcache.googleusercontent.com/search?q=cache:T5hudFlBksUJ:https://www.tutorialrepublic.com/html-tutorial/html-url.php+&cd=14&hl=en&ct=clnk&gl=ir",
#     "https://webcache.googleusercontent.com/search?q=cache:T5hudFlBksUJ:https://www.tutorialrepublic.com/html-tutorial/html-url.php+;cd=14;hl=en;ct=clnk;gl=ir#Syntax",
#     "https://en.wikipedia.org/wiki/URL#Syntax",
#     "https://themeisle.com/blog/what-is-a-website-url/",
#     "https://themeisle.com/blog/what-is-a-website-url",
#     "https://john.doe@www.example.com:123/forum/questions/?tag=networking&order=newest#top",
#     "https://john.doe@www.example.com:123/forum/questions/search?tag=networking&order=newest#top",
#     "telnet://192.0.2.16:80/",
#     "ldap://[2001:db8::7]/c=GB?objectClass?one",
#     "mailto:John.Doe@example.com",
#     "tel:+1-816-555-1212",
#     "news:comp.infosystems.www.servers.unix",
# ]

# for url in urls:
#     urlp = URLParser(url)
#     urlp.parse()

#     print(urlp.components_as_dictionary())
