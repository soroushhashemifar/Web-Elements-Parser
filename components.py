import re
# pip3 install iso-639
from iso639 import languages


class Browser:
    # The browser of the user-agent

    component_type = "browser"

    def __init__(self, browser, compatibility=None, gecko_release_version=None, version=None):
        self.browser = browser.split("/")[0]
        if version is None and browser != "":
            self.browser_version = browser.split("/")[1]
        elif version is None and browser != None:
            self.browser_version = None
        else:
            self.browser_version = version.split(
                "/")[1] if version is not None else None
        self.compatibility = compatibility
        self.gecko_release_version = gecko_release_version

    def get_as_dict(self):
        return {
            "browser": self.browser,
            "browser_version": self.browser_version,
            "compatibility": [item.get_as_dict() for item in self.compatibility],
            "gecko_release_version": self.gecko_release_version
        }


class OS:
    # Native platform the browser is running on

    component_type = "os"

    def __init__(self, os):
        self.os = os
        if isinstance(self.os, str):
            self.os = [term for term in os.split("; ") if term != None]

    def get_as_dict(self):
        return {
            "os": self.os,
        }


class Product:
    # The general token that says the browser is Mozilla compatible

    component_type = "product"

    def __init__(self, product):
        self.product = product.split("/")[0]
        if len(product.split("/")) > 1:
            self.product_version = product.split("/")[1]
        else:
            self.product_version = None

    def get_as_dict(self):
        return {
            "product": self.product,
            "product_version": self.product_version,
        }


class Bot:
    # The bot/crawler which is running

    component_type = "bot"

    def __init__(self, bot, url_parser):
        if bool(re.match(r"\+?https?://.+/.*", bot)):
            self.bot = None
            self.bot_version = None
            self.target_link = bot
        else:
            bot_temp = bot.split("; ")
            splitted_bot = bot_temp[1].split("/")
            self.bot = splitted_bot[0] if len(
                splitted_bot) == 2 else bot_temp[1]
            self.bot_version = splitted_bot[1] if len(
                splitted_bot) == 2 else None
            if bot_temp[2][0] == "+":
                self.target_link = bot_temp[2][1:]
            else:
                self.target_link = bot_temp[2]

        self.url_parser = url_parser

    def get_as_dict(self):
        return {
            "bot": self.bot,
            "bot_version": self.bot_version,
            "target_link": self.url_parser(self.target_link).parse().components_as_dictionary()
        }


class Device:

    component_type = "device"

    def __init__(self, device_name, device_build=None):
        self.device = device_name
        self.device_build = None if device_build is None else device_build.split(
            "/")[1]

    def get_as_dict(self):
        return {
            "device": self.device,
            "device_build": self.device_build,
        }


class Domain:

    component_type = "domain"

    def __init__(self, domain):
        self.domain = domain
        self.top_level_domain = None
        self.second_level_domain = None
        self.other_level_domains = None

        self._separate_parts()

    def _separate_parts(self):
        userinfo_host_parts = self.domain.split("@")
        if len(userinfo_host_parts) == 1:  # there is no format userinfo@host
            if bool(re.match(r"\[.+\]", self.domain)):  # ipv6
                splitted_domain = [self.domain[1:-1]]
            # ipv4
            elif bool(re.match(r"\d+\.\d+\.\d+\.\d+", self.domain)):
                splitted_domain = [self.domain]
            else:
                splitted_domain = self.domain.split(".")

        else:  # format: userinfo@host
            if ":" in userinfo_host_parts[0]:  # format: username:password
                self.user_info = userinfo_host_parts[0].split(":")
            else:  # format: blah.blah
                self.user_info = userinfo_host_parts[0].split(".")

            if bool(re.match(r"\[.+\]", userinfo_host_parts[1])):  # ipv6
                splitted_domain = [userinfo_host_parts[1][1:-1]]
            # ipv4
            elif bool(re.match(r"\d+\.\d+\.\d+\.\d+", userinfo_host_parts[1])):
                splitted_domain = [userinfo_host_parts[1]]
            else:
                splitted_domain = userinfo_host_parts[1].split(".")

        self.top_level_domain = splitted_domain[-1]
        if len(splitted_domain) > 1:
            self.second_level_domain = splitted_domain[-2]

            if len(splitted_domain) > 2:
                self.other_level_domains = splitted_domain[:-2]

    def get_as_dict(self):
        return {
            "top_level_domain": self.top_level_domain,
            "second_level_domain": self.second_level_domain,
            "other_level_domains": self.other_level_domains,
        }


class Subdirectories:

    component_type = "subdirectories"

    def __init__(self, subdirectories):
        self.subdirectories = subdirectories
        self.cleaned_subdirectories = None
        self.language = None

        self._separate_parts()

    def _separate_parts(self):
        if self.subdirectories[0] == "/":
            self.subdirectories = self.subdirectories[1:].split("/")
        else:
            self.subdirectories = self.subdirectories.split("/")

        self.cleaned_subdirectories = [
            item for item in self.subdirectories if item != "" and item[0] != ":"]

        try:
            languages.get(alpha2=self.cleaned_subdirectories[0])
            self.language = self.cleaned_subdirectories[0]
            self.cleaned_subdirectories.pop(0)
        except Exception:
            pass

    def get_as_dict(self):
        return {
            "subdirectories": self.cleaned_subdirectories,
            "language": self.language,
        }


class Query:

    component_type = "query"

    def __init__(self, query_text):
        self.query_text = query_text
        self.path = []
        self.fragment_identifiers = []
        self.query = None

        self._separate_parts()

    def _separate_parts(self):
        query_parts = self.query_text.split("?")
        for item in query_parts:
            if "=" in item:
                self._process_query(item)
            else:
                self.path.append(Subdirectories(item))

    def _process_query(self, item):
        # common query delimiters: ? ;
        item_parts = item.split("&")
        if len(item_parts) < 2:
            item_parts = item.split(";")

        parts = []
        for part in item_parts:
            parts.append(tuple(part.split("=")))

        self.query = dict(parts)

    def get_as_dict(self):
        return {
            "path": [item.get_as_dict() for item in self.path],
            "query": self.query,
        }
