#!/usr/bin/python

import sys

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

def show_result(factors, result):
    print("Factors: " + str(factors))
    print("Distribution: " + str(result))
    print("Gain: " + str((result[0] * factors[0] - 1) * 100) + "%")

options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
driver = webdriver.Chrome(options=options)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined })"})
driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})
last_overview = "https://www.oddschecker.com/tennis"
driver.get(last_overview)

def get_body():
    global driver
    return lxml.html.fromstring(driver.page_source)

last_results = []
last_many = False
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
    return factors, factor_bookies, result, gain

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
                    link = "https://www.oddschecker.com/" + link
                    submit = False
                    if check:
                        driver.get(link)
                        factors, _, result, gain = get_details()
                        if gain > 1 and gain < 1.04:
                            submit = True
                    else:
                        submit = True
                    if submit:
                        results.append((gain, in_play, names, factors, result, link, title))
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
    for gain, in_play, names, factors, result, _, title in last_results:
        if i != len(last_results):
            print()
        print("#" + str(i))
        if in_play:
            print("IN PLAY")
        if last_many and title:
            print(title)
        print(names)
        show_result(factors, result)
        i -= 1

def list_many(check):
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
    return results

def cmd_list(arguments):
    global last_results
    global last_many
    global last_overview
    last_overview = driver.current_url
    many = len(arguments) >= 1 and arguments[0] == "many"
    check = len(arguments) >= 1 and arguments[-1] == "check"
    if many:
        results = list_many(check)
    else:
        results = list_single(check)
    results.sort(key = lambda x: (0 if x[1] else 1, x[0]))
    last_results = results
    last_many = many
    show_results()

def show_bookies():
    global last_bookies
    global last_bookie_names
    print(last_bookies)
    relevant_names = {}
    for bookie in last_bookies:
        if bookie in last_bookie_names:
            relevant_names[bookie] = last_bookie_names[bookie]
    if relevant_names:
        print(relevant_names)

def show_values(values):
    global last_bookies
    global last_bookie_names
    global last_factors
    if last_bookies:
        show_bookies()
    for i in range(len(values)):
        print("Bet " + str(values[i]) + (" at " + last_bookies[i] if last_bookies else ""))
    if len(values) == len(last_factors):
        total = sum(values)
        print("Total: " + str(total))
        results = []
        gains = []
        for i in range(len(values)):
            result = round(values[i] * factors[i], 2)
            gains.append(result / total)
            results.append(result)
        print("Results: " + str(results))
        print("Gain: " + str((min(gains) - 1) * 100) + "% to " + str((max(gains) - 1) * 100) + "%")

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
        if len(last_bookies) != len(factors):
            last_bookies = []
    elif command == "l" or command == "list":
        cmd_list(arguments[1:])
    elif command == "d" or command == "details":
        t = get_details()
        if t is not None:
            factors, factor_bookies, result, gain = t
            last_bookies = factor_bookies
            last_bookie_names = get_bookie_names()
            show_bookies()
            show_result(factors, result)
            last_factors = factors
            last_distribution = result
    elif command == "f" or command == "follow":
        index = len(last_results) - int(arguments[1])
        if index >= 0:
            driver.get(last_results[index][5])
        else:
            print("No such result")
    elif command == "b" or command == "back":
        driver.get(last_overview)
        show_results()
    elif command == "a" or command == "amount":
        if last_distribution:
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
                    values[i] = round(values[i] * total, 2)
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
