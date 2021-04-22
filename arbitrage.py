#!/usr/bin/python

import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import lxml.html

def arbitrage(factors):
    result = []
    for i in range(len(factors)):
        result.append(1 / factors[i])
    total = sum(result)
    for i in range(len(result)):
        result[i] /= total
    return result, result[0] * factors[0]

def show_result(factors, result, only_gain = False):
    pad = ""
    if not only_gain:
        factors_display = []
        for factor in factors:
            factors_display.append(round(factor, 3))
        distribution_display = []
        for x in result:
            distribution_display.append(round(x, 3))
        print("Factors:      " + str(factors_display))
        print("Distribution: " + str(distribution_display))
        pad = "        "
    print("Gain: " + pad + str(round((result[0] * factors[0] - 1) * 100, 2)) + "%")

def create_driver(headless = False):
    global driver
    options = Options()
    if headless:
        options.headless = True
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options = options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined })"})
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})

def get_body():
    global driver
    return lxml.html.fromstring(driver.page_source)

driver = None
create_driver()
last_overview = "https://www.oddschecker.com/tennis"
driver.get(last_overview)

last_results = []
last_many = False
last_names = []
last_factors = []
last_distribution = []
last_bookies = []
last_bookie_names = {}
exclude = []

def get_details():
    body = get_body()
    items = body.cssselect(".diff-row")
    factors = []
    factor_bookies = []
    for item in items:
        fields = item.cssselect("td")[1:]
        best = None
        best_bookie = None
        for field in fields:
            bookie = field.attrib.get("data-bk")
            if bookie is not None and bookie not in exclude:
                text = field.text_content()
                if text and text != "SP":
                    components = text.split("/")
                    if len(components) == 1:
                        factor = 1 + float(components[0])
                    elif len(components) == 2:
                        factor = 1 + float(components[0]) / float(components[1])
                    else:
                        print("Data error: " + text)
                        return None
                    if best is None or factor > best:
                        best = factor
                        best_bookie = bookie
        if best is None:
            return None
        factors.append(best)
        factor_bookies.append(best_bookie)
    result, gain = arbitrage(factors)
    date = body.cssselect(".event .date")
    if date:
        date = date[0].text_content()
    else:
        date = None
    items = body.cssselect(".selTxt")
    names = []
    for item in items:
        names.append(item.text_content())
    return date, names, factors, factor_bookies, result, gain

def get_bookie_names():
    body = get_body()
    names = {}
    items = body.cssselect(".bk-logo-click")
    for item in items:
        names[item.attrib.get("data-bk")] = item.attrib.get("title")
    return names

def list_single(check, ignore_live = False):
    global driver
    body = get_body()
    results = []
    skip = False
    in_play = False
    factors = []
    names = ()
    link = ""
    started = False
    title = ""
    titles = body.cssselect("h1")
    if titles:
        title = titles[0].text_content()
    fields = body.cssselect(".match-on td")
    for field in fields:
        c = field.attrib.get("class")
        if c is None:
            c = ""
        if "all-odds-click" in c:
            if "time" in c:
                in_play = len(field.cssselect(".in-play")) > 0
            else:
                names = field.cssselect(".fixtures-bet-name")
                for i in range(len(names)):
                    names[i] = names[i].text_content()
        elif "basket-add" in c and not skip:
            started = True
            components = field.text_content().split("/")
            if len(components) == 2:
                factor = 1 + float(components[0]) / float(components[1])
                factors.append(factor)
            else:
                skip = True
        elif "link-right" in c:
            if not skip:
                links = field.cssselect("a")
                if links:
                    link = links[0].attrib.get("href")
                result, gain = arbitrage(factors)
                if gain > 1 and gain < 1.04 and (not ignore_live or not in_play):
                    link = "https://www.oddschecker.com" + link
                    submit = False
                    if check:
                        driver.get(link)
                        date, _, factors, _, result, gain = get_details()
                        if gain > 1 and gain < 1.04:
                            submit = True
                    else:
                        submit = True
                        date = None
                    if submit:
                        results.append((date, gain, in_play, names, factors, result, link, title))
            skip = False
            in_play = False
            factors = []
            link = ""
            started = False
        elif started:
            skip = True
    return results

def show_results():
    global last_results
    global last_many
    i = len(last_results)
    for date, gain, in_play, names, factors, result, _, title in last_results:
        if i != len(last_results):
            print()
        header = "#" + str(i)
        if last_many and title:
            header += " -- " + title
        if date is not None:
            header += " | " + date
        print(header)
        if in_play:
            print("IN PLAY")
        print(names)
        show_result(factors, result, True)
        i -= 1

def list_many(check, sleep = 0):
    urls = [
        "american-football",
        "australian-rules",
        "baseball",
        "basketball",
        "boxing",
        "football/english/premier-league",
        "football/english/championship",
        "football/english/league-1",
        "football/english/league-2",
        "football/italy/serie-a",
        "football/euro-2020",
        "football/champions-league",
        "football/poland/ekstraklasa",
        "football/scottish/championship",
        "football/scottish/fa-cup",
        "football/germany/bundesliga",
        "football/france/ligue-1",
        "football/france/ligue-2",
        "football/spain/la-liga-primera",
        "football/portugal/primeira-liga",
        "football/world/australia/a-league",
        "football/bulgaria/a-pfg",
        "football/world/china/super-league",
        "football/denmark/superligaen",
        "football/netherlands/eredivisie",
        "football/germany/bundesliga-2",
        "football/romania/liga-i",
        "football/switzerland/super-league",
        "football/ireland/premier-division",
        "football/netherlands/eerste-divisie",
        "football/romania/liga-i",
        "handball",
        "rugby-league",
        "rugby-union",
        "snooker/world-championship",
        "tennis",
        "ufc-mma",
        "volleyball"
        ]
    results = []
    for url in urls:
        driver.get("https://www.oddschecker.com/" + url)
        results += list_single(check, True)
        if sleep > 0:
            time.sleep(sleep)
    return results

def monitor():
    global last_results
    global driver
    driver.close()
    create_driver(True)
    lookup = set([])
    for _, _, _, _, _, _, link, _ in last_results:
        lookup.add(link)
    first = True
    while True:
        new = list_many(True, 5)
        for item in new:
            link = item[6]
            if link not in lookup:
                lookup.add(link)
                if first:
                    first = False
                else:
                    print()
                print(link)
                print(item[0])
                print(str(round((item[1] - 1) * 100, 2)) + "%")

def cmd_list(arguments):
    global last_results
    global last_many
    global last_overview
    last_overview = driver.current_url
    many = "many" in arguments
    check = "check" in arguments
    if many:
        results = list_many(check)
    else:
        results = list_single(check)
    results.sort(key = lambda x: (0 if x[2] else 1, x[1]))
    last_results = results
    last_many = many
    show_results()

def show_bookies(short = True):
    global last_bookies
    global last_bookie_names
    if short:
        print(last_bookies)
    relevant_names = {}
    for bookie in last_bookies:
        if bookie in last_bookie_names:
            relevant_names[bookie] = last_bookie_names[bookie]
    if relevant_names:
        print(relevant_names)

def show_values(values):
    global last_names
    global last_bookies
    global last_bookie_names
    global last_factors
    global last_distribution
    if last_bookies:
        show_bookies(False)
    if last_names:
        names = last_names
    else:
        names = []
        for i in range(len(values)):
            names.append("#" + str(i + 1))
    if len(values) == len(last_factors):
        total = sum(values)
        results = []
        gains = []
        expected = 0
        for i in range(len(values)):
            result = round(values[i] * factors[i], 2)
            gain = result / total
            gains.append(gain)
            expected += gain * last_distribution[i]
            results.append(result)
        min_gain = round((min(gains) - 1) * 100, 2)
        max_gain = round((max(gains) - 1) * 100, 2)
        for i in range(len(values)):
            print("Bet " + str(values[i]) + (" @ " + last_bookies[i] if last_bookies else "") + " on " + names[i] + ", " + str(round(last_factors[i], 3)) + " -> " + str(round((gains[i] - 1) * 100, 2)) + "%")
        print("Total:   " + str(total))
        print("Results: " + str(results))
        if min_gain == max_gain:
            print("Gain:    " + str(min_gain) + "%")
        else:
            print("Gain:    " + str(min_gain) + "% to " + str(max_gain) + "%, expected " + str(round((expected - 1) * 100, 2)) + "%")

while True:
    try:
        line = input("> ")
    except EOFError:
        driver.close()
        quit()
    arguments = line.split(" ")
    command = arguments[0]
    if command == "c" or command == "calc":
        odds = arguments[1:]
        factors = []
        for odd in odds:
            components = odd.split("/")
            if len(components) == 1:
                factor = float(components[0])
            else:
                factor = 1 + float(components[0]) / float(components[1])
            factors.append(factor)
        result, gain = arbitrage(factors)
        show_result(factors, result)
        last_factors = factors
        last_distribution = result
        if len(last_names) != len(factors):
            last_names = []
            last_bookies = []
    elif command == "l" or command == "list":
        cmd_list(arguments[1:])
    elif command == "m" or command == "monitor":
        monitor()
    elif command == "d" or command == "details":
        t = get_details()
        if t is not None:
            date, names, factors, factor_bookies, result, gain = t
            if date is not None:
                print(date)
            last_bookies = factor_bookies
            last_bookie_names = get_bookie_names()
            show_bookies()
            show_result(factors, result)
            last_names = names
            last_factors = factors
            last_distribution = result
    elif command == "f" or command == "follow":
        index = len(last_results) - int(arguments[1])
        if index >= 0:
            driver.get(last_results[index][6])
        else:
            print("No such result")
    elif command == "b" or command == "back":
        driver.get(last_overview)
        show_results()
    elif command == "a" or command == "amount":
        if last_distribution:
            do_round = "round" in arguments[1:]
            if do_round:
                arguments.remove("round")
            skip = False
            if len(arguments) == 2:
                total = float(arguments[1])
            elif len(arguments) == 3 and int(arguments[1]) <= len(last_distribution):
                total = float(arguments[2]) / last_distribution[int(arguments[1]) - 1]
            else:
                print("Incorrect arguments")
                skip = True
            if not skip:
                values = last_distribution.copy()
                for i in range(len(values)):
                    values[i] = round(values[i] * total, 0 if do_round else 2)
                show_values(values)
    elif command == "p" or command == "place":
        values = arguments[1:].copy()
        for i in range(len(values)):
            values[i] = float(values[i])
        if len(values) == len(last_factors):
            show_values(values)
    elif command == "e" or command == "exclude":
        exclude = arguments[1:]
    else:
        print("Unknown command: " + command)
